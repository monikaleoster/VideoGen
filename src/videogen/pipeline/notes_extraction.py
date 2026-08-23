"""Real notes-extraction step: local .pptx path -> per-slide speaker notes.

Per specs/2026-08-23-notes-extraction-real/requirements.md: pulls each
slide's raw speaker-notes text via python-pptx, in deck order, stripping
only leading/trailing whitespace (no other normalization). A slide with
no notes slide, or an empty/whitespace-only one, is flagged via
`has_notes` but still produces a normal result and still gates on human
approval like any other slide.
"""

import asyncio
import logging
from dataclasses import dataclass

from pptx import Presentation

from videogen.pipeline.base import StepState, StepStatus

logger = logging.getLogger(__name__)


@dataclass
class NotesExtractionInput:
    local_pptx_path: str


@dataclass
class NotesExtractionOutput:
    slide_count: int
    notes: list[str]
    has_notes: list[bool]


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[NotesExtractionOutput] = StepState()


def _extract_notes(pptx_path: str) -> tuple[list[str], list[bool]]:
    """Read each slide's speaker notes, in deck order, via python-pptx.

    A missing notes slide and an empty/whitespace-only one are both
    represented the same way: `""` in `notes`, `False` in `has_notes`.
    """
    presentation = Presentation(pptx_path)

    notes: list[str] = []
    has_notes: list[bool] = []
    for i, slide in enumerate(presentation.slides, start=1):
        raw_text = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
        stripped = raw_text.strip()
        notes.append(stripped)
        has_notes.append(bool(stripped))
        logger.debug("Slide %d: has_notes=%s, %d char(s)", i, bool(stripped), len(stripped))

    return notes, has_notes


async def run_notes_extraction(step_input: NotesExtractionInput) -> NotesExtractionOutput:
    """Run the real extraction, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()
    logger.info("notes_extraction starting: local_pptx_path=%s", step_input.local_pptx_path)

    # python-pptx parsing is blocking (file I/O + XML parsing) — run it off
    # the event loop thread so the WebSocket status push keeps working.
    notes, has_notes = await asyncio.to_thread(_extract_notes, step_input.local_pptx_path)

    output = NotesExtractionOutput(
        slide_count=len(notes),
        notes=notes,
        has_notes=has_notes,
    )
    logger.info(
        "notes_extraction complete: %d slide(s), %d with notes",
        output.slide_count, sum(has_notes),
    )
    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output
