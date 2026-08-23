# Validation — Notes Extraction (Real) (Phase 6)

This file is filled in during/after implementation (Plan.md task group 5).
Template below defines what "done" means.

## Automated validation

- [ ] `uv run pytest` passes in full, no regressions in any existing
      suite (download, runner, pipeline UI, etc.).
- [ ] Unit tests (`tests/test_notes_extraction.py`):
  - [ ] Real extraction against the fixture deck returns the correct
        notes text for every slide with notes, exact match (after
        whitespace strip) against what's actually in the deck.
  - [ ] Slide order is preserved — `notes[i]` corresponds to slide `i+1`.
  - [ ] The empty-notes slide yields `notes[i] == ""` and
        `has_notes[i] is False`; the step completes normally (no
        exception, no crash) rather than erroring out.
  - [ ] `slide_count` in the output matches `python-pptx`'s real slide
        count for the fixture deck.
  - [ ] The step's approval gate still blocks until
        `state.approval_event` is set, then resumes and returns the same
        output (matching every other step's behavior).
- [ ] Integration (`tests/test_runner.py`): full 7-step chain still
      completes correctly with `notes_extraction`'s real output threaded
      through `tts` (and beyond) with no ordering regressions.
- [ ] `tests/test_pipeline_ui.py`: UI's `notes_extraction` Run/Approve/
      Reject flow still works against the real fixture deck.

## Regression validation

- [ ] `download` step's existing tests still pass unmodified (or with
      only the minimal fixture-related changes noted in Plan.md task
      group 1), confirming the fixture change (if made in-place) didn't
      alter its assumptions.

## Build / lint / static analysis

- [ ] `uv run pytest` (build/test gate — this repo has no separate
      lint/typecheck step beyond what pytest covers; if one is added
      later, it applies here too).

## Manual verification

Performed by: <fill in> — <date>

1. Run `run_notes_extraction` directly (outside pytest) against the
   fixture deck.
2. Confirm the step reaches `waiting_approval` with the correct
   `slide_count` and one `notes` entry + one `has_notes` entry per slide.
3. Manually compare each non-empty `notes[i]` value against the actual
   speaker-notes text visible when opening the fixture `.pptx` in an
   editor/viewer — confirm exact match (aside from the whitespace strip).
4. Confirm the empty-notes slide's entry is `""` / `has_notes=False`, and
   that approving the step still resumes it to `done` with the same
   output (no special-cased approval path was introduced).
5. Confirm the full pipeline (`run_pipeline`) still runs start to finish
   against the fixture deck with the real download + real notes
   extraction wired together, blocking on each step's approval gate in
   order.

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

Not yet run — implementation has not started. This section is filled in
after Plan.md's task group 5.

## Roadmap update

Not yet applied — `specs/roadmap.md` Phase 6 status stays ⬜ until this
validation is complete and the human has signed off.
