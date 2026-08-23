import asyncio

import pytest
from fastapi.testclient import TestClient

from videogen.app import app
from videogen.pipeline.base import StepStatus
from videogen.pipeline.notes_extraction import state


@pytest.fixture(autouse=True)
def reset_state():
    state.status = StepStatus.PENDING
    state.output = None
    state.approval_event = asyncio.Event()
    yield
    state.status = StepStatus.PENDING
    state.output = None
    state.approval_event = asyncio.Event()


# `run` starts a background task that must outlive the request that created
# it, and `approve` must reach that same task's Event. TestClient only keeps
# a single event loop across requests when used as a context manager (see
# starlette.testclient._portal_factory) — without it, each call gets its own
# loop and the asyncio.Event breaks across requests.
def test_run_then_status_is_waiting_approval() -> None:
    with TestClient(app) as client:
        response = client.post("/steps/notes-extraction/run")
        assert response.status_code == 200

        status_response = client.get("/steps/notes-extraction/status")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "waiting_approval"


def test_approve_then_status_is_done_with_output() -> None:
    with TestClient(app) as client:
        client.post("/steps/notes-extraction/run")

        approve_response = client.post("/steps/notes-extraction/approve")
        assert approve_response.status_code == 200

        status_response = client.get("/steps/notes-extraction/status")
        body = status_response.json()
        assert body["status"] == "done"
        assert body["output"]["slide_count"] == 3
        assert len(body["output"]["notes"]) == 3


def test_approve_before_run_returns_error() -> None:
    with TestClient(app) as client:
        response = client.post("/steps/notes-extraction/approve")
        assert response.status_code == 409
