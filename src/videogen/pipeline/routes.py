import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException

from videogen.pipeline.base import StepStatus
from videogen.pipeline.notes_extraction import (
    NotesExtractionInput,
    run_notes_extraction,
    state,
)

router = APIRouter(prefix="/steps/notes-extraction")

_DEMO_PPTX_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "sample_deck.pptx"


@router.post("/run")
async def run() -> dict[str, str]:
    if state.status in (StepStatus.RUNNING, StepStatus.WAITING_APPROVAL):
        raise HTTPException(status_code=409, detail="Step is already running")

    asyncio.create_task(
        run_notes_extraction(NotesExtractionInput(local_pptx_path=str(_DEMO_PPTX_PATH)))
    )
    # Wait until the step reaches WAITING_APPROVAL before responding, per
    # requirements.md: "starts the step; step runs until it reaches done,
    # waiting for approval and blocks".
    while state.status not in (StepStatus.WAITING_APPROVAL, StepStatus.DONE):
        await asyncio.sleep(0.01)
    return {"status": state.status.value}


@router.post("/approve")
async def approve() -> dict[str, str]:
    if state.status != StepStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"Step is not waiting for approval (status={state.status.value})",
        )

    state.approval_event.set()
    # Wait until the step resumes and reaches DONE before responding.
    while state.status != StepStatus.DONE:
        await asyncio.sleep(0.01)
    return {"status": state.status.value}


@router.get("/status")
async def status() -> dict:
    return {"status": state.status.value, "output": state.output}
