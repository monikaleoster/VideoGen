import asyncio

import pytest

from videogen.pipeline.audio_upload import AudioUploadInput, run_audio_upload, state
from videogen.pipeline.base import StepStatus


@pytest.fixture(autouse=True)
def reset_state():
    state.status = StepStatus.PENDING
    state.output = None
    state.approval_event = asyncio.Event()
    yield
    state.status = StepStatus.PENDING
    state.output = None
    state.approval_event = asyncio.Event()


async def test_step_blocks_until_approved() -> None:
    task = asyncio.create_task(
        run_audio_upload(AudioUploadInput(audio_paths=["a.mp3", "b.mp3"]))
    )

    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=1.0)
    assert state.status == StepStatus.WAITING_APPROVAL

    await asyncio.sleep(0.05)
    assert not task.done()

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_step_resumes_and_completes_after_approval() -> None:
    task = asyncio.create_task(
        run_audio_upload(AudioUploadInput(audio_paths=["a.mp3", "b.mp3", "c.mp3"]))
    )

    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=1.0)

    state.approval_event.set()
    output = await asyncio.wait_for(task, timeout=1.0)

    assert state.status == StepStatus.DONE
    assert len(output.drive_file_ids) == 3
    assert len(output.drive_urls) == 3
    assert state.output is output


async def _wait_for_status(target: StepStatus) -> None:
    while state.status != target:
        await asyncio.sleep(0.01)
