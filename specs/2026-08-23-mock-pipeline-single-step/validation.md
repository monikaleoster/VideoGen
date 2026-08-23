# Validation — Mock Pipeline, Single Step (Phase 1)

## How this phase succeeds

Per specs/roadmap.md's Phase 1 validation criteria: run the single stub
step via a route/CLI call, confirm it blocks, confirm it resumes after the
Event is manually set. Concretely, this phase is done when:

- [x] `uv run pytest` passes, including the new notes-extraction unit
      tests and HTTP route integration tests, alongside Phase 0's
      existing tests.
- [x] The notes-extraction step, run standalone, reaches
      `WAITING_APPROVAL` and provably does not proceed until its
      `asyncio.Event` is set (not just "usually finishes fast").
- [x] Setting the Event lets the step resume to `DONE` with fake but
      well-shaped output (slide count + notes list).
- [x] The same behavior is reachable two ways — via the CLI entry point
      and via the `run` / `approve` / `status` HTTP routes — without
      duplicated stub logic (both call into the same step function).
- [x] No step-specific logic leaked into `app.py`'s route handlers; the
      step itself lives in `src/videogen/pipeline/`.

## Merge readiness checklist

- [x] All items in "How this phase succeeds" are checked.
- [ ] CI (`.github/workflows/test.yml`) is green on the PR.
- [x] `specs/roadmap.md` Phase 1 status updated to ✅.
- [x] No leftover debug prints, TODOs without a follow-up phase
      reference, or dead code from earlier attempts.
- [x] Manual verification section below is complete.

## Manual verification

Performed by: Claude (session, monikaleoster@gmail.com) — 2026-08-23

1. **CLI path**
   - Command run: `uv run python -m videogen.pipeline` (the package's
     `__main__.py` entry point — `python -m videogen.pipeline.notes_extraction`
     was the originally sketched form, but the module itself has no
     `__main__` block, so the CLI lives at the package level per
     plan.md 3.1's "pick whichever matches how base.py ends up
     structured").
   - Observed output:
     ```
     [cli] status=pending
     [cli] status=running
     [cli] status=waiting_approval
     [cli] status=waiting_approval -> simulating approval
     [cli] status=done
     [cli] output=NotesExtractionOutput(slide_count=5, notes=["Fake notes for slide 1 of 'demo-deck.pptx'", "Fake notes for slide 2 of 'demo-deck.pptx'", "Fake notes for slide 3 of 'demo-deck.pptx'", "Fake notes for slide 4 of 'demo-deck.pptx'", "Fake notes for slide 5 of 'demo-deck.pptx'"])
     ```
   - Confirmed the process did not exit/complete until the Event was
     set: yes — the `WAITING_APPROVAL` line is printed by a status-poll
     task, then a 1-second real delay elapses (visible wall-clock gap)
     before the `-> simulating approval` line, and the automated test
     `test_step_blocks_until_approved` independently asserts the task
     is still not done 50ms after reaching `WAITING_APPROVAL` with the
     Event unset.

2. **HTTP path**
   - Started the server: `uv run uvicorn videogen.app:app --port 8123`.
   - `curl -X POST localhost:8123/steps/notes-extraction/run` →
     `{"status":"waiting_approval"}` [200]
   - `curl localhost:8123/steps/notes-extraction/status` immediately
     after → confirmed status is `waiting_approval`, not `done`: yes —
     `{"status":"waiting_approval","output":{"slide_count":5,"notes":[...]}}`
   - `curl -X POST localhost:8123/steps/notes-extraction/approve` →
     `{"status":"done"}` [200]
   - `curl localhost:8123/steps/notes-extraction/status` again →
     confirmed status is `done` with fake output present: yes —
     `{"status":"done","output":{"slide_count":5,"notes":[...]}}`

3. **Negative case**
   - Called `approve` before `run` → confirmed a clear error response,
     not a hang:
     `{"detail":"Step is not waiting for approval (status=pending)"}` [409]

4. **Regression check**
   - `GET /health` and `/ws/echo` from Phase 0 still work unchanged:
     yes — `GET /health` returned `{"status":"ok"}`, and Phase 0's
     `tests/test_app.py` (health + ws echo) still pass in the full
     `uv run pytest` run alongside the new tests.

## Result

PASS — the notes-extraction stub proves the step interface and the
asyncio.Event approval-gate mechanism via both the CLI entry point and
the `run`/`approve`/`status` HTTP routes, with no duplicated stub logic
and no regressions to Phase 0. 7/7 tests pass locally; CI status to be
confirmed once a PR is opened.
