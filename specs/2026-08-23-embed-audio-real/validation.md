# Validation — Embed Audio into PPTX (Real) (Phase 8)

This file is filled in during/after implementation (Plan.md task group 5).
Template below defines what "done" means.

## Automated validation

- [x] `uv run pytest` passes in full, no regressions in any existing
      suite — 41 passed.
- [x] Unit tests (`tests/test_embed.py`):
  - [x] A slide with a real audio path gets a real audio media
        relationship in the output `.pptx`.
  - [x] That slide's timing tree has an autoplay trigger (`delay="0"`),
        not an on-click-only trigger (`delay="indefinite"`) — verified by
        XML inspection, not just that a shape was inserted.
  - [x] A slide with `None` audio is left unchanged — no `<p:timing>`
        tree added for it at all.
  - [x] A missing audio file causes the step to fail (exception
        propagates) without writing a partial/corrupt output file, and
        the step never reaches `WAITING_APPROVAL`.
  - [x] The output is a new file; the original source `.pptx` is
        untouched (confirmed no `<p:timing>` tree in the original).
  - [x] The step's approval gate still blocks until
        `state.approval_event` is set, then resumes and returns the same
        output.
- [x] `tests/test_runner.py` / `tests/test_pipeline_ui.py`: full pipeline
      chain still completes correctly with the corrected `EmbedInput`
      shape (`audio_paths` from `tts`, not `drive_file_ids` from
      `audio_upload`), no ordering regressions.

## Regression validation

- [x] `download`, `notes_extraction`, and `tts` steps' existing tests
      still pass unmodified.
- [x] `audio_upload` still runs and gates in the pipeline sequence
      exactly as before (confirmed via the CLI's full run log), even
      though `embed` no longer consumes its output.

## Build / lint / static analysis

- [x] `uv run pytest` (this repo's build/test gate).

## How the autoplay XML edit was determined (group 1 research)

`add_movie` produces a click-triggered media node whose start condition
is `<p:cond delay="indefinite"/>` (wait for the picture's
`ppaction://media` hyperlink click action). Changing that one attribute
to `<p:cond delay="0"/>` makes the media start immediately once the
slide's timing root begins (i.e., on slide entry) — confirmed by
inspecting the XML `add_movie` produces on a scratch deck, editing it,
and reconverting through LibreOffice headless (a structural-validity
proxy — see Manual verification item 5) with no corruption/repair
prompt.

## Manual verification

Performed by: Claude (session, monikaleoster@gmail.com) — 2026-08-23

1. Ran the full pipeline (via `uv run python -m videogen.pipeline`, real
   `download`/`notes_extraction`/`embed`, `tts`'s ElevenLabs client
   mocked) end-to-end: `embed`'s output was
   `EmbedOutput(updated_pptx_path='.../sample_deck_with_audio.pptx',
   slides_embedded=[True, True, False])` — matching the fixture's 2
   notes-bearing slides + 1 empty-notes slide. `audio_upload` ran and
   gated normally beforehand, confirming it's unaffected by no longer
   feeding `embed`.
2. Inspected the output file's XML directly: slides 1 and 2 have a real
   audio media relationship and `delay="0"` (autoplay) timing; slide 3
   has no `<p:timing>` tree at all.
3. Confirmed the fixture's no-notes slide ("Thank You", slide 3) has no
   audio relationship added, per the above.
4. Triggered a deliberate failure (a nonexistent audio file path) via
   `tests/test_embed.py::test_missing_audio_file_fails_without_partial_output`:
   confirmed the step raises and never reaches `WAITING_APPROVAL`.
5. Real-viewer proxy check (LibreOffice headless, since no PowerPoint is
   available in this sandbox): converted the real pipeline run's output
   `_with_audio.pptx` to PDF successfully, with no corruption or
   repair-needed signal — the file is structurally sound. **A human with
   PowerPoint/LibreOffice Impress installed locally should still do a
   real playback check (opening the deck and confirming audio actually
   autoplays per slide) as the strongest form of corroboration**, though
   per the confirmed validation-method decision this isn't required for
   this phase's automated sign-off.

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

- Automated checks: done — 41/41 tests pass, including real XML-level
  autoplay verification.
- Manual verification: done for everything the confirmed validation
  method requires (automated XML/structure inspection); a real
  PowerPoint/LibreOffice Impress playback check by a human is optional
  corroboration, not a blocker for this phase per that decision.
- Outcome: ready to merge.

## Roadmap update

Phase 8 marked ✅ in `specs/roadmap.md`.
