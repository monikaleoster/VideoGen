import asyncio
import subprocess
from pathlib import Path

import pytest
from pptx import Presentation

from videogen.pipeline import workdir
from videogen.pipeline.base import StepStatus
from videogen.pipeline.embed import EmbedInput, run_embed, state

SAMPLE_PPTX = str(Path(__file__).resolve().parent / "fixtures" / "sample_deck.pptx")

_TIMING_NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}


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


@pytest.fixture
def silent_mp3_path(tmp_path: Path) -> str:
    out_path = tmp_path / "silence.mp3"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1.0", "-q:a", "9", "-y", str(out_path)],
        check=True,
        capture_output=True,
    )
    return str(out_path)


def _autoplay_conditions(slide) -> list[str | None]:
    """All `delay` attrs of `p:cond` elements under this slide's timing."""
    return [c.get("delay") for c in slide._element.findall(".//p:timing//p:cond", _TIMING_NS)]


async def test_step_blocks_until_approved(silent_mp3_path) -> None:
    task = asyncio.create_task(
        run_embed(EmbedInput(local_pptx_path=SAMPLE_PPTX, audio_paths=[silent_mp3_path, None, None]))
    )

    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=10.0)
    assert state.status == StepStatus.WAITING_APPROVAL

    await asyncio.sleep(0.05)
    assert not task.done()

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_audio_slides_get_real_autoplay_media_others_untouched(silent_mp3_path) -> None:
    task = asyncio.create_task(
        run_embed(
            EmbedInput(
                local_pptx_path=SAMPLE_PPTX,
                audio_paths=[silent_mp3_path, None, silent_mp3_path],
            )
        )
    )
    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=10.0)
    state.approval_event.set()
    output = await asyncio.wait_for(task, timeout=10.0)

    assert state.status == StepStatus.DONE
    assert output.slides_embedded == [True, False, True]
    assert Path(output.updated_pptx_path).exists()

    # The output is a genuinely new file — the original is unmodified.
    assert output.updated_pptx_path != SAMPLE_PPTX
    original = Presentation(SAMPLE_PPTX)
    assert not original.slides[0]._element.findall(".//p:timing", _TIMING_NS)

    result = Presentation(output.updated_pptx_path)

    # Slide 1: has audio, autoplay (delay="0"), not click-triggered.
    conds_1 = _autoplay_conditions(result.slides[0])
    assert "0" in conds_1
    assert "indefinite" not in conds_1

    # Slide 2: no audio — no timing tree, no media relationship at all.
    assert result.slides[1]._element.findall(".//p:timing", _TIMING_NS) == []

    # Slide 3: has audio, also autoplay.
    conds_3 = _autoplay_conditions(result.slides[2])
    assert "0" in conds_3
    assert "indefinite" not in conds_3


async def test_missing_audio_file_fails_without_partial_output(tmp_path) -> None:
    missing_path = str(tmp_path / "does_not_exist.mp3")

    with pytest.raises(Exception):
        await run_embed(EmbedInput(local_pptx_path=SAMPLE_PPTX, audio_paths=[missing_path, None, None]))

    assert state.status != StepStatus.WAITING_APPROVAL


async def test_work_dir_nests_under_shared_tmp_root_when_set(
    tmp_path: Path, silent_mp3_path: str
) -> None:
    custom_root = tmp_path / "shared_root"
    workdir.set_tmp_root(str(custom_root))

    task = asyncio.create_task(
        run_embed(EmbedInput(local_pptx_path=SAMPLE_PPTX, audio_paths=[silent_mp3_path, None, None]))
    )
    await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=10.0)
    state.approval_event.set()
    output = await asyncio.wait_for(task, timeout=10.0)

    # embed's work dir (holding the output .pptx) nests under the shared
    # root instead of the OS default temp location.
    embed_dirs = list(custom_root.glob("videogen_embed_*"))
    assert len(embed_dirs) == 1
    assert Path(output.updated_pptx_path).parent == embed_dirs[0]


async def _wait_for_status(target: StepStatus) -> None:
    while state.status != target:
        await asyncio.sleep(0.01)
