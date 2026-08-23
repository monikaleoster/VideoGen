"""CLI entry point: run the full seven-step mock pipeline end-to-end.

Usage: uv run python -m videogen.pipeline

There is no UI yet, so approval is simulated here by setting each step's
Event after a short delay. This is CLI-only scaffolding, not real approval
logic — per-step/pipeline HTTP routes are Phase 3's concern, once the real
approval-gate UI needs something to call.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from videogen.pipeline.base import StepState, StepStatus
from videogen.pipeline.runner import run, run_pipeline

_DEMO_PPTX_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "sample_deck.pptx"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("videogen.pipeline")

# Steps in fixed roadmap order, paired with a human-readable name for logs.
_STEPS: list[tuple[str, StepState]] = [
    ("download", run.download),
    ("notes_extraction", run.notes_extraction),
    ("tts", run.tts),
    ("audio_upload", run.audio_upload),
    ("embed", run.embed),
    ("render", run.render),
    ("video_upload", run.video_upload),
]


async def _wait_for(state: StepState, target: StepStatus) -> None:
    while state.status != target:
        await asyncio.sleep(0.005)


async def _watch_and_auto_approve_in_order(delay: float) -> None:
    """Log each step's status transitions and auto-approve, one step at a
    time in fixed order, so a later step's log lines never race ahead of an
    earlier step's `DONE` line."""
    for name, state in _STEPS:
        # Poll for "left PENDING" rather than "hit RUNNING" specifically —
        # a fast real step can move from RUNNING to WAITING_APPROVAL between
        # two poll ticks, and a poll that only recognizes RUNNING would then
        # wait forever for a state it will never see again.
        while state.status == StepStatus.PENDING:
            await asyncio.sleep(0.005)
        logger.info("[%s] RUNNING", name)

        await _wait_for(state, StepStatus.WAITING_APPROVAL)
        logger.info("[%s] WAITING_APPROVAL output=%s", name, state.output)
        await asyncio.sleep(delay)
        logger.info("[%s] simulating approval (CLI-only, not real approval logic)", name)
        state.approval_event.set()

        await _wait_for(state, StepStatus.DONE)
        logger.info("[%s] DONE", name)


async def main() -> None:
    # No UI here to collect ElevenLabs credentials interactively, so the CLI
    # demo falls back to environment variables — a narrow, CLI-only
    # exception; the approval-gate UI never reads or persists these.
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
    if not api_key or not voice_id:
        logger.error(
            "ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID must both be set "
            "in the environment to run the CLI demo pipeline (the tts "
            "step calls the real ElevenLabs API)."
        )
        sys.exit(1)

    logger.info("Pipeline run starting")

    watcher = asyncio.create_task(_watch_and_auto_approve_in_order(delay=0.2))

    output = await run_pipeline(
        local_pptx_path=str(_DEMO_PPTX_PATH),
        elevenlabs_api_key=api_key,
        elevenlabs_voice_id=voice_id,
    )

    await watcher

    logger.info("Pipeline run complete: final video at %s", output.drive_url)


if __name__ == "__main__":
    asyncio.run(main())
