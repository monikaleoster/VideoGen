# Plan — Approval-Gate UI (Phase 3)

Numbered task groups. Complete and validate each group before moving on.

## 1. Dependencies
1.1. Add `jinja2` to `pyproject.toml` dependencies (needed for
     `Jinja2Templates`, not previously required).
1.2. `uv sync` and confirm it installs cleanly.

## 2. Per-step dispatch layer
2.1. Create `src/videogen/pipeline/ui.py` with a `STEPS` list, in roadmap
     order, one entry per step: name, the step module, its `run_x`
     function, its `state`, its prerequisite step name(s) (`None` for
     `download`), and a `build_input()` callable that constructs that
     step's Input dataclass from the prerequisite step(s)' `state.output`
     (mirroring `runner.run_pipeline`'s chaining — same field mappings).
2.2. `download`'s `build_input()` uses a fixed demo `drive_link` string
     (no real Drive integration yet, per requirements.md).
2.3. Implement `get_snapshot()`: returns a dict of all 7 steps' `{status,
     output}` (dataclass output converted via `dataclasses.asdict`, `None`
     if not yet produced), keyed by step name.

## 3. HTTP routes
3.1. `GET /pipeline/status` → `get_snapshot()`.
3.2. `POST /pipeline/{step}/run`: 404 for an unknown step name; 409 if the
     prerequisite step isn't `DONE`; 409 if this step is already
     running/waiting_approval; otherwise build the input, `create_task`
     the step's `run_x`, wait until it reaches `WAITING_APPROVAL` or
     `DONE`, return its status.
3.3. `POST /pipeline/{step}/approve`: 409 if not `WAITING_APPROVAL`;
     otherwise set the approval event, wait until `DONE`, return status.
3.4. `POST /pipeline/{step}/reject`: 409 if not `WAITING_APPROVAL`;
     otherwise rebuild the same input and re-invoke `run_x` fresh (new
     `RUNNING` → `WAITING_APPROVAL` cycle, discarding the previous output),
     wait until `WAITING_APPROVAL` again, return status.
3.5. Mount this router in `src/videogen/app.py` alongside the existing
     Phase 1 notes-extraction router (left untouched).

## 4. WebSocket status push
4.1. `GET /ws/pipeline-status` (WebSocket): on connect, send the current
     snapshot immediately; then loop, checking the snapshot on a short
     interval (e.g. every 150ms) and sending it again only when it differs
     from the last one sent, until the client disconnects.

## 5. Page
5.1. Add `templates/index.html` (Jinja2): a list of all 7 steps in order,
     each row showing display name, status badge, output (pretty-printed),
     and Run/Approve/Reject buttons shown only when relevant to that
     step's current status.
5.2. Inline vanilla JS: connects to `/ws/pipeline-status`, re-renders the
     step list from each incoming snapshot; wires each button to a `fetch`
     POST against the matching route.
5.3. Mount `GET /` in `app.py` to render this template via
     `Jinja2Templates`.

## 6. Tests
6.1. `tests/test_pipeline_ui.py`: run→approve for `download`, confirm
     `notes_extraction` run is rejected with 409 before `download` is
     `DONE`, then confirm it succeeds once `download` is `DONE`.
6.2. Same file: reject `download` while `WAITING_APPROVAL`, confirm it
     re-enters `WAITING_APPROVAL` with a freshly produced output object
     (not the same Python object reference), then approve it.
6.3. `tests/test_index_route.py` (or added to the same file): `GET /`
     returns 200 and the response body contains all 7 steps' display
     names.
6.4. Run the full `uv run pytest` suite, confirm no regressions in
     Phase 0–2's existing tests.

## 7. Validation pass
7.1. Start the server, open `/` in a browser (or via the `run` skill),
     manually run → approve/reject each of the 7 steps in order, confirm
     the page updates live via the WebSocket without a manual refresh.
7.2. Fill in specs/2026-08-23-approval-gate-ui/validation.md with results.
7.3. Update Phase 3's status in specs/roadmap.md to ✅.
