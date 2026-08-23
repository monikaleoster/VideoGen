"""Stub embed step.

Fake implementation only — Phase 8 replaces this with real python-pptx
audio-embedding logic. This phase proves the step interface and the
approval-gate block/unblock mechanism.
"""

import asyncio
from dataclasses import dataclass

from videogen.pipeline.base import StepState, StepStatus


@dataclass
class EmbedInput:
    local_pptx_path: str
    drive_file_ids: list[str]


@dataclass
class EmbedOutput:
    updated_pptx_path: str
    slides_embedded: list[bool]


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[EmbedOutput] = StepState()


async def run_embed(step_input: EmbedInput) -> EmbedOutput:
    """Run the stub step, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()

    await asyncio.sleep(0.1)

    base_path = step_input.local_pptx_path.removesuffix(".pptx")
    output = EmbedOutput(
        updated_pptx_path=f"{base_path}_with_audio.pptx",
        slides_embedded=[True for _ in step_input.drive_file_ids],
    )
    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output
