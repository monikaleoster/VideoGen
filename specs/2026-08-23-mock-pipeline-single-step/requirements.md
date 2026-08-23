# Requirements — Mock Pipeline, Single Step (Phase 1)

## Context

This is Phase 1 of specs/roadmap.md, building directly on the Phase 0
scaffold (`src/videogen/app.py`: FastAPI app with `GET /health` and
`/ws/echo`). Per specs/mission.md's "prove the shape before the substance"
principle, this phase proves the pipeline step interface and the
approval-gate block/unblock mechanism using exactly one stubbed step,
before Phase 2 extends the same pattern to all seven steps.

## Scope decisions (confirmed with user)

- **Which step:** Notes extraction is the one step stubbed in this phase.
  This matches the roadmap's own example and sets up Phase 6 (making
  notes extraction real) to be the first "real step" phase to land.
- **Step interface:** A plain async function per specs/tech-stack.md
  ("Pipeline steps are implemented as independent, individually callable
  async functions... never as logic inlined into route handlers"). Input
  and output are typed dataclasses (`NotesExtractionInput`,
  `NotesExtractionOutput`), not raw dicts.
- **Invocation for validation:** A small CLI script
  (`python -m videogen.pipeline.notes_extraction`, or an equivalent
  `__main__` entry point in the pipeline package) drives the step
  standalone, without requiring the FastAPI server. This is the primary
  way Phase 1's behavior is validated (per mission.md's "every step
  stands alone" principle) — no route is required just to run the step.
- **Approval unblock mechanism:** In addition to the CLI path, a FastAPI
  route pair is added so the same step can be driven and approved over
  HTTP, which is the shape Phase 3's UI will eventually call into:
  - `POST /steps/notes-extraction/run` — starts the step; step runs until
    it reaches "done, waiting for approval" and blocks on its
    `asyncio.Event`.
  - `POST /steps/notes-extraction/approve` — sets the Event, letting the
    blocked step resume and complete.
  - `GET /steps/notes-extraction/status` — returns the current status
    (`running` / `waiting_approval` / `done`) and, once available, the
    stub's fake output.
  Step state for this phase is held in a single in-process instance
  (module-level), not persisted — that's acceptable because Phase 1 only
  proves the mechanism with one step and one run at a time; concurrent
  runs and persistence are not addressed until later phases need them.

## In scope

- `src/videogen/pipeline/` package:
  - `base.py` — the step interface: a `Step` protocol/base shape common
    to input, output, and status, so Phase 2's six additional steps can
    follow the same shape.
  - `notes_extraction.py` — the one stubbed step: returns fake notes data
    after a short `asyncio.sleep`, then blocks on an `asyncio.Event` until
    approved.
  - `__main__.py` (or a `cli.py` invoked via `__main__`) — CLI entry point
    that runs the step standalone and prints its status transitions.
- FastAPI routes (`run` / `approve` / `status`) wired into `app.py` (or a
  new router module included by `app.py`), covering the same step.
- pytest tests (async) covering:
  - The step blocks after reporting "waiting for approval".
  - The step resumes and completes once its Event is set.
  - Both CLI invocation and the three HTTP routes exercise the same
    underlying step function (no duplicated stub logic).

## Out of scope

- The other six pipeline steps (download, TTS, audio upload, embed,
  render, video upload) — Phase 2.
- Any real approval-gate UI (HTML/JS, live WebSocket status) — Phase 3.
  The HTTP routes in this phase exist to prove the mechanism, not to be
  user-facing.
- A pipeline *runner* that chains multiple steps — Phase 2, once more
  than one step exists to chain.
- Persistence of step state across process restarts, or support for
  multiple concurrent runs of the same step — not needed until a later
  phase's requirements call for it.
- Any real notes-extraction logic (`python-pptx` parsing) — Phase 6.

## Constraints (from specs/tech-stack.md and specs/mission.md)

- Steps are independent, individually callable async functions (or a
  small class per step), never logic inlined into route handlers.
- One `asyncio.Event` per step is the block/unblock mechanism; the
  Approve action sets it.
- No step auto-advances — the stub must genuinely block until approved,
  not merely simulate blocking with a delay.
- Tests run via pytest + pytest-asyncio, independent of any external
  network access (nothing in this phase touches Drive, ElevenLabs,
  python-pptx, or ffmpeg).
