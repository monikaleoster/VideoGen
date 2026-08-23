import asyncio

import pytest

from videogen.pipeline.base import StepStatus
from videogen.pipeline.notes_extraction import (
    NotesExtractionInput,
    run_notes_extraction,
    state,
)


@pytest.fixture(autouse=True)
def reset_state():
    # Recreate the Event (not just clear it) so it isn't left bound to a
    # previous test's event loop.
    state.status = StepStatus.PENDING
    state.output = None
    state.approval_event = asyncio.Event()
    yield
    state.status = StepStatus.PENDING
    state.output = None
    state.approval_event = asyncio.Event()


async def test_step_blocks_until_approved() -> None:
    task = asyncio.create_task(
        run_notes_extraction(NotesExtractionInput(deck_name="deck.pptx"))
    )

    await asyncio.wait_for(
        _wait_for_status(StepStatus.WAITING_APPROVAL), timeout=1.0
    )
    assert state.status == StepStatus.WAITING_APPROVAL

    # The task must not be done yet: it's genuinely blocked on the Event.
    await asyncio.sleep(0.05)
    assert not task.done()

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_step_resumes_and_completes_after_approval() -> None:
    task = asyncio.create_task(
        run_notes_extraction(NotesExtractionInput(deck_name="deck.pptx"))
    )

    await asyncio.wait_for(
        _wait_for_status(StepStatus.WAITING_APPROVAL), timeout=1.0
    )

    state.approval_event.set()
    output = await asyncio.wait_for(task, timeout=1.0)

    assert state.status == StepStatus.DONE
    assert output.slide_count == 5
    assert len(output.notes) == 5
    assert state.output is output


async def _wait_for_status(target: StepStatus) -> None:
    while state.status != target:
        await asyncio.sleep(0.01)
