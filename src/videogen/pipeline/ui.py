"""Per-step dispatch layer for the approval-gate UI (Phase 3).

Orchestration only — mirrors runner.run_pipeline's input-chaining, but one
step at a time instead of all seven at once, so a human can Run/Approve/
Reject each step individually from the browser. No step-specific fake-data
logic lives here (that stays inside each step module, per tech-stack.md).
"""

import asyncio
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Body, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from videogen.pipeline import (
    audio_upload,
    download,
    embed,
    notes_extraction,
    render,
    tts,
    video_upload,
)
from videogen.pipeline.base import StepState, StepStatus

# No real Drive integration — download takes a local .pptx path per
# specs/2026-08-23-download-and-slide-images/requirements.md. The UI's
# demo input points at the repo's checked-in sample deck fixture.
_DEMO_PPTX_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "sample_deck.pptx"


def _download_input(request_data: dict[str, Any]) -> download.DownloadInput:
    return download.DownloadInput(local_pptx_path=str(_DEMO_PPTX_PATH))


def _notes_extraction_input(request_data: dict[str, Any]) -> notes_extraction.NotesExtractionInput:
    return notes_extraction.NotesExtractionInput(
        local_pptx_path=download.state.output.local_pptx_path,
    )


def _tts_input(request_data: dict[str, Any]) -> tts.TtsInput:
    # Per-run credentials only — entered through the UI, held in memory for
    # this request only, never persisted (per
    # specs/2026-08-23-audio-generation-real/requirements.md).
    api_key = request_data.get("api_key")
    voice_id = request_data.get("voice_id")
    if not api_key or not voice_id:
        raise HTTPException(
            status_code=422,
            detail="'api_key' and 'voice_id' are both required to run the tts step",
        )
    return tts.TtsInput(
        notes=notes_extraction.state.output.notes,
        has_notes=notes_extraction.state.output.has_notes,
        api_key=api_key,
        voice_id=voice_id,
    )


def _audio_upload_input(request_data: dict[str, Any]) -> audio_upload.AudioUploadInput:
    return audio_upload.AudioUploadInput(audio_paths=tts.state.output.audio_paths)


def _embed_input(request_data: dict[str, Any]) -> embed.EmbedInput:
    return embed.EmbedInput(
        local_pptx_path=download.state.output.local_pptx_path,
        drive_file_ids=audio_upload.state.output.drive_file_ids,
    )


def _render_input(request_data: dict[str, Any]) -> render.RenderInput:
    return render.RenderInput(
        slide_image_paths=download.state.output.slide_image_paths,
        audio_paths=tts.state.output.audio_paths,
    )


def _video_upload_input(request_data: dict[str, Any]) -> video_upload.VideoUploadInput:
    return video_upload.VideoUploadInput(video_path=render.state.output.video_path)


class _StepEntry:
    def __init__(
        self,
        name: str,
        display_name: str,
        run_fn: Callable[[Any], Any],
        state: StepState,
        build_input: Callable[[dict[str, Any]], Any],
        prereq: str | None,
    ) -> None:
        self.name = name
        self.display_name = display_name
        self.run_fn = run_fn
        self.state = state
        self.build_input = build_input
        self.prereq = prereq


STEPS: list[_StepEntry] = [
    _StepEntry("download", "Download", download.run_download, download.state, _download_input, None),
    _StepEntry(
        "notes_extraction",
        "Notes Extraction",
        notes_extraction.run_notes_extraction,
        notes_extraction.state,
        _notes_extraction_input,
        "download",
    ),
    _StepEntry("tts", "Text-to-Speech", tts.run_tts, tts.state, _tts_input, "notes_extraction"),
    _StepEntry(
        "audio_upload",
        "Audio Upload",
        audio_upload.run_audio_upload,
        audio_upload.state,
        _audio_upload_input,
        "tts",
    ),
    _StepEntry("embed", "Embed Audio", embed.run_embed, embed.state, _embed_input, "audio_upload"),
    _StepEntry("render", "Render Video", render.run_render, render.state, _render_input, "embed"),
    _StepEntry(
        "video_upload",
        "Video Upload",
        video_upload.run_video_upload,
        video_upload.state,
        _video_upload_input,
        "render",
    ),
]

_STEPS_BY_NAME = {step.name: step for step in STEPS}


def _serialize_output(output: Any) -> Any:
    if output is None:
        return None
    if is_dataclass(output):
        return asdict(output)
    return output


def get_snapshot() -> dict[str, dict[str, Any]]:
    return {
        step.name: {
            "display_name": step.display_name,
            "status": step.state.status.value,
            "output": _serialize_output(step.state.output),
        }
        for step in STEPS
    }


def _get_step(name: str) -> _StepEntry:
    step = _STEPS_BY_NAME.get(name)
    if step is None:
        raise HTTPException(status_code=404, detail=f"Unknown step '{name}'")
    return step


async def _await_step_settled(step: _StepEntry, task: asyncio.Task) -> None:
    """Wait for `step` to settle, or surface `task`'s exception as a real
    HTTP error instead of hanging forever polling for a status transition
    that a failed step will never reach (e.g. a real ElevenLabs API error
    in `tts` — the step must fail visibly, not silently, per
    specs/2026-08-23-audio-generation-real/requirements.md)."""
    while step.state.status not in (StepStatus.WAITING_APPROVAL, StepStatus.DONE):
        if task.done() and task.exception() is not None:
            exc = task.exception()
            step.state.status = StepStatus.PENDING
            step.state.output = None
            raise HTTPException(status_code=502, detail=f"Step '{step.name}' failed: {exc}")
        await asyncio.sleep(0.01)


router = APIRouter()


@router.get("/pipeline/status")
async def pipeline_status() -> dict[str, dict[str, Any]]:
    return get_snapshot()


@router.post("/pipeline/{step_name}/run")
async def run_step(step_name: str, request_data: dict[str, Any] | None = Body(default=None)) -> dict[str, str]:
    step = _get_step(step_name)

    if step.prereq is not None:
        prereq_state = _STEPS_BY_NAME[step.prereq].state
        if prereq_state.status != StepStatus.DONE:
            raise HTTPException(
                status_code=409,
                detail=f"Prerequisite step '{step.prereq}' is not done yet",
            )

    if step.state.status in (StepStatus.RUNNING, StepStatus.WAITING_APPROVAL):
        raise HTTPException(status_code=409, detail=f"Step '{step_name}' is already running")

    task = asyncio.create_task(step.run_fn(step.build_input(request_data or {})))
    await _await_step_settled(step, task)
    return {"status": step.state.status.value}


@router.post("/pipeline/{step_name}/approve")
async def approve_step(step_name: str) -> dict[str, str]:
    step = _get_step(step_name)

    if step.state.status != StepStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"Step '{step_name}' is not waiting for approval (status={step.state.status.value})",
        )

    step.state.approval_event.set()
    while step.state.status != StepStatus.DONE:
        await asyncio.sleep(0.01)
    return {"status": step.state.status.value}


@router.post("/pipeline/{step_name}/reject")
async def reject_step(step_name: str, request_data: dict[str, Any] | None = Body(default=None)) -> dict[str, str]:
    step = _get_step(step_name)

    if step.state.status != StepStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"Step '{step_name}' is not waiting for approval (status={step.state.status.value})",
        )

    task = asyncio.create_task(step.run_fn(step.build_input(request_data or {})))
    # Wait for the fresh run to actually start (status flips away from the
    # stale WAITING_APPROVAL) before waiting for it to settle again —
    # otherwise we'd see the old status and return immediately.
    while step.state.status == StepStatus.WAITING_APPROVAL:
        if task.done() and task.exception() is not None:
            exc = task.exception()
            step.state.status = StepStatus.PENDING
            step.state.output = None
            raise HTTPException(status_code=502, detail=f"Step '{step_name}' failed: {exc}")
        await asyncio.sleep(0.01)
    await _await_step_settled(step, task)
    return {"status": step.state.status.value}


@router.post("/pipeline/tts/slide/{index}/generate")
async def generate_tts_slide(index: int, request_data: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Regenerate a single slide's audio in place, independent of the rest
    of the tts step's output — for the per-slide "Generate" button. Also
    backs the "Generate All" flow's per-slide entries when a slide's text
    override differs from the notes_extraction text (the whole-step
    Run/Reject path is used when no per-slide overrides are needed)."""
    if tts.state.output is None:
        raise HTTPException(
            status_code=409,
            detail="Run the tts step at least once before regenerating an individual slide",
        )

    audio_paths = tts.state.output.audio_paths
    if not (0 <= index < len(audio_paths)):
        raise HTTPException(status_code=404, detail=f"Slide index {index} is out of range")

    api_key = request_data.get("api_key")
    voice_id = request_data.get("voice_id")
    text = request_data.get("text", "")
    if not api_key or not voice_id:
        raise HTTPException(
            status_code=422, detail="'api_key' and 'voice_id' are both required"
        )
    if not text or not text.strip():
        raise HTTPException(
            status_code=422, detail="'text' must be non-empty to generate audio for this slide"
        )

    try:
        audio_path, duration = await tts.regenerate_slide(index, text.strip(), api_key, voice_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Slide {index} generation failed: {exc}") from None

    tts.state.output.audio_paths[index] = audio_path
    tts.state.output.durations_sec[index] = duration
    return {"audio_path": audio_path, "duration_sec": duration}


@router.get("/pipeline/tts/slide/{index}/audio")
async def get_tts_slide_audio(index: int) -> FileResponse:
    """Serve a generated slide's MP3 so it can be linked/played directly
    from the UI instead of the human having to locate the file on disk."""
    if tts.state.output is None or not (0 <= index < len(tts.state.output.audio_paths)):
        raise HTTPException(status_code=404, detail=f"No audio for slide {index}")

    audio_path = tts.state.output.audio_paths[index]
    if audio_path is None or not Path(audio_path).exists():
        raise HTTPException(status_code=404, detail=f"No audio generated yet for slide {index}")

    return FileResponse(audio_path, media_type="audio/mpeg")


@router.websocket("/ws/pipeline-status")
async def ws_pipeline_status(websocket: WebSocket) -> None:
    await websocket.accept()
    last_sent: dict[str, dict[str, Any]] | None = None
    try:
        while True:
            snapshot = get_snapshot()
            if snapshot != last_sent:
                await websocket.send_json(snapshot)
                last_sent = snapshot
            await asyncio.sleep(0.15)
    except WebSocketDisconnect:
        pass
