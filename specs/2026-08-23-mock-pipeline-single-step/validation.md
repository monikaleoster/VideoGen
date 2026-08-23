# Validation — Mock Pipeline, Single Step (Phase 1)

## How this phase succeeds

Per specs/roadmap.md's Phase 1 validation criteria: run the single stub
step via a route/CLI call, confirm it blocks, confirm it resumes after the
Event is manually set. Concretely, this phase is done when:

- [ ] `uv run pytest` passes, including the new notes-extraction unit
      tests and HTTP route integration tests, alongside Phase 0's
      existing tests.
- [ ] The notes-extraction step, run standalone, reaches
      `WAITING_APPROVAL` and provably does not proceed until its
      `asyncio.Event` is set (not just "usually finishes fast").
- [ ] Setting the Event lets the step resume to `DONE` with fake but
      well-shaped output (slide count + notes list).
- [ ] The same behavior is reachable two ways — via the CLI entry point
      and via the `run` / `approve` / `status` HTTP routes — without
      duplicated stub logic (both call into the same step function).
- [ ] No step-specific logic leaked into `app.py`'s route handlers; the
      step itself lives in `src/videogen/pipeline/`.

## Merge readiness checklist

- [ ] All items in "How this phase succeeds" are checked.
- [ ] CI (`.github/workflows/test.yml`) is green on the PR.
- [ ] `specs/roadmap.md` Phase 1 status updated to ✅.
- [ ] No leftover debug prints, TODOs without a follow-up phase
      reference, or dead code from earlier attempts.
- [ ] Manual verification section below is complete.

## Manual verification

Performed by: _(fill in — name/date)_

1. **CLI path**
   - Command run: `uv run python -m videogen.pipeline.notes_extraction`
     (adjust to match the actual entry point once implemented).
   - Observed output: _(paste status transitions — expect to see
     `RUNNING` → `WAITING_APPROVAL` → `DONE`, with fake output printed)_.
   - Confirmed the process did not exit/complete until the Event was set
     (not just a fixed sleep): _(yes/no + how confirmed)_.

2. **HTTP path**
   - Started the server: `uv run uvicorn videogen.app:app --reload` (or
     equivalent).
   - `curl -X POST localhost:8000/steps/notes-extraction/run` →
     _(paste response)_.
   - `curl localhost:8000/steps/notes-extraction/status` immediately
     after → confirmed status is `waiting_approval`, not `done`:
     _(yes/no)_.
   - `curl -X POST localhost:8000/steps/notes-extraction/approve` →
     _(paste response)_.
   - `curl localhost:8000/steps/notes-extraction/status` again →
     confirmed status is `done` with fake output present: _(yes/no)_.

3. **Negative case**
   - Called `approve` before `run` (or before reaching
     `waiting_approval`) → confirmed a clear error response, not a hang:
     _(paste response)_.

4. **Regression check**
   - `GET /health` and `/ws/echo` from Phase 0 still work unchanged:
     _(yes/no)_.

## Result

_(fill in once complete: PASS / FAIL, with a one-line summary and link to
the PR)_
