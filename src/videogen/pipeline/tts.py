"""Stub text-to-speech step.

Fake implementation only — Phase 7 replaces this with real ElevenLabs calls.
This phase proves the step interface and the approval-gate block/unblock
mechanism.
"""

import asyncio
from dataclasses import dataclass

from videogen.pipeline.base import StepState, StepStatus


@dataclass
class TtsInput:
    notes: list[str]


@dataclass
class TtsOutput:
    audio_paths: list[str]
    durations_sec: list[float]


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[TtsOutput] = StepState()


async def run_tts(step_input: TtsInput) -> TtsOutput:
    """Run the stub step, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()

    await asyncio.sleep(0.1)

    output = TtsOutput(
        audio_paths=[
            f"/tmp/videogen/audio/slide_{i:02d}.mp3" for i in range(1, len(step_input.notes) + 1)
        ],
        durations_sec=[round(4.0 + 0.5 * i, 1) for i in range(len(step_input.notes))],
    )
    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output
