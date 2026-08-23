# Validation — Notes Extraction (Real) (Phase 6)

This file is filled in during/after implementation (Plan.md task group 5).
Template below defines what "done" means.

## Automated validation

- [x] `uv run pytest` passes in full, no regressions in any existing
      suite (download, runner, pipeline UI, etc.) — 28 passed.
- [x] Unit tests (`tests/test_notes_extraction.py`):
  - [x] Real extraction against the fixture deck returns the correct
        notes text for every slide with notes, exact match (after
        whitespace strip) against what's actually in the deck.
  - [x] Slide order is preserved — `notes[i]` corresponds to slide `i+1`.
  - [x] The empty-notes slide yields `notes[i] == ""` and
        `has_notes[i] is False`; the step completes normally (no
        exception, no crash) rather than erroring out.
  - [x] `slide_count` in the output matches `python-pptx`'s real slide
        count for the fixture deck.
  - [x] The step's approval gate still blocks until
        `state.approval_event` is set, then resumes and returns the same
        output (matching every other step's behavior).
- [x] Integration (`tests/test_runner.py`): full 7-step chain still
      completes correctly with `notes_extraction`'s real output threaded
      through `tts` (and beyond) with no ordering regressions.
- [x] `tests/test_pipeline_ui.py`: UI's `notes_extraction` Run/Approve/
      Reject flow still works against the real fixture deck.

## Regression validation

- [x] `download` step's existing tests still pass. Fixture change was
      made in-place (slide 3's speaker notes removed rather than adding a
      4th slide), keeping the 3-slide count `download`'s tests hardcode
      unaffected.

## Build / lint / static analysis

- [x] `uv run pytest` (build/test gate — this repo has no separate
      lint/typecheck step beyond what pytest covers).

## Bugs found and fixed along the way (required to make this phase's own validation possible, not scope creep)

- **Pre-existing bug from Phase 4**: `src/videogen/pipeline/__main__.py`
  still called `run_pipeline(drive_link=...)`, which Phase 4 had already
  renamed to `local_pptx_path`. The CLI entry point was broken on `main`
  before this phase; fixed as part of wiring the real `.pptx` path
  through (now points at the fixture, matching `ui.py`'s convention).
- **Legacy single-step demo route** (`src/videogen/pipeline/routes.py`,
  predating the Phase 3 pipeline UI): hardcoded `deck_name="demo-deck.pptx"`,
  a path that never existed on disk. Real `python-pptx` parsing would
  crash on it immediately. Updated to point at the same fixture.
- **Real race condition in test/CLI approval-simulation helpers**: both
  `tests/test_runner.py`'s `_approve_in_order` and
  `src/videogen/pipeline/__main__.py`'s `_watch_and_auto_approve_in_order`
  polled specifically for a step to be *observed* in `RUNNING` before
  moving on. The old stub steps all had an artificial `asyncio.sleep(0.1)`
  guaranteeing a wide observation window; real `notes_extraction` (a fast
  in-memory parse) can move from `RUNNING` to `WAITING_APPROVAL` between
  two 5ms poll ticks, so the poll could permanently miss `RUNNING` and
  hang forever waiting for a state that would never recur. Fixed both to
  poll for "left `PENDING`" instead of "hit `RUNNING`" — semantically
  equivalent for the ordering assertions, but race-free. Without this fix,
  `uv run pytest` and `uv run python -m videogen.pipeline` hung.

## Manual verification

Performed by: Claude (session, monikaleoster@gmail.com) — 2026-08-23

1. Ran `run_notes_extraction` directly (outside pytest) against the
   fixture deck: reached `waiting_approval` with `slide_count=3`,
   `notes=['Speaker notes for slide 1: Welcome.', 'Speaker notes for
   slide 2: Agenda.', '']`, `has_notes=[True, True, False]`. Approving
   resumed it to `done` with the same output.
2. Compared `notes[0]` and `notes[1]` against
   `tests/fixtures/generate_sample_deck.js`'s source notes text — exact
   match.
3. Confirmed slide 3 ("Thank You") has no speaker notes in the generator
   script (`notes: null`), matching its `notes[2] == ""` /
   `has_notes[2] is False` output — not crashed, not skipped, still
   gated on the same approval flow as slides 1-2.
4. Ran the full pipeline via `uv run python -m videogen.pipeline`
   end-to-end against the fixture: all 7 steps ran in order, each
   blocking for (simulated) approval, `notes_extraction`'s real output
   correctly visible in the log and threaded to `tts`.

## Expected result

- Every slide's extracted notes text matches the deck's actual speaker
  notes, in correct order.
- The empty-notes slide is flagged, not crashed on, and still gates on
  human approval exactly like every other slide/step.
- No regressions elsewhere in the pipeline.

## Failure conditions

- Any mismatch between extracted notes text and the deck's actual notes
  content (wrong slide, wrong text, unexpected transformation).
- The empty-notes slide raises an exception, silently skips approval, or
  is indistinguishable from a slide that has real (but coincidentally
  empty-after-strip) notes without the `has_notes` flag.
- Any existing test regresses.

## Evidence the human should provide

- Confirmation of the manual verification steps above (or a note on
  where they diverged).
- `APPROVED` or `CHANGES REQUIRED` per the human-validation gate before
  this phase's implementation PR is merged.

## Result

- Automated checks: done — 28/28 tests pass.
- Manual verification: done — real extraction produces correct,
  correctly-ordered notes text and correctly flags the empty-notes slide
  without crashing; full pipeline runs end-to-end.
- Outcome: ready to merge.

## Roadmap update

Phase 6 marked ✅ in `specs/roadmap.md`.
