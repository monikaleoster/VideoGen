"""CLI entry point: run the notes-extraction step standalone.

Usage: uv run python -m videogen.pipeline

There is no UI yet, so approval is simulated here by setting the step's
Event after a short delay. This is CLI-only scaffolding, not real approval
logic — the HTTP routes (`/steps/notes-extraction/approve`) are the real
approval path.
"""

import asyncio

from videogen.pipeline.notes_extraction import (
    NotesExtractionInput,
    run_notes_extraction,
    state,
)
from videogen.pipeline.base import StepStatus


async def _auto_approve_after_delay(delay: float) -> None:
    await asyncio.sleep(delay)
    print(f"[cli] status={state.status.value} -> simulating approval")
    state.approval_event.set()


async def _print_status_transitions(final_status: StepStatus) -> None:
    last_seen: StepStatus | None = None
    while last_seen != final_status:
        if state.status != last_seen:
            last_seen = state.status
            print(f"[cli] status={last_seen.value}")
        await asyncio.sleep(0.01)


async def main() -> None:
    print(f"[cli] status={StepStatus.PENDING.value}")

    watcher = asyncio.create_task(_print_status_transitions(StepStatus.DONE))
    approver = asyncio.create_task(_auto_approve_after_delay(1.0))
    output = await run_notes_extraction(NotesExtractionInput(deck_name="demo-deck.pptx"))
    await approver
    await watcher

    print(f"[cli] output={output}")


if __name__ == "__main__":
    asyncio.run(main())
