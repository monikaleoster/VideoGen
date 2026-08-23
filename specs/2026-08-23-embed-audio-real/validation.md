# Validation — Embed Audio into PPTX (Real) (Phase 8)

This file is filled in during/after implementation (Plan.md task group 5).
Template below defines what "done" means.

## Automated validation

- [ ] `uv run pytest` passes in full, no regressions in any existing
      suite.
- [ ] Unit tests (`tests/test_embed.py`):
  - [ ] A slide with a real audio path gets a real audio media
        relationship in the output `.pptx`.
  - [ ] That slide's timing tree has an autoplay trigger (`onBegin`/"with
        previous"), not an on-click-only trigger — verified by XML
        inspection, not just that a shape was inserted.
  - [ ] A slide with `None` audio is left unchanged — no media
        relationship added for it.
  - [ ] A missing/corrupt audio file causes the step to fail (exception
        propagates) without writing a partial/corrupt output file.
  - [ ] The output is a new file; the original source `.pptx` is
        untouched.
  - [ ] The step's approval gate still blocks until
        `state.approval_event` is set, then resumes and returns the same
        output.
- [ ] `tests/test_runner.py` / `tests/test_pipeline_ui.py`: full pipeline
      chain still completes correctly with the corrected `EmbedInput`
      shape (`audio_paths` from `tts`, not `drive_file_ids` from
      `audio_upload`), no ordering regressions.

## Regression validation

- [ ] `download`, `notes_extraction`, and `tts` steps' existing tests
      still pass unmodified.
- [ ] `audio_upload` still runs and gates in the pipeline sequence
      exactly as before, even though `embed` no longer consumes its
      output.

## Build / lint / static analysis

- [ ] `uv run pytest` (this repo's build/test gate).

## Manual verification

Performed by: <fill in> — <date>

1. Run the full pipeline through `tts` against the fixture deck, then run
   `embed`; confirm it produces a new `_with_audio.pptx` file distinct
   from the source.
2. Inspect the output file's XML directly (or via the same
   python-pptx/lxml calls the automated tests use) to confirm the
   audio-bearing slides have both a real audio relationship and an
   autoplay trigger.
3. Confirm the fixture's no-notes slide ("Thank You") has no audio
   relationship added in the output.
4. Trigger a deliberate failure (e.g. point a slide's audio path at a
   nonexistent file) and confirm the step fails visibly rather than
   producing a partial/corrupt output.
5. Optional but recommended if a PowerPoint/LibreOffice Impress viewer is
   available: open the resulting `.pptx` and confirm audio actually
   autoplays per slide, as a real-world sanity check beyond the XML-level
   assertions (per the roadmap's original "open the resulting .pptx"
   validation wording) — not required for this phase's automated
   sign-off per the confirmed validation-method decision, but valuable
   corroboration if convenient.

## Expected result

- Every slide with audio has that audio embedded and set to autoplay on
  slide entry; every slide without audio is untouched.
- Failures are visible, not swallowed; no partial/corrupt output on
  failure.
- No regressions elsewhere in the pipeline.

## Failure conditions

- A slide's audio plays only on click, not automatically.
- A slide with no audio ends up with a spurious media shape.
- A failure produces a partial or corrupt `.pptx` rather than failing
  cleanly.
- Any existing test regresses.

## Evidence the human should provide

- Confirmation of the manual verification steps above (or a note on
  where they diverged), including the optional real-viewer check if
  performed.
- `APPROVED` or `CHANGES REQUIRED` per the human-validation gate before
  this phase's implementation PR is merged.

## Result

Not yet run — implementation has not started. This section is filled in
after Plan.md's task group 5.

## Roadmap update

Not yet applied — `specs/roadmap.md` Phase 8 status stays ⬜ until this
validation is complete and the human has signed off.
