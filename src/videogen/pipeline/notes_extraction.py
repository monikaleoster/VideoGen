"""Stub notes-extraction step.

Fake implementation only — Phase 6 replaces this with real python-pptx
parsing. This phase proves the step interface and the approval-gate
block/unblock mechanism.
"""

import asyncio
from dataclasses import dataclass

from videogen.pipeline.base import StepState, StepStatus


@dataclass
class NotesExtractionInput:
    deck_name: str


@dataclass
class NotesExtractionOutput:
    slide_count: int
    notes: list[str]


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[NotesExtractionOutput] = StepState()


async def run_notes_extraction(
    step_input: NotesExtractionInput,
) -> NotesExtractionOutput:
    """Run the stub step, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()

    await asyncio.sleep(0.1)

    output = NotesExtractionOutput(
        slide_count=5,
        notes=[f"Fake notes for slide {i} of '{step_input.deck_name}'" for i in range(1, 6)],
    )
    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output
