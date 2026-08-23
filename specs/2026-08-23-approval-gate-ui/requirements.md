# Requirements — Approval-Gate UI (Phase 3)

## Context

Phase 0 (scaffold), Phase 1 (single mocked step), and Phase 2 (all 7 mocked
steps chained by `runner.py`) are done and merged. All seven steps exist as
stubs behind the same `StepState`/`asyncio.Event` approval-gate pattern, but
the only way to drive them today is `curl` or the FastAPI `/docs` Swagger
page — there is no purpose-built UI yet. This phase builds that UI: a single
browser page where a human can run each step, see its fake output, and
Approve or Reject it, per specs/mission.md's "no step auto-advances" and
specs/tech-stack.md's server-rendered-HTML-plus-WebSocket design.

This phase is UI-only. No step's fake logic changes; no real integrations
(Drive, ElevenLabs, python-pptx, ffmpeg) are touched — those stay deferred
to Phases 4+.

## Scope decisions (confirmed with user)

- **Trigger model:** per-step "Run" buttons — the user manually starts each
  of the 7 steps one at a time, rather than one "Start Pipeline" button that
  auto-chains all seven via `runner.run_pipeline`.
- **Layout:** a single list of all 7 steps, always visible top to bottom,
  each showing its current status and output. Not a "current step only"
  focus view.
- **Live updates:** server pushes over WebSocket. A `/ws/pipeline-status`
  route sends a JSON snapshot of all 7 steps' status/output whenever any
  step's state changes; the page re-renders whatever arrives. No client-side
  polling.
- **Reject behavior:** Reject re-runs that step fresh with the same input —
  discards its current output, resets it to running, and immediately calls
  the step's `run_x()` again with the same input it was given. Not just a
  reset-to-pending that waits for a separate manual re-run action.

## In scope

- A generic per-step dispatch layer (`src/videogen/pipeline/ui.py`) that:
  - Knows the 7 steps in roadmap order and how to build each one's input
    dataclass from the prior steps' already-stored outputs (mirroring
    `runner.run_pipeline`'s chaining, but one step at a time instead of
    all at once).
  - Exposes `POST /pipeline/{step}/run`, `POST /pipeline/{step}/approve`,
    `POST /pipeline/{step}/reject`, and `GET /pipeline/status` (all 7
    steps' status + output in one response).
  - Rejects (409) running a step whose prerequisite step isn't `DONE` yet,
    and rejects approving/rejecting a step that isn't `WAITING_APPROVAL`.
- `/ws/pipeline-status`: pushes the same all-steps snapshot as
  `GET /pipeline/status` whenever it changes, so the page stays live
  without the user refreshing.
- `templates/index.html` (Jinja2, server-rendered): lists all 7 steps with
  status, output, and the Run/Approve/Reject buttons relevant to each
  step's current state; vanilla JS connects to the WebSocket and posts to
  the run/approve/reject routes via `fetch`.
- Tests covering: the prerequisite gate (running step 2 before step 1 is
  done fails with 409), the full run→approve chain for at least two
  adjacent steps, reject-then-approve producing a fresh output, and the
  index route serving a page that names all 7 steps.

## Out of scope

- Any change to the 7 steps' fake-data logic, or to Phase 1's existing
  `/steps/notes-extraction/*` routes (left untouched).
- Real Google Drive input for the `download` step — its `drive_link` input
  stays a hardcoded demo string, same as the other steps' hardcoded fake
  data, since Phase 4 is where real Drive integration lands.
- Auth, multi-user support, or persisting run history — single in-flight
  run per step, matching the existing module-level `state` pattern.
- A "Start Pipeline" button that auto-chains all 7 steps — explicitly
  rejected in favor of per-step Run buttons (see scope decisions above).

## Constraints (from specs/tech-stack.md and specs/mission.md)

- Server-rendered HTML (Jinja2) + vanilla JS, no SPA framework, no frontend
  build step.
- WebSocket for live status push (native FastAPI WebSocket support).
- No step auto-advances without explicit human approval — Approve/Reject
  buttons are the only way a step moves past `WAITING_APPROVAL`.
- Every step still stands alone: the dispatch layer only orchestrates
  input-building and route wiring; no step-specific fake-data logic moves
  into it or into the route handlers.
