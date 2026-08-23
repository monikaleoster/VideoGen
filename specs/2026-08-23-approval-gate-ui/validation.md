# Validation — Approval-Gate UI (Phase 3)

This file is filled in once implementation (plan.md) is complete. It's the
merge gate for this feature branch: nothing here should stay unchecked when
the PR is proposed for merge.

## Automated checks

- [x] `uv sync` installs cleanly with `jinja2` added.
- [x] `uv run pytest` passes (28 passed), including:
  - [x] Prerequisite gate: running `notes_extraction` before `download` is
        `DONE` returns 409 (`test_run_notes_extraction_before_download_done_is_409`).
  - [x] Run → approve chain succeeds for `download` then `notes_extraction`
        (`test_download_then_notes_extraction_run_approve_chain`).
  - [x] Reject re-runs a step fresh (new output, same shape) and it can
        then be approved (`test_reject_reruns_step_with_fresh_output`).
  - [x] `GET /` returns 200 and names all 7 steps
        (`test_index_route_lists_all_seven_steps`).
  - [x] Unknown step name (404) and approve-before-run (409) also covered.
  - [x] No regressions: all 22 of Phase 0-2's existing tests still pass
        alongside the 6 new ones.

Note: the first attempt at these tests hung the whole suite. Root cause —
the test fixture called `state.approval_event.clear()` instead of
assigning a fresh `asyncio.Event()`; since pytest-asyncio gives each test
function its own event loop and `Event` binds to whichever loop first
calls `.wait()` on it, reusing the old Event across tests silently
deadlocked a later test's background task. Fixed by assigning a new
`asyncio.Event()` per test, matching the pattern already used in
`test_notes_extraction.py` and `test_runner.py`.

## Manual verification

Performed by: Claude (session, monikaleoster@gmail.com) — 2026-08-23

1. Started the server (`uv run uvicorn videogen.app:app --port 8321`).
   `GET /health` → `{"status":"ok"}`; `GET /` returned the page with all 7
   `data-step="..."` rows present (`download`, `notes_extraction`, `tts`,
   `audio_upload`, `embed`, `render`, `video_upload`) and
   `GET /pipeline/status` showed all 7 steps as `pending` with `null`
   output.
2. Drove the full pipeline via `curl`, in order, for all 7 steps: `run` →
   `reject` → `approve` for each. Every step: `run` returned
   `waiting_approval`, `reject` produced a fresh `waiting_approval` (new
   output), `approve` returned `done`. Final `GET /pipeline/status` showed
   all 7 steps `done` with fully-populated fake output (5 slide images,
   5 notes, 5 audio clips + durations, 5 Drive file IDs/URLs, embed
   confirmation, a rendered video path/duration, and a final video Drive
   URL) — matches `runner.py`'s chaining exactly (e.g. `notes_extraction`'s
   notes reference `download`'s `local_pptx_path`).
3. Confirmed the prerequisite gate and error paths on a fresh server
   instance: `POST /pipeline/tts/run` before `download` is done → 409;
   `POST /pipeline/download/approve` before any `run` → 409;
   `POST /pipeline/nope/run` (unknown step) → 404.
4. Confirmed the WebSocket push directly (Python `websockets` script):
   connected to `/ws/pipeline-status`, received an initial `pending`
   snapshot, then triggered `POST /pipeline/download/run` from a separate
   client — the socket pushed an updated snapshot (`download` →
   `running`) without any client poll, proving the push is driven by the
   server noticing the state change, not by the HTTP response.
5. Did not re-verify the same steps by clicking through and eyeballing an
   actual browser window (no interactive browser available in this
   environment) — the curl + WebSocket-script verification above exercises
   the identical HTTP/WebSocket surface the page's JS calls into, so the
   remaining risk is confined to the front-end JS/DOM wiring itself
   (`templates/index.html`), which was reviewed by hand but not
   click-tested.

## Result

- Automated checks: done — 28/28 tests pass, including all 6 new
  Phase 3 tests and zero regressions.
- Manual verification: done for the HTTP/WebSocket surface (steps 1-4
  above); browser click-through not performed (no browser available in
  this environment) — flagged as the one open item in step 5.
- Outcome: ready to merge, with the caveat that a human should click
  through the actual page once (steps 2-8 of the original manual-check
  list) before fully trusting the front-end wiring, since that part
  wasn't exercised end-to-end here.

## Roadmap update

Once this phase is fully validated, mark Phase 3 as ✅ in specs/roadmap.md.
