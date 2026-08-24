import asyncio
from pathlib import Path

import pytest

from videogen.pipeline import workdir
from videogen.pipeline.base import StepStatus
from videogen.pipeline.notes_extraction import (
    NotesExtractionInput,
    run_notes_extraction,
    state,
)

SAMPLE_PPTX = str(Path(__file__).resolve().parent / "fixtures" / "sample_deck.pptx")


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
        run_notes_extraction(NotesExtractionInput(local_pptx_path=SAMPLE_PPTX))
    )

    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=10.0)
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
        run_notes_extraction(NotesExtractionInput(local_pptx_path=SAMPLE_PPTX))
    )

    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=10.0)

    state.approval_event.set()
    output = await asyncio.wait_for(task, timeout=5.0)

    assert state.status == StepStatus.DONE
    assert state.output is output

    # Real extraction: exact per-slide text, correct order, correct
    # empty-notes flagging — matches tests/fixtures/generate_sample_deck.js.
    assert output.slide_count == 3
    assert output.notes == [
        "Speaker notes for slide 1: Welcome.",
        "Speaker notes for slide 2: Agenda.",
        "",
    ]
    assert output.has_notes == [True, True, False]

    # One .txt file per slide, always — including the empty-notes slide —
    # each byte-for-byte matching that slide's `notes[i]` value.
    assert len(output.notes_file_paths) == 3
    for path, expected_text in zip(output.notes_file_paths, output.notes, strict=True):
        assert Path(path).read_text() == expected_text
    assert Path(output.notes_file_paths[2]).read_bytes() == b""


async def test_notes_files_nest_under_shared_tmp_root(tmp_path: Path) -> None:
    workdir.set_tmp_root(str(tmp_path))
    try:
        task = asyncio.create_task(
            run_notes_extraction(NotesExtractionInput(local_pptx_path=SAMPLE_PPTX))
        )
        await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=10.0)
        state.approval_event.set()
        output = await asyncio.wait_for(task, timeout=5.0)

        for path in output.notes_file_paths:
            assert Path(path).parent.parent == tmp_path
    finally:
        workdir.set_tmp_root(None)


async def _wait_for_status(target: StepStatus) -> None:
    while state.status != target:
        await asyncio.sleep(0.01)
