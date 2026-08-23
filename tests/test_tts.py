import asyncio
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from videogen.pipeline.base import StepStatus
from videogen.pipeline.tts import TtsInput, run_tts, state


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
def silent_mp3_bytes(tmp_path: Path) -> bytes:
    """~1.5s of real silence as MP3 bytes, so ffprobe measures a real,
    deterministic-enough duration without any network access."""
    out_path = tmp_path / "silence.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            "1.5",
            "-q:a",
            "9",
            "-y",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )
    return out_path.read_bytes()


async def test_slide_with_notes_gets_real_audio_file_and_duration(silent_mp3_bytes) -> None:
    with patch("videogen.pipeline.tts._synthesize", return_value=silent_mp3_bytes) as mock_synth:
        task = asyncio.create_task(
            run_tts(
                TtsInput(
                    notes=["Hello slide one."],
                    has_notes=[True],
                    api_key="fake-key",
                    voice_id="fake-voice",
                )
            )
        )
        await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=10.0)

        state.approval_event.set()
        output = await asyncio.wait_for(task, timeout=10.0)

    mock_synth.assert_called_once_with("Hello slide one.", "fake-key", "fake-voice")
    assert output.audio_paths[0] is not None
    assert Path(output.audio_paths[0]).exists()
    assert output.durations_sec[0] == pytest.approx(1.5, abs=0.2)


async def test_slide_without_notes_is_skipped_no_api_call() -> None:
    with patch("videogen.pipeline.tts._synthesize") as mock_synth:
        task = asyncio.create_task(
            run_tts(
                TtsInput(
                    notes=[""],
                    has_notes=[False],
                    api_key="fake-key",
                    voice_id="fake-voice",
                )
            )
        )
        await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=10.0)

        state.approval_event.set()
        output = await asyncio.wait_for(task, timeout=10.0)

    mock_synth.assert_not_called()
    assert output.audio_paths == [None]
    assert output.durations_sec == [None]


async def test_mixed_slides_only_calls_api_for_slides_with_notes(silent_mp3_bytes) -> None:
    with patch("videogen.pipeline.tts._synthesize", return_value=silent_mp3_bytes) as mock_synth:
        task = asyncio.create_task(
            run_tts(
                TtsInput(
                    notes=["Slide one.", "", "Slide three."],
                    has_notes=[True, False, True],
                    api_key="fake-key",
                    voice_id="fake-voice",
                )
            )
        )
        await asyncio.wait_for(_wait_for_status(StepStatus.WAITING_APPROVAL), timeout=10.0)

        state.approval_event.set()
        output = await asyncio.wait_for(task, timeout=10.0)

    assert mock_synth.call_count == 2
    assert output.audio_paths[0] is not None
    assert output.audio_paths[1] is None
    assert output.audio_paths[2] is not None
    assert output.durations_sec[1] is None


async def test_synthesis_failure_propagates_not_swallowed() -> None:
    with patch("videogen.pipeline.tts._synthesize", side_effect=RuntimeError("ElevenLabs 429")):
        with pytest.raises(RuntimeError, match="ElevenLabs 429"):
            await run_tts(
                TtsInput(
                    notes=["Will fail."],
                    has_notes=[True],
                    api_key="fake-key",
                    voice_id="fake-voice",
                )
            )

    # The step must not have transitioned to WAITING_APPROVAL for a failed run.
    assert state.status != StepStatus.WAITING_APPROVAL


async def test_step_blocks_until_approved(silent_mp3_bytes) -> None:
    with patch("videogen.pipeline.tts._synthesize", return_value=silent_mp3_bytes):
        task = asyncio.create_task(
            run_tts(
                TtsInput(
                    notes=["Hello."],
                    has_notes=[True],
                    api_key="fake-key",
                    voice_id="fake-voice",
                )
            )
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


async def _wait_for_status(target: StepStatus) -> None:
    while state.status != target:
        await asyncio.sleep(0.01)
