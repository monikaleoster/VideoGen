import asyncio
from pathlib import Path

import pytest

from videogen.pipeline import workdir
from videogen.pipeline.base import StepStatus
from videogen.pipeline.download import DownloadInput, run_download, state

SAMPLE_PPTX = str(Path(__file__).resolve().parent / "fixtures" / "sample_deck.pptx")


@pytest.fixture(autouse=True)
def reset_state():
    state.status = StepStatus.PENDING
    state.output = None
    state.approval_event = asyncio.Event()
    workdir.set_tmp_root(None)
    yield
    state.status = StepStatus.PENDING
    state.output = None
    state.approval_event = asyncio.Event()
    workdir.set_tmp_root(None)


async def test_step_blocks_until_approved() -> None:
    task = asyncio.create_task(run_download(DownloadInput(local_pptx_path=SAMPLE_PPTX)))

    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=30.0)
    assert state.status == StepStatus.WAITING_APPROVAL

    await asyncio.sleep(0.05)
    assert not task.done()

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_step_resumes_and_completes_after_approval() -> None:
    task = asyncio.create_task(run_download(DownloadInput(local_pptx_path=SAMPLE_PPTX)))

    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=30.0)

    state.approval_event.set()
    output = await asyncio.wait_for(task, timeout=5.0)

    assert state.status == StepStatus.DONE
    assert output.slide_count == 3
    assert output.slide_count == len(output.slide_image_paths)
    assert output.local_pptx_path
    assert state.output is output

    # Real conversion: confirm the images actually exist, are PNGs, and are
    # 1920x1080, not just that the paths were returned.
    import struct
    from pathlib import Path

    for image_path in output.slide_image_paths:
        path = Path(image_path)
        assert path.exists()
        with path.open("rb") as f:
            header = f.read(24)
        assert header[:8] == b"\x89PNG\r\n\x1a\n"
        width, height = struct.unpack(">II", header[16:24])
        assert (width, height) == (1920, 1080)


async def test_custom_tmp_root_places_output_under_it(tmp_path: Path) -> None:
    custom_root = tmp_path / "my_tmp_root"

    task = asyncio.create_task(
        run_download(DownloadInput(local_pptx_path=SAMPLE_PPTX, tmp_root=str(custom_root)))
    )
    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=30.0)
    state.approval_event.set()
    output = await asyncio.wait_for(task, timeout=5.0)

    # The copied .pptx and every slide-image PNG land under
    # <tmp_root>/videogen_download_*/, not the OS default temp dir.
    work_dir = Path(output.local_pptx_path).parent
    assert work_dir.parent == custom_root
    assert work_dir.name.startswith("videogen_download_")
    for image_path in output.slide_image_paths:
        assert Path(image_path).parent == work_dir


async def _wait_for_status(target: StepStatus) -> None:
    while state.status != target:
        await asyncio.sleep(0.01)
