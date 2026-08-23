# Plan — Notes Extraction (Real) (Phase 6)

Numbered task groups. Complete and validate each group before moving on.

## 1. Fixture deck update
- Objective: have a real `.pptx` fixture that exercises both a populated
  and an empty-notes slide, without breaking existing `download`-step
  tests that assert exact content/count on `sample_deck.pptx`.
- Tasks:
  1.1. Decide fixture approach: add an empty-notes slide to
       `tests/fixtures/sample_deck.pptx` (if `download`-step tests don't
       hardcode "all 3 slides have notes"), or add a second fixture
       (e.g. `tests/fixtures/sample_deck_with_empty_notes.pptx`) used only
       by notes-extraction tests.
  1.2. Build the fixture with a notes-generation script consistent with
       how `sample_deck.pptx` was originally created, so it stays
       regeneratable rather than a one-off binary with no provenance.
- Dependencies: none.
- Files affected: `tests/fixtures/`.
- Validation: fixture opens correctly under `python-pptx`; manual
  inspection confirms which slide(s) have notes and which don't.
- Independent: yes — can be done first, standalone.

## 2. Real `notes_extraction` step
- Objective: replace the stub with real `python-pptx`-backed extraction.
- Tasks:
  2.1. Change `NotesExtractionInput` to carry the real `.pptx` path
       (rename/repurpose `deck_name`), keep `slide_image_paths` if still
       needed downstream, drop the now-unnecessary `slide_count` default
       trust (see requirements: real slide count comes from `python-pptx`,
       not the caller).
  2.2. In `run_notes_extraction`: open the deck with `python-pptx`,
       iterate slides in order, read each slide's notes-slide text if
       present, strip leading/trailing whitespace.
  2.3. Build `NotesExtractionOutput` with `slide_count` (from
       `python-pptx`), `notes: list[str]` (stripped text, `""` if none),
       and a parallel `has_notes: list[bool]` flag per slide.
  2.4. Keep the same `StepState`/`StepStatus`/`asyncio.Event`
       approval-gate shape as every other step.
- Dependencies: task group 1 (needs the fixture to test against).
- Files affected: `src/videogen/pipeline/notes_extraction.py`.
- Validation: unit tests in group 4.
- Independent: no — depends on group 1's fixture decision.

## 3. Wire the new input/output shape through
- Tasks:
  3.1. Update `runner.py`'s call to `notes_extraction.run_notes_extraction`
       to pass the real `.pptx` path from `download_output`.
  3.2. Update `tts.py`'s input construction if it relied on the old
       `NotesExtractionOutput.notes` shape assuming no empty-string
       entries (check whether TTS needs to skip/handle empty notes
       differently — if so, flag as a blocker per Stop Conditions, since
       that would be new product behavior beyond this phase's scope; if
       TTS already tolerates an empty string per-slide with no special
       casing needed, no change required).
  3.3. Update `ui.py`'s demo/manual-run wiring if it hardcodes any
       notes-extraction input shape that no longer matches.
- Dependencies: task group 2.
- Files affected: `src/videogen/pipeline/runner.py`,
  `src/videogen/pipeline/ui.py`, possibly `src/videogen/pipeline/tts.py`
  (read-only check, not a scope change).
- Validation: `uv run pytest` full suite still passes end-to-end.
- Independent: no — depends on group 2.

## 4. Tests
- Tasks:
  4.1. `tests/test_notes_extraction.py`: real extraction against the
       fixture returns correct per-slide notes text (exact match after
       whitespace strip) in correct slide order; the empty-notes slide
       has `notes[i] == ""` and `has_notes[i] is False`; `slide_count`
       matches the fixture's real slide count; the step's approval gate
       still blocks/resumes correctly via `asyncio.Event`.
  4.2. `tests/test_runner.py`: update any calls/assumptions tied to the
       old stub shape.
  4.3. `tests/test_pipeline_ui.py`: update any hardcoded notes-related
       assumptions left over from the stub.
  4.4. Run the full `uv run pytest` suite, confirm no regressions.
- Dependencies: task groups 1-3.
- Files affected: `tests/test_notes_extraction.py` (new or updated),
  `tests/test_runner.py`, `tests/test_pipeline_ui.py`.
- Validation: all tests pass, including the new empty-notes assertions.
- Independent: no — depends on the implementation being in place.

## 5. Validation pass
- Tasks:
  5.1. Run real extraction manually against the fixture deck outside
       pytest, confirm notes text and empty-notes flag by hand.
  5.2. Fill in `specs/2026-08-23-notes-extraction-real/validation.md`.
  5.3. Update Phase 6's status in `specs/roadmap.md` to ✅.
- Dependencies: task groups 1-4.
- Files affected: `specs/2026-08-23-notes-extraction-real/validation.md`,
  `specs/roadmap.md`.
- Independent: no — final step.

## Delegable task groups

Groups 1 and 4 are independent enough to delegate to separate agents once
group 2's output shape is settled (group 4 needs group 2 done first, so
in practice: group 1 can start immediately/independently; groups 2-5 are
sequential given their dependencies).
