"""Stub render step.

Fake implementation only — Phase 5 re-validates the real ffmpeg render
against this interface. This phase proves the step interface and the
approval-gate block/unblock mechanism.
"""

import asyncio
from dataclasses import dataclass

from videogen.pipeline.base import StepState, StepStatus


@dataclass
class RenderInput:
    slide_image_paths: list[str]
    audio_paths: list[str]


@dataclass
class RenderOutput:
    video_path: str
    duration_sec: float


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[RenderOutput] = StepState()


async def run_render(step_input: RenderInput) -> RenderOutput:
    """Run the stub step, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()

    await asyncio.sleep(0.1)

    output = RenderOutput(
        video_path="/tmp/videogen/render/final_video.mp4",
        duration_sec=round(sum(4.0 + 0.5 * i for i in range(len(step_input.slide_image_paths))), 1),
    )
    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output
