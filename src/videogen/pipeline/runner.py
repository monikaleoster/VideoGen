"""Pipeline runner: chains all seven mock steps in roadmap order.

Orchestration only — no step-specific fake-data generation lives here; that
stays inside each step module (per tech-stack.md).
"""

from dataclasses import dataclass, field

from videogen.pipeline import (
    audio_upload,
    download,
    embed,
    notes_extraction,
    render,
    tts,
    video_upload,
)
from videogen.pipeline.base import StepState


@dataclass
class PipelineRun:
    """Holds all seven steps' `StepState` instances for one run."""

    download: StepState = field(default_factory=lambda: download.state)
    notes_extraction: StepState = field(default_factory=lambda: notes_extraction.state)
    tts: StepState = field(default_factory=lambda: tts.state)
    audio_upload: StepState = field(default_factory=lambda: audio_upload.state)
    embed: StepState = field(default_factory=lambda: embed.state)
    render: StepState = field(default_factory=lambda: render.state)
    video_upload: StepState = field(default_factory=lambda: video_upload.state)


# Module-level holder so the CLI (and later HTTP routes) reach the same
# in-flight run's state, matching the single-in-flight-run model.
run = PipelineRun()


async def run_pipeline(
    local_pptx_path: str, elevenlabs_api_key: str, elevenlabs_voice_id: str
) -> video_upload.VideoUploadOutput:
    """Run all seven steps in order, threading each step's output forward.

    Each step is awaited to `DONE` (i.e. its approval Event has been set and
    it has resumed) before the next step starts — no step skips ahead.
    """
    download_output = await download.run_download(
        download.DownloadInput(local_pptx_path=local_pptx_path)
    )

    notes_output = await notes_extraction.run_notes_extraction(
        notes_extraction.NotesExtractionInput(
            local_pptx_path=download_output.local_pptx_path,
        )
    )

    tts_output = await tts.run_tts(
        tts.TtsInput(
            notes=notes_output.notes,
            has_notes=notes_output.has_notes,
            api_key=elevenlabs_api_key,
            voice_id=elevenlabs_voice_id,
        )
    )

    # audio_upload's output isn't consumed downstream — it only produces
    # fake Drive IDs, not local paths (real Drive upload is Phase 9's
    # concern, still deferred) — but the step still runs and gates on its
    # own approval Event per requirements.
    await audio_upload.run_audio_upload(
        audio_upload.AudioUploadInput(audio_paths=tts_output.audio_paths)
    )

    # embed's real audio-path input comes from tts's output directly, not
    # audio_upload's, per specs/2026-08-23-embed-audio-real/requirements.md.
    await embed.run_embed(
        embed.EmbedInput(
            local_pptx_path=download_output.local_pptx_path,
            audio_paths=tts_output.audio_paths,
        )
    )

    render_output = await render.run_render(
        render.RenderInput(
            slide_image_paths=download_output.slide_image_paths,
            audio_paths=tts_output.audio_paths,
        )
    )

    return await video_upload.run_video_upload(
        video_upload.VideoUploadInput(video_path=render_output.video_path)
    )
