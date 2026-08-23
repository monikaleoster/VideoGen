"""Stub audio-upload step.

Fake implementation only — Phase 9 replaces this with real Google Drive
uploads. This phase proves the step interface and the approval-gate
block/unblock mechanism.
"""

import asyncio
from dataclasses import dataclass

from videogen.pipeline.base import StepState, StepStatus


@dataclass
class AudioUploadInput:
    audio_paths: list[str]


@dataclass
class AudioUploadOutput:
    drive_file_ids: list[str]
    drive_urls: list[str]


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[AudioUploadOutput] = StepState()


async def run_audio_upload(step_input: AudioUploadInput) -> AudioUploadOutput:
    """Run the stub step, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()

    await asyncio.sleep(0.1)

    file_ids = [f"fake-drive-id-audio-{i:02d}" for i in range(1, len(step_input.audio_paths) + 1)]
    output = AudioUploadOutput(
        drive_file_ids=file_ids,
        drive_urls=[f"https://drive.google.com/file/d/{fid}/view" for fid in file_ids],
    )
    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output
