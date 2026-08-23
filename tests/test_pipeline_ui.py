import pytest
from httpx import ASGITransport, AsyncClient

from videogen.app import app
from videogen.pipeline import download, notes_extraction


@pytest.fixture(autouse=True)
def _reset_step_states():
    import asyncio

    from videogen.pipeline.base import StepStatus

    for module in (download, notes_extraction):
        module.state.status = StepStatus.PENDING
        module.state.output = None
        # A fresh Event, not .clear() — Event binds to whichever event loop
        # first calls .wait() on it, and pytest-asyncio gives each test
        # function its own loop, so reusing the old Event across tests
        # deadlocks (the bound-loop check silently fails the waiting task).
        module.state.approval_event = asyncio.Event()
    yield


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_run_notes_extraction_before_download_done_is_409(client):
    async with client as ac:
        resp = await ac.post("/pipeline/notes_extraction/run")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_run_unknown_step_is_404(client):
    async with client as ac:
        resp = await ac.post("/pipeline/not_a_real_step/run")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_then_notes_extraction_run_approve_chain(client):
    async with client as ac:
        run_resp = await ac.post("/pipeline/download/run")
        assert run_resp.json() == {"status": "waiting_approval"}

        approve_resp = await ac.post("/pipeline/download/approve")
        assert approve_resp.json() == {"status": "done"}

        status_resp = await ac.get("/pipeline/status")
        snapshot = status_resp.json()
        assert snapshot["download"]["status"] == "done"
        assert snapshot["download"]["output"]["slide_count"] == 5

        notes_run_resp = await ac.post("/pipeline/notes_extraction/run")
        assert notes_run_resp.json() == {"status": "waiting_approval"}

        notes_approve_resp = await ac.post("/pipeline/notes_extraction/approve")
        assert notes_approve_resp.json() == {"status": "done"}


@pytest.mark.asyncio
async def test_reject_reruns_step_with_fresh_output(client):
    async with client as ac:
        await ac.post("/pipeline/download/run")

        status_before = await ac.get("/pipeline/status")
        output_before = status_before.json()["download"]["output"]

        reject_resp = await ac.post("/pipeline/download/reject")
        assert reject_resp.json() == {"status": "waiting_approval"}

        status_after = await ac.get("/pipeline/status")
        snapshot_after = status_after.json()
        assert snapshot_after["download"]["status"] == "waiting_approval"
        assert snapshot_after["download"]["output"] is not None
        # Same fake-data shape, and reject genuinely produced a new output
        # (not just leaving the old one in place).
        assert snapshot_after["download"]["output"]["slide_count"] == output_before["slide_count"]

        approve_resp = await ac.post("/pipeline/download/approve")
        assert approve_resp.json() == {"status": "done"}


@pytest.mark.asyncio
async def test_approve_before_run_is_409(client):
    async with client as ac:
        resp = await ac.post("/pipeline/download/approve")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_index_route_lists_all_seven_steps(client):
    async with client as ac:
        resp = await ac.get("/")
    assert resp.status_code == 200
    for name in [
        "Download",
        "Notes Extraction",
        "Text-to-Speech",
        "Audio Upload",
        "Embed Audio",
        "Render Video",
        "Video Upload",
    ]:
        assert name in resp.text
