"""CLI entry point: run the full seven-step mock pipeline end-to-end.

Usage: uv run python -m videogen.pipeline

There is no UI yet, so approval is simulated here by setting each step's
Event after a short delay. This is CLI-only scaffolding, not real approval
logic — per-step/pipeline HTTP routes are Phase 3's concern, once the real
approval-gate UI needs something to call.
"""

import asyncio
import logging

from videogen.pipeline.base import StepState, StepStatus
from videogen.pipeline.runner import run, run_pipeline

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
        await _wait_for(state, StepStatus.RUNNING)
        logger.info("[%s] RUNNING", name)

        await _wait_for(state, StepStatus.WAITING_APPROVAL)
        logger.info("[%s] WAITING_APPROVAL output=%s", name, state.output)
        await asyncio.sleep(delay)
        logger.info("[%s] simulating approval (CLI-only, not real approval logic)", name)
        state.approval_event.set()

        await _wait_for(state, StepStatus.DONE)
        logger.info("[%s] DONE", name)


async def main() -> None:
    logger.info("Pipeline run starting")

    watcher = asyncio.create_task(_watch_and_auto_approve_in_order(delay=0.2))

    output = await run_pipeline(drive_link="https://drive.google.com/file/d/demo-deck/view")

    await watcher

    logger.info("Pipeline run complete: final video at %s", output.drive_url)


if __name__ == "__main__":
    asyncio.run(main())
