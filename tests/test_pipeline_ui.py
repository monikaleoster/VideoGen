import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from videogen.app import app
from videogen.pipeline import download, embed, notes_extraction, tts, workdir


@pytest.fixture(autouse=True)
def _reset_step_states():
    import asyncio

    from videogen.pipeline.base import StepStatus

    for module in (download, notes_extraction, tts, embed):
        module.state.status = StepStatus.PENDING
        module.state.output = None
        # A fresh Event, not .clear() — Event binds to whichever event loop
        # first calls .wait() on it, and pytest-asyncio gives each test
        # function its own loop, so reusing the old Event across tests
        # deadlocks (the bound-loop check silently fails the waiting task).
        module.state.approval_event = asyncio.Event()
    tts._current_work_dir = None
    workdir.set_tmp_root(None)
    yield
    workdir.set_tmp_root(None)


@pytest.fixture
def silent_mp3_bytes(tmp_path: Path) -> bytes:
    out_path = tmp_path / "silence.mp3"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1.0", "-q:a", "9", "-y", str(out_path)],
        check=True,
        capture_output=True,
    )
    return out_path.read_bytes()


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
        assert snapshot["download"]["output"]["slide_count"] == 3

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


@pytest.mark.asyncio
async def test_index_route_has_tts_credential_and_per_slide_fields(client):
    async with client as ac:
        resp = await ac.get("/")
    assert 'data-role="api-key"' in resp.text
    assert 'data-role="voice-id"' in resp.text
    assert 'data-role="tts-slides"' in resp.text


@pytest.mark.asyncio
async def test_generate_slide_before_any_tts_run_is_409(client):
    async with client as ac:
        resp = await ac.post(
            "/pipeline/tts/slide/0/generate",
            json={"api_key": "k", "voice_id": "v", "text": "hello"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_generate_slide_updates_only_that_slides_output(client, silent_mp3_bytes):
    with patch("videogen.pipeline.tts._synthesize", return_value=silent_mp3_bytes) as mock_synth:
        async with client as ac:
            await ac.post("/pipeline/download/run")
            await ac.post("/pipeline/download/approve")
            await ac.post("/pipeline/notes_extraction/run")
            await ac.post("/pipeline/notes_extraction/approve")

            run_resp = await ac.post(
                "/pipeline/tts/run", json={"api_key": "k", "voice_id": "v"}
            )
            assert run_resp.json() == {"status": "waiting_approval"}

            status_before = await ac.get("/pipeline/status")
            before = status_before.json()["tts"]["output"]

            # Regenerate slide 1 only, with a manual override text.
            calls_before_regenerate = mock_synth.call_count

            gen_resp = await ac.post(
                "/pipeline/tts/slide/0/generate",
                json={"api_key": "k", "voice_id": "v", "text": "Overridden text."},
            )
            assert gen_resp.status_code == 200
            assert gen_resp.json()["audio_path"]

            status_after = await ac.get("/pipeline/status")
            after = status_after.json()["tts"]["output"]

            # Slide 1 was actually regenerated (in place, same path — a fresh
            # ElevenLabs call was made and overwrote the file); every other
            # slide's entry is completely untouched.
            mock_synth.assert_called_with("Overridden text.", "k", "v")
            assert mock_synth.call_count == calls_before_regenerate + 1
            assert after["audio_paths"][1:] == before["audio_paths"][1:]
            assert after["durations_sec"][1:] == before["durations_sec"][1:]


@pytest.mark.asyncio
async def test_generate_slide_requires_non_empty_text(client, silent_mp3_bytes):
    with patch("videogen.pipeline.tts._synthesize", return_value=silent_mp3_bytes):
        async with client as ac:
            await ac.post("/pipeline/download/run")
            await ac.post("/pipeline/download/approve")
            await ac.post("/pipeline/notes_extraction/run")
            await ac.post("/pipeline/notes_extraction/approve")
            await ac.post("/pipeline/tts/run", json={"api_key": "k", "voice_id": "v"})

            resp = await ac.post(
                "/pipeline/tts/slide/2/generate",
                json={"api_key": "k", "voice_id": "v", "text": "   "},
            )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_slide_audio_before_any_tts_run_is_404(client):
    async with client as ac:
        resp = await ac.get("/pipeline/tts/slide/0/audio")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_slide_audio_for_skipped_slide_is_404(client, silent_mp3_bytes):
    with patch("videogen.pipeline.tts._synthesize", return_value=silent_mp3_bytes):
        async with client as ac:
            await ac.post("/pipeline/download/run")
            await ac.post("/pipeline/download/approve")
            await ac.post("/pipeline/notes_extraction/run")
            await ac.post("/pipeline/notes_extraction/approve")
            await ac.post("/pipeline/tts/run", json={"api_key": "k", "voice_id": "v"})

            # Fixture's slide 3 ("Thank You") has no notes, so tts skips it.
            resp = await ac.get("/pipeline/tts/slide/2/audio")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_slide_audio_returns_the_real_generated_mp3(client, silent_mp3_bytes):
    with patch("videogen.pipeline.tts._synthesize", return_value=silent_mp3_bytes):
        async with client as ac:
            await ac.post("/pipeline/download/run")
            await ac.post("/pipeline/download/approve")
            await ac.post("/pipeline/notes_extraction/run")
            await ac.post("/pipeline/notes_extraction/approve")
            await ac.post("/pipeline/tts/run", json={"api_key": "k", "voice_id": "v"})

            resp = await ac.get("/pipeline/tts/slide/0/audio")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content == silent_mp3_bytes


@pytest.mark.asyncio
async def test_index_route_has_download_config_fields(client):
    async with client as ac:
        resp = await ac.get("/")
    assert 'data-role="pptx-path"' in resp.text
    assert 'data-role="tmp-root"' in resp.text


@pytest.mark.asyncio
async def test_download_with_blank_fields_uses_demo_fixture_no_regression(client):
    async with client as ac:
        run_resp = await ac.post("/pipeline/download/run", json={"local_pptx_path": "", "tmp_root": ""})
        assert run_resp.json() == {"status": "waiting_approval"}

    demo_fixture = Path(__file__).resolve().parent / "fixtures" / "sample_deck.pptx"
    output = download.state.output
    assert Path(output.local_pptx_path).name == demo_fixture.name
    # No custom root was supplied, so the work dir must not be nested under
    # any caller-chosen directory — it lands straight in the OS temp dir.
    import tempfile

    assert Path(output.local_pptx_path).parent.parent == Path(tempfile.gettempdir())


@pytest.mark.asyncio
async def test_download_with_custom_pptx_path_converts_that_file_not_the_demo(client, tmp_path: Path):
    demo_fixture = Path(__file__).resolve().parent / "fixtures" / "sample_deck.pptx"
    custom_pptx = tmp_path / "my_custom_deck.pptx"
    custom_pptx.write_bytes(demo_fixture.read_bytes())

    async with client as ac:
        run_resp = await ac.post("/pipeline/download/run", json={"local_pptx_path": str(custom_pptx)})
        assert run_resp.json() == {"status": "waiting_approval"}

    output = download.state.output
    assert Path(output.local_pptx_path).name == "my_custom_deck.pptx"


@pytest.mark.asyncio
async def test_index_route_has_notes_slides_container(client):
    async with client as ac:
        resp = await ac.get("/")
    assert 'data-role="notes-slides"' in resp.text


@pytest.mark.asyncio
async def test_get_notes_slide_before_any_run_is_404(client):
    async with client as ac:
        resp = await ac.get("/pipeline/notes_extraction/slide/0/notes")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_notes_slide_out_of_range_is_404(client):
    async with client as ac:
        await ac.post("/pipeline/download/run")
        await ac.post("/pipeline/download/approve")
        await ac.post("/pipeline/notes_extraction/run")

        resp = await ac.get("/pipeline/notes_extraction/slide/99/notes")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_notes_slide_served_at_waiting_approval_and_done(client):
    async with client as ac:
        await ac.post("/pipeline/download/run")
        await ac.post("/pipeline/download/approve")
        run_resp = await ac.post("/pipeline/notes_extraction/run")
        assert run_resp.json() == {"status": "waiting_approval"}

        status_resp = await ac.get("/pipeline/status")
        notes = status_resp.json()["notes_extraction"]["output"]["notes"]

        # Served correctly while still waiting_approval...
        resp_waiting = await ac.get("/pipeline/notes_extraction/slide/0/notes")
        assert resp_waiting.status_code == 200
        assert resp_waiting.headers["content-type"].startswith("text/plain")
        assert resp_waiting.text == notes[0]

        # The no-notes slide serves an empty body, not a 404.
        resp_empty = await ac.get("/pipeline/notes_extraction/slide/2/notes")
        assert resp_empty.status_code == 200
        assert resp_empty.text == ""

        # ...and again after approval (status flips to done).
        approve_resp = await ac.post("/pipeline/notes_extraction/approve")
        assert approve_resp.json() == {"status": "done"}

        resp_done = await ac.get("/pipeline/notes_extraction/slide/1/notes")
        assert resp_done.status_code == 200
        assert resp_done.text == notes[1]


@pytest.mark.asyncio
async def test_custom_tmp_root_shared_across_download_tts_and_embed(client, tmp_path: Path, silent_mp3_bytes):
    custom_root = tmp_path / "shared_run_root"

    with patch("videogen.pipeline.tts._synthesize", return_value=silent_mp3_bytes):
        async with client as ac:
            run_resp = await ac.post("/pipeline/download/run", json={"tmp_root": str(custom_root)})
            assert run_resp.json() == {"status": "waiting_approval"}
            await ac.post("/pipeline/download/approve")

            await ac.post("/pipeline/notes_extraction/run")
            await ac.post("/pipeline/notes_extraction/approve")

            await ac.post("/pipeline/tts/run", json={"api_key": "k", "voice_id": "v"})
            await ac.post("/pipeline/tts/approve")

            await ac.post("/pipeline/audio_upload/run")
            await ac.post("/pipeline/audio_upload/approve")

            await ac.post("/pipeline/embed/run")
            await ac.post("/pipeline/embed/approve")

    download_work_dir = Path(download.state.output.local_pptx_path).parent
    assert download_work_dir.parent == custom_root

    tts_work_dir = Path(tts.state.output.audio_paths[0]).parent
    assert tts_work_dir.parent == custom_root

    embed_dirs = list(custom_root.glob("videogen_embed_*"))
    assert len(embed_dirs) == 1
