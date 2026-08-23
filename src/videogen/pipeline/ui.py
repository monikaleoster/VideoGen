"""Per-step dispatch layer for the approval-gate UI (Phase 3).

Orchestration only — mirrors runner.run_pipeline's input-chaining, but one
step at a time instead of all seven at once, so a human can Run/Approve/
Reject each step individually from the browser. No step-specific fake-data
logic lives here (that stays inside each step module, per tech-stack.md).
"""

import asyncio
from dataclasses import asdict, is_dataclass
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

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

# No real Drive integration until Phase 4 — every step's fake input is
# either hardcoded (download) or built from a prerequisite's stored output.
_DEMO_DRIVE_LINK = "https://drive.google.com/demo-deck"


def _download_input() -> download.DownloadInput:
    return download.DownloadInput(drive_link=_DEMO_DRIVE_LINK)


def _notes_extraction_input() -> notes_extraction.NotesExtractionInput:
    d = download.state.output
    return notes_extraction.NotesExtractionInput(
        deck_name=d.local_pptx_path,
        slide_count=d.slide_count,
        slide_image_paths=d.slide_image_paths,
    )


def _tts_input() -> tts.TtsInput:
    return tts.TtsInput(notes=notes_extraction.state.output.notes)


def _audio_upload_input() -> audio_upload.AudioUploadInput:
    return audio_upload.AudioUploadInput(audio_paths=tts.state.output.audio_paths)


def _embed_input() -> embed.EmbedInput:
    return embed.EmbedInput(
        local_pptx_path=download.state.output.local_pptx_path,
        drive_file_ids=audio_upload.state.output.drive_file_ids,
    )


def _render_input() -> render.RenderInput:
    return render.RenderInput(
        slide_image_paths=download.state.output.slide_image_paths,
        audio_paths=tts.state.output.audio_paths,
    )


def _video_upload_input() -> video_upload.VideoUploadInput:
    return video_upload.VideoUploadInput(video_path=render.state.output.video_path)


class _StepEntry:
    def __init__(
        self,
        name: str,
        display_name: str,
        run_fn: Callable[[Any], Any],
        state: StepState,
        build_input: Callable[[], Any],
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


async def _await_step_settled(step: _StepEntry) -> None:
    while step.state.status not in (StepStatus.WAITING_APPROVAL, StepStatus.DONE):
        await asyncio.sleep(0.01)


router = APIRouter()


@router.get("/pipeline/status")
async def pipeline_status() -> dict[str, dict[str, Any]]:
    return get_snapshot()


@router.post("/pipeline/{step_name}/run")
async def run_step(step_name: str) -> dict[str, str]:
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

    asyncio.create_task(step.run_fn(step.build_input()))
    await _await_step_settled(step)
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
async def reject_step(step_name: str) -> dict[str, str]:
    step = _get_step(step_name)

    if step.state.status != StepStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"Step '{step_name}' is not waiting for approval (status={step.state.status.value})",
        )

    asyncio.create_task(step.run_fn(step.build_input()))
    # Wait for the fresh run to actually start (status flips away from the
    # stale WAITING_APPROVAL) before waiting for it to settle again —
    # otherwise we'd see the old status and return immediately.
    while step.state.status == StepStatus.WAITING_APPROVAL:
        await asyncio.sleep(0.01)
    await _await_step_settled(step)
    return {"status": step.state.status.value}


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
