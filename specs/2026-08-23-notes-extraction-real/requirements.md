# Requirements — Notes Extraction (Real) (Phase 6)

## Context

Phases 0-4 are done and merged: scaffold, all 7 mocked pipeline steps, the
approval-gate UI, and the real `download` step (local `.pptx` path ->
LibreOffice-rendered slide images). This phase replaces the mock
`notes_extraction` step with real `python-pptx` parsing of each slide's
speaker notes, per `specs/roadmap.md` Phase 6 and `specs/tech-stack.md`'s
stated use of `python-pptx` for reading speaker notes.

## User-provided requirements (confirmed 2026-08-23)

- **Extraction:** pull each slide's raw speaker-notes text via
  `python-pptx`. Minimal cleaning only — strip leading/trailing whitespace
  from the notes text as a whole. Internal line breaks/paragraph structure
  within the notes are preserved as-is (no re-joining into a single line,
  no markup stripping).
- **Empty notes:** a slide with empty or whitespace-only notes is flagged
  (its output record indicates "no notes"), but is otherwise treated like
  any other slide — the step still produces a result for it and the whole
  step still blocks for human approval same as always. No auto-skip, no
  special-cased approval flow. The human decides what to do (e.g. reject
  and add notes, or approve and let a later phase handle empty-audio
  behavior — that "no narration" behavior itself belongs to a later phase
  per `specs/roadmap.md` Phase 5's "graceful fallback for a slide with no
  audio").
- **Validation bar:** run against a real `.pptx` with several slides
  including at least one empty-notes slide; verify each slide's extracted
  notes text matches what's actually in the deck (byte-for-byte after the
  whitespace strip), in the correct slide order, and the empty-notes slide
  is correctly flagged without crashing the step or the pipeline.

## In scope

- Replace `src/videogen/pipeline/notes_extraction.py`'s stub body with
  real logic:
  - Take a real `.pptx` path as input, matching the shape the real
    `download` step already produces (`DownloadOutput.local_pptx_path`).
    The existing `NotesExtractionInput.deck_name` field is repurposed (or
    renamed for clarity) to carry the actual local `.pptx` path used to
    open the deck with `python-pptx`, not a display name.
  - For each slide in deck order, extract the raw speaker-notes text via
    `python-pptx`'s notes-slide API, strip leading/trailing whitespace.
  - Represent an empty/whitespace-only note as an empty string in the
    output notes list, and add a matching per-slide flag (e.g. a parallel
    `has_notes: list[bool]`, or an equivalent structure) so callers (the
    UI, tests) can tell "no notes" apart from "notes happen to be empty
    after some future normalization" without guessing from an empty
    string alone.
  - Output slide count must match `python-pptx`'s reported slide count
    for the deck (not the `slide_count` carried over from the `download`
    step's input, to avoid silently trusting a stale/mismatched number).
  - Keep the same `StepState`/`StepStatus`/`asyncio.Event` approval-gate
    shape as every other step — this phase only changes what happens
    *inside* `run_notes_extraction`.
- Update `src/videogen/pipeline/runner.py`'s call site to pass the real
  `.pptx` path through to `notes_extraction`'s new input shape.
- Update `src/videogen/pipeline/ui.py`'s demo/manual-run wiring if it
  hardcodes any notes-extraction input shape that no longer matches.
- Extend the checked-in sample deck fixture
  (`tests/fixtures/sample_deck.pptx`, 3 slides) with at least one
  empty-notes slide, or add a second small fixture deck that includes one
  — whichever keeps existing `download`-step tests (which assert exact
  slide count/content on the current fixture) unaffected.
- Tests: real extraction produces the correct notes text per slide in
  correct order against the fixture deck; the empty-notes slide is
  correctly flagged and does not crash the step; the step's approval gate
  (block/resume via `asyncio.Event`) still works exactly as before.

## Explicitly out of scope

- Any TTS/audio behavior for empty-notes slides (e.g. "no narration for
  this slide") — that belongs to a later phase (Phase 5 revalidation /
  Phase 7), not this one. This phase only extracts and flags; it does not
  decide downstream audio behavior.
- Any change to steps other than `notes_extraction` (and the minimal
  wiring changes in `runner.py`/`ui.py` needed to pass the real path
  through) — `download`, `tts`, `audio_upload`, `embed`, `render`,
  `video_upload` are untouched beyond that wiring.
- Text normalization beyond whitespace-stripping (no case folding, no
  removal of special characters, no re-flowing of paragraphs).
- Real Google Drive integration — still deferred per Phase 4's recorded
  scope decision, unaffected by this phase.

## Constraints (from specs/tech-stack.md)

- `python-pptx` for reading speaker notes, per tech-stack.md's stated
  approach.
- The step still follows the same `StepState`/`StepStatus`/
  `asyncio.Event` approval-gate shape as every other step.
- pytest + pytest-asyncio, testable with a real sample `.pptx` and no
  network access required (per mission.md's "every step stands alone,
  testable in isolation").

## Open questions

None outstanding — scope was confirmed with the human before writing this
implementation plan (see "User-provided requirements" above).
