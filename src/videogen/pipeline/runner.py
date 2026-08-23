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


async def run_pipeline(local_pptx_path: str) -> video_upload.VideoUploadOutput:
    """Run all seven steps in order, threading each step's output forward.

    Each step is awaited to `DONE` (i.e. its approval Event has been set and
    it has resumed) before the next step starts — no step skips ahead.
    """
    download_output = await download.run_download(
        download.DownloadInput(local_pptx_path=local_pptx_path)
    )

    notes_output = await notes_extraction.run_notes_extraction(
        notes_extraction.NotesExtractionInput(
            deck_name=download_output.local_pptx_path,
            slide_count=download_output.slide_count,
            slide_image_paths=download_output.slide_image_paths,
        )
    )

    tts_output = await tts.run_tts(tts.TtsInput(notes=notes_output.notes))

    audio_upload_output = await audio_upload.run_audio_upload(
        audio_upload.AudioUploadInput(audio_paths=tts_output.audio_paths)
    )

    # embed's output isn't consumed further downstream in this phase, but
    # the step still runs and gates on its own approval Event per
    # requirements.
    await embed.run_embed(
        embed.EmbedInput(
            local_pptx_path=download_output.local_pptx_path,
            drive_file_ids=audio_upload_output.drive_file_ids,
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
