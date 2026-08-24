# Validation — Notes Extraction: Per-Slide Text Files + UI Links

This file is filled in during/after implementation (Plan.md task group 5).
Template below defines what "done" means.

## Automated validation

- [ ] `uv run pytest` passes in full, no regressions.
- [ ] `tests/test_notes_extraction.py`: `notes_file_paths` has one entry
      per slide; each file exists and its content exactly matches
      `notes[i]`, including an empty file for the empty-notes slide.
- [ ] New/updated route test: `GET
      /pipeline/notes_extraction/slide/{index}/notes` returns 200 with
      correct `text/plain` content post-run, 404 before any run, 404 for
      an out-of-range index.

## Regression validation

- [ ] Existing extraction-correctness and empty-notes-flagging tests
      still pass unmodified.
- [ ] `runner.py`/`tts.py` wiring unaffected (they don't consume
      `notes_file_paths`).

## Build / lint / static analysis

- [ ] `uv run pytest` (this repo's build/test gate).

## Manual verification

Performed by: _(fill in)_

1. Run `notes_extraction` against the real fixture deck through the
   browser UI.
2. Open each slide's link; confirm the content matches what's actually
   in the deck's notes (or is empty for the no-notes slide).

## Expected result

- Every slide gets a real `.txt` file on disk and a working UI link,
  including the empty-notes slide.

## Failure conditions

- Any slide's file content doesn't match its extracted `notes[i]` value.
- A slide is missing a file or a link.
- Any existing test regresses.

## Evidence the human should provide

- Confirmation of the manual verification steps above.
- `APPROVED` or `CHANGES REQUIRED` before this phase's implementation PR
  is merged.

## Result

_(fill in after implementation)_
