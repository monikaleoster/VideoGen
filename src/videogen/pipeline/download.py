"""Stub download step.

Fake implementation only — Phase 4 replaces this with real Google Drive
download and LibreOffice-headless slide-image conversion. This phase proves
the step interface and the approval-gate block/unblock mechanism.
"""

import asyncio
from dataclasses import dataclass

from videogen.pipeline.base import StepState, StepStatus


@dataclass
class DownloadInput:
    drive_link: str


@dataclass
class DownloadOutput:
    local_pptx_path: str
    slide_image_paths: list[str]
    slide_count: int


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[DownloadOutput] = StepState()


async def run_download(step_input: DownloadInput) -> DownloadOutput:
    """Run the stub step, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()

    await asyncio.sleep(0.1)

    slide_count = 5
    output = DownloadOutput(
        local_pptx_path=f"/tmp/videogen/downloads/{step_input.drive_link.rsplit('/', 1)[-1]}.pptx",
        slide_image_paths=[
            f"/tmp/videogen/downloads/slide_{i:02d}.png" for i in range(1, slide_count + 1)
        ],
        slide_count=slide_count,
    )
    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output
