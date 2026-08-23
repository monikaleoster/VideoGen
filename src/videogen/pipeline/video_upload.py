"""Stub video-upload step.

Fake implementation only — Phase 9 replaces this with real Google Drive
uploads. This phase proves the step interface and the approval-gate
block/unblock mechanism.
"""

import asyncio
from dataclasses import dataclass

from videogen.pipeline.base import StepState, StepStatus


@dataclass
class VideoUploadInput:
    video_path: str


@dataclass
class VideoUploadOutput:
    drive_file_id: str
    drive_url: str


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[VideoUploadOutput] = StepState()


async def run_video_upload(step_input: VideoUploadInput) -> VideoUploadOutput:
    """Run the stub step, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()

    await asyncio.sleep(0.1)

    file_id = "fake-drive-id-video-01"
    output = VideoUploadOutput(
        drive_file_id=file_id,
        drive_url=f"https://drive.google.com/file/d/{file_id}/view",
    )
    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output
