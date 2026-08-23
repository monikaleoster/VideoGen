"""Real text-to-speech step: per-slide notes -> ElevenLabs audio clips.

Per specs/2026-08-23-audio-generation-real/requirements.md: fixed voice
settings (no per-run override), a slide flagged `has_notes=False` by
notes_extraction is skipped entirely (no ElevenLabs call, None in both
output lists), and any ElevenLabs failure propagates rather than being
retried — the human re-runs manually via the existing Reject action.
"""

import asyncio
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from elevenlabs.client import ElevenLabs
from elevenlabs.types.voice_settings import VoiceSettings

from videogen.pipeline.base import StepState, StepStatus

# Fixed per specs/2026-08-23-audio-generation-real/requirements.md — not
# user-configurable per run.
_VOICE_SETTINGS = VoiceSettings(stability=0.5, similarity_boost=0.75)
_OUTPUT_FORMAT = "mp3_44100_128"


@dataclass
class TtsInput:
    notes: list[str]
    has_notes: list[bool]
    api_key: str
    voice_id: str


@dataclass
class TtsOutput:
    audio_paths: list[str | None]
    durations_sec: list[float | None]


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[TtsOutput] = StepState()


def _synthesize(text: str, api_key: str, voice_id: str) -> bytes:
    """Call ElevenLabs once for `text`, returning raw MP3 bytes.

    Any API error (auth, rate limit, network) propagates unmodified — no
    retry, per the confirmed no-auto-retry scope decision.
    """
    client = ElevenLabs(api_key=api_key)
    chunks = client.text_to_speech.convert(
        voice_id,
        text=text,
        voice_settings=_VOICE_SETTINGS,
        output_format=_OUTPUT_FORMAT,
    )
    return b"".join(chunks)


def _probe_duration_sec(audio_path: Path) -> float:
    """Read `audio_path`'s real duration via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _generate_one(
    text: str, api_key: str, voice_id: str, out_path: Path
) -> float:
    """Synthesize `text` to `out_path`, returning the clip's real duration."""
    audio_bytes = _synthesize(text, api_key, voice_id)
    out_path.write_bytes(audio_bytes)
    return _probe_duration_sec(out_path)


async def run_tts(step_input: TtsInput) -> TtsOutput:
    """Run real per-slide synthesis, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()

    work_dir = Path(tempfile.mkdtemp(prefix="videogen_tts_"))

    audio_paths: list[str | None] = []
    durations_sec: list[float | None] = []

    # Sequential, one slide at a time — no concurrent burst against the
    # ElevenLabs API, per the rate-limit-awareness scope decision.
    for i, (text, has_notes) in enumerate(
        zip(step_input.notes, step_input.has_notes, strict=True), start=1
    ):
        if not has_notes:
            audio_paths.append(None)
            durations_sec.append(None)
            continue

        out_path = work_dir / f"slide_{i:02d}.mp3"
        duration = await asyncio.to_thread(
            _generate_one, text, step_input.api_key, step_input.voice_id, out_path
        )
        audio_paths.append(str(out_path))
        durations_sec.append(duration)

    output = TtsOutput(audio_paths=audio_paths, durations_sec=durations_sec)
    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output
