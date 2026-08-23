# Plan — Mock Pipeline, Single Step (Phase 1)

Numbered task groups. Each group should leave the repo in a working,
test-passing state.

## 1. Pipeline step interface (`base.py`)

1.1. Create `src/videogen/pipeline/__init__.py` (empty, marks the
     package).

1.2. Create `src/videogen/pipeline/base.py`:
   - Define a `StepStatus` enum or `Literal` type:
     `PENDING`, `RUNNING`, `WAITING_APPROVAL`, `DONE`.
   - Define a small base shape (dataclass or Protocol) that every step's
     state follows: current `StepStatus`, an `asyncio.Event` for the
     approval gate, and a slot for the step's output once produced.
   - Keep this minimal — just enough structure for Phase 2 to reuse
     across six more steps, not a speculative generic step-runner.

## 2. Notes-extraction stub step

2.1. Create `src/videogen/pipeline/notes_extraction.py`:
   - `NotesExtractionInput` dataclass (e.g. a `deck_name: str` field —
     enough to be realistic without needing a real file).
   - `NotesExtractionOutput` dataclass (e.g. `slide_count: int`,
     `notes: list[str]` — fake data).
   - An async function (or small class) implementing the step: sets
     status to `RUNNING`, `await asyncio.sleep(...)` briefly, produces
     fake `NotesExtractionOutput`, sets status to `WAITING_APPROVAL`,
     `await`s the step's `asyncio.Event`, then sets status to `DONE` and
     returns the output.
   - Module-level (or small holder-class) instance so both the CLI and
     the HTTP routes can reach the same in-flight run and status.

2.2. Unit tests (`tests/test_notes_extraction.py`):
   - Running the step reaches `WAITING_APPROVAL` and does not proceed
     further while the Event is unset (assert with a timeout / task
     state, not a real sleep-and-hope).
   - Setting the Event lets the step resume and reach `DONE` with the
     expected fake output.

## 3. CLI entry point

3.1. Create `src/videogen/pipeline/__main__.py`:
   - Running `uv run python -m videogen.pipeline.notes_extraction` (or
     `python -m videogen.pipeline` — pick whichever matches how `base.py`
     ends up structured) starts the step, prints each status transition,
     and exits after approval + completion.
   - Approval in the CLI path can be simulated by immediately setting the
     Event after a short delay (since there's no UI yet) — document this
     inline as CLI-only scaffolding, not real approval logic.

3.2. Smoke-test the CLI manually (see validation.md) — not a pytest test,
     since it's an interactive/manual entry point.

## 4. HTTP routes

4.1. Add a router (e.g. `src/videogen/pipeline/routes.py`) with:
   - `POST /steps/notes-extraction/run`
   - `POST /steps/notes-extraction/approve`
   - `GET /steps/notes-extraction/status`

4.2. Wire the router into `src/videogen/app.py` via
     `app.include_router(...)`.

4.3. Integration tests (`tests/test_notes_extraction_routes.py`) using
     FastAPI's `TestClient`/`AsyncClient`:
   - `run` then `status` shows `waiting_approval`.
   - `approve` then `status` shows `done` with the fake output present.
   - Calling `approve` before `run` (or before reaching
     `waiting_approval`) returns a sensible error, not a hang or crash.

## 5. Wire-up check and docs

5.1. Run the full test suite (`uv run pytest`) — confirm Phase 0's tests
     still pass alongside the new ones.

5.2. Update `specs/roadmap.md`: flip Phase 1's status from ⬜ to ✅ once
     validation.md's checklist is complete.

5.3. Fill in `validation.md` with results, including the manual
     verification section.
