# Requirements — Mock Pipeline, All 7 Steps (Phase 2)

## Context

This is Phase 2 of specs/roadmap.md, building directly on Phase 1
(`src/videogen/pipeline/`: the `Step`/`StepState` shape in `base.py`, and
`notes_extraction.py` as the one proven stub step, driven via both a CLI
entry point and per-step HTTP routes). Per specs/mission.md's "prove the
shape before the substance" principle, this phase extends Phase 1's exact
pattern — stub step + `asyncio.Event` approval gate — to all seven pipeline
steps (download, notes extraction, TTS, audio upload, embed, render, video
upload), chained by a single pipeline runner, before any step goes real
(Phases 4-9).

## Scope decisions (confirmed with user)

- **Invocation:** CLI runner only. `python -m videogen.pipeline` drives all
  seven steps in order end-to-end, auto-approving each step after a short
  delay (same "CLI-only scaffolding, not real approval logic" pattern
  Phase 1 used). No new HTTP routes are added in this phase — Phase 1's
  existing `/steps/notes-extraction/*` routes are left as-is, untouched,
  and are not extended to the other six steps. Per-step/pipeline HTTP
  routes are Phase 3's concern, once the real approval-gate UI needs
  something to call.
- **Observability:** Maximum observability in the CLI runner. Use Python's
  `logging` module (not bare `print`, which Phase 1's CLI used) so every
  status transition for every step is logged with the step name, a
  timestamp, and enough context to follow the whole run's progress from
  the terminal without extra flags. Log at least: run start, each step's
  `RUNNING` / `WAITING_APPROVAL` / (simulated) approval / `DONE`
  transition with its fake output summary, and run completion.
- **Fake output shape:** Plausible per-step fields, not generic
  placeholders — each step's output dataclass resembles what the real step
  will eventually produce, so Phases 4-9 have a concrete real output to
  slot in later:
  - Download → local file path(s) for the downloaded `.pptx` and a
    slide-image path per slide, plus slide count.
  - Notes extraction → per-slide notes list (already exists from Phase 1;
    reused as-is).
  - TTS → per-slide fake audio file path and a fake duration (seconds).
  - Audio upload → per-slide fake Drive file ID/URL for the uploaded
    audio clip.
  - Embed → fake path to the updated `.pptx` with audio embedded, plus a
    per-slide "audio embedded: true" flag.
  - Render → fake path to the final `.mp4` and a fake total duration.
  - Video upload → fake Drive file ID/URL for the uploaded final video.
- **Step chaining:** Chained, not independent. The runner passes each
  step's fake output forward as the next step's input (e.g. download's
  fake slide count and slide-image paths feed notes extraction's input;
  notes extraction's fake notes feed TTS's input; and so on through video
  upload). This proves the runner's data-passing shape between steps, not
  just that steps run in order. Each step's *content* is still fake/stub
  data — only the wiring between steps is real.
- **Concurrency:** Single in-flight run, matching Phase 1's model. A
  module-level (or single-holder-class) instance holds all seven steps'
  state for one run at a time. Multiple concurrent runs are out of scope
  until a later phase's requirements call for it.

## In scope

- `src/videogen/pipeline/` gains six new stub step modules, one per
  remaining step, each following `notes_extraction.py`'s established
  shape (typed `*Input`/`*Output` dataclasses, an async function that
  transitions `PENDING` → `RUNNING` → produces fake output →
  `WAITING_APPROVAL` → blocks on its own `asyncio.Event` → `DONE`):
  - `download.py`
  - `tts.py`
  - `audio_upload.py`
  - `embed.py`
  - `render.py`
  - `video_upload.py`
- A pipeline **runner** (e.g. `src/videogen/pipeline/runner.py`) that:
  - Holds all seven steps' `StepState` instances for one run.
  - Runs the seven steps in the fixed roadmap order: download → notes
    extraction → TTS → audio upload → embed → render → video upload.
  - Passes each completed step's fake output into the next step's input,
    per the chaining decision above.
  - Does not start a step until the previous step has reached `DONE`
    (i.e. its approval Event has been set and it has resumed) — no step
    skips ahead.
- CLI entry point (`src/videogen/pipeline/__main__.py`, extending Phase
  1's) that runs the full seven-step runner, logs every transition via
  `logging`, and auto-approves each step after a short delay so the whole
  run completes unattended for validation purposes.
- pytest tests (async) covering:
  - Each of the six new stub steps individually: blocks at
    `WAITING_APPROVAL`, resumes and reaches `DONE` with well-shaped fake
    output once its Event is set (same shape as Phase 1's
    `notes_extraction` tests).
  - The runner: all seven steps execute in the correct order; a step
    never starts before the previous one reaches `DONE`; each step's fake
    output is correctly threaded into the next step's input (assert on at
    least one chained field per hop, e.g. slide count staying consistent
    from download through render).
  - The full run completes end-to-end when every step's Event is set in
    order (simulating sequential approval).

## Out of scope

- Any new or extended HTTP routes for the six new steps or the runner —
  Phase 1's single-step routes are left untouched; full route coverage
  is Phase 3's concern once the UI needs it.
- Any real approval-gate UI (HTML/JS, live WebSocket status) — Phase 3.
- Real implementations of any step's logic (Drive download, python-pptx
  notes/embed, ElevenLabs TTS, LibreOffice conversion, ffmpeg render,
  Drive upload) — Phases 4-9, one step at a time.
- Persistence of run state across process restarts, or support for
  multiple concurrent pipeline runs — not needed until a later phase's
  requirements call for it.
- Reject/re-run behavior beyond what Phase 1 already proved (the runner
  only needs to prove forward chaining through approval in this phase;
  reject-and-re-run wiring is Phase 3's UI concern).

## Constraints (from specs/tech-stack.md and specs/mission.md)

- Steps are independent, individually callable async functions (or a
  small class per step), never logic inlined into the runner or route
  handlers — each of the seven stays a standalone, testable unit per
  mission.md's "every step stands alone" principle.
- One `asyncio.Event` per step is the block/unblock mechanism; no step
  auto-advances — every step must genuinely block until its Event is set,
  not merely simulate blocking with a delay.
- The runner orchestrates the steps; it does not contain step-specific
  logic itself (per tech-stack.md: "orchestrated by a single pipeline
  runner — never as logic inlined into route handlers").
- Tests run via pytest + pytest-asyncio, independent of any external
  network access (nothing in this phase touches Drive, ElevenLabs,
  python-pptx, LibreOffice, or ffmpeg — all still fake/stub data).
