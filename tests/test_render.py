import asyncio
import subprocess
from pathlib import Path

import pytest

from videogen.pipeline.base import StepStatus
from videogen.pipeline.render import RenderInput, run_render, state


@pytest.fixture(autouse=True)
def reset_state():
    state.status = StepStatus.PENDING
    state.output = None
    state.approval_event = asyncio.Event()
    yield
    state.status = StepStatus.PENDING
    state.output = None
    state.approval_event = asyncio.Event()


@pytest.fixture
def slide_image_paths(tmp_path: Path) -> list[str]:
    paths = []
    for i, color in enumerate(["red", "green", "blue"], start=1):
        path = tmp_path / f"slide_{i:02d}.png"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=1920x1080:d=1", "-frames:v", "1", str(path)],
            check=True,
            capture_output=True,
        )
        paths.append(str(path))
    return paths


@pytest.fixture
def audio_path(tmp_path: Path) -> str:
    path = tmp_path / "audio.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-q:a", "9", str(path)],
        check=True,
        capture_output=True,
    )
    return str(path)


async def test_step_blocks_until_approved(slide_image_paths, audio_path) -> None:
    task = asyncio.create_task(
        run_render(RenderInput(slide_image_paths=slide_image_paths[:2], audio_paths=[audio_path, None]))
    )

    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=30.0)
    assert state.status == StepStatus.WAITING_APPROVAL

    await asyncio.sleep(0.05)
    assert not task.done()

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_step_resumes_and_completes_after_approval(slide_image_paths, audio_path) -> None:
    task = asyncio.create_task(
        run_render(
            RenderInput(
                slide_image_paths=slide_image_paths,
                audio_paths=[audio_path, None, audio_path],
            )
        )
    )

    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=30.0)

    state.approval_event.set()
    output = await asyncio.wait_for(task, timeout=30.0)

    assert state.status == StepStatus.DONE
    assert state.output is output

    # Real render: a genuine file exists at the reported path, with a real
    # (roughly expected) duration — not a fake fixed value.
    assert Path(output.video_path).exists()
    # 2 real-audio segments (~2s each) + 1 silent 3s fallback ≈ 7s.
    assert output.duration_sec == pytest.approx(7.0, abs=1.0)


async def test_missing_image_fails_without_partial_output(audio_path, tmp_path) -> None:
    missing_path = str(tmp_path / "does_not_exist.png")

    with pytest.raises(Exception):
        await run_render(RenderInput(slide_image_paths=[missing_path], audio_paths=[audio_path]))

    assert state.status != StepStatus.WAITING_APPROVAL


async def _wait_for_status(target: StepStatus) -> None:
    while state.status != target:
        await asyncio.sleep(0.01)
