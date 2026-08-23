import asyncio
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from videogen.pipeline import audio_upload, download, embed, notes_extraction, render, tts, video_upload
from videogen.pipeline.base import StepStatus
from videogen.pipeline.runner import run, run_pipeline

SAMPLE_PPTX = str(Path(__file__).resolve().parent / "fixtures" / "sample_deck.pptx")


@pytest.fixture
def silent_mp3_bytes(tmp_path: Path) -> bytes:
    """Real silence as MP3 bytes, so the real `tts` step's ffprobe duration
    measurement has a real file to read, with no network access needed."""
    out_path = tmp_path / "silence.mp3"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1.0", "-q:a", "9", "-y", str(out_path)],
        check=True,
        capture_output=True,
    )
    return out_path.read_bytes()


@pytest.fixture(autouse=True)
def mock_elevenlabs(silent_mp3_bytes):
    with patch("videogen.pipeline.tts._synthesize", return_value=silent_mp3_bytes):
        yield


_ALL_STATES = [
    ("download", download.state),
    ("notes_extraction", notes_extraction.state),
    ("tts", tts.state),
    ("audio_upload", audio_upload.state),
    ("embed", embed.state),
    ("render", render.state),
    ("video_upload", video_upload.state),
]


@pytest.fixture(autouse=True)
def reset_state():
    for _, state in _ALL_STATES:
        state.status = StepStatus.PENDING
        state.output = None
        state.approval_event = asyncio.Event()
    yield
    for _, state in _ALL_STATES:
        state.status = StepStatus.PENDING
        state.output = None
        state.approval_event = asyncio.Event()


async def _approve_in_order(log: list[str]) -> None:
    """Approve each step, in order, only once it reaches WAITING_APPROVAL.

    Also records a `<name>:running` / `<name>:done` entry into `log` for
    every observed transition, so tests can assert ordering.
    """
    for name, state in _ALL_STATES:
        # Poll for "left PENDING" rather than "hit RUNNING" specifically —
        # a fast real step (e.g. notes_extraction's python-pptx parse) can
        # move from RUNNING to WAITING_APPROVAL between two poll ticks, and
        # a poll that only recognizes RUNNING would then spin forever
        # waiting for a state it will never see again.
        while state.status == StepStatus.PENDING:
            await asyncio.sleep(0.005)
        log.append(f"{name}:running")

        while state.status != StepStatus.WAITING_APPROVAL:
            await asyncio.sleep(0.005)
        state.approval_event.set()

        while state.status != StepStatus.DONE:
            await asyncio.sleep(0.005)
        log.append(f"{name}:done")


async def test_steps_run_in_fixed_order_and_none_skip_ahead() -> None:
    log: list[str] = []
    approver = asyncio.create_task(_approve_in_order(log))
    run_task = asyncio.create_task(
        run_pipeline(local_pptx_path=SAMPLE_PPTX, elevenlabs_api_key="fake-key", elevenlabs_voice_id="fake-voice")
    )

    await asyncio.wait_for(asyncio.gather(approver, run_task), timeout=30.0)

    expected_order = [
        "download",
        "notes_extraction",
        "tts",
        "audio_upload",
        "embed",
        "render",
        "video_upload",
    ]
    observed_order = [entry.split(":")[0] for entry in log if entry.endswith(":running")]
    assert observed_order == expected_order

    # A step's `running` must come after the previous step's `done`.
    for i in range(1, len(expected_order)):
        prev_done = log.index(f"{expected_order[i - 1]}:done")
        this_running = log.index(f"{expected_order[i]}:running")
        assert prev_done < this_running


async def test_chained_output_threads_through_the_pipeline() -> None:
    approver = asyncio.create_task(_approve_in_order([]))
    output = await asyncio.wait_for(
        run_pipeline(local_pptx_path=SAMPLE_PPTX, elevenlabs_api_key="fake-key", elevenlabs_voice_id="fake-voice"), timeout=30.0
    )
    await asyncio.wait_for(approver, timeout=30.0)

    slide_count = download.state.output.slide_count
    assert slide_count == len(download.state.output.slide_image_paths)
    assert notes_extraction.state.output.slide_count == slide_count
    assert len(notes_extraction.state.output.notes) == slide_count
    assert len(tts.state.output.audio_paths) == slide_count
    assert len(audio_upload.state.output.drive_file_ids) == slide_count
    assert len(embed.state.output.slides_embedded) == slide_count

    assert output is video_upload.state.output
    assert output.drive_file_id
    assert output.drive_url


async def test_full_run_reaches_video_upload_done() -> None:
    approver = asyncio.create_task(_approve_in_order([]))
    await asyncio.wait_for(run_pipeline(local_pptx_path=SAMPLE_PPTX, elevenlabs_api_key="fake-key", elevenlabs_voice_id="fake-voice"), timeout=30.0)
    await asyncio.wait_for(approver, timeout=30.0)

    assert run.video_upload.status == StepStatus.DONE
    for _, state in _ALL_STATES:
        assert state.status == StepStatus.DONE
