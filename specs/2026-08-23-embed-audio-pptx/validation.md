# Validation — Embed Audio Into PPTX (Real) (Phase 8)

This file is filled in during/after implementation (Plan.md task group 5).
Template below defines what "done" means.

## Automated validation

- [ ] `uv run pytest` passes in full, no regressions in any existing suite
      (download, notes_extraction, tts, runner, pipeline UI, etc.).
- [ ] Unit tests (`tests/test_embed.py`):
  - [ ] Every slide in the output `.pptx` has exactly one audio media
        element.
  - [ ] A slide with a real `audio_paths[i]` gets that clip embedded.
  - [ ] A slide with `audio_paths[i] is None` gets the 1-second silent
        placeholder clip embedded instead.
  - [ ] Every embedded clip is set to autoplay on slide entry.
  - [ ] The media placeholder/icon is hidden for every embedded clip.
  - [ ] Re-running the embed step (same or already-embedded input) does
        not produce duplicate audio elements on any slide.
  - [ ] The step's approval gate still blocks until
        `state.approval_event` is set, then resumes and returns the same
        output (matching every other step's behavior).
- [ ] Integration (`tests/test_runner.py`): full 7-step chain still
      completes correctly with `embed` consuming `tts_output.audio_paths`
      directly (not `audio_upload_output.drive_file_ids`), no ordering
      regressions.
- [ ] `tests/test_pipeline_ui.py`: UI's `embed` Run/Approve/Reject flow
      still works against the real fixture deck.

## Regression validation

- [ ] `notes_extraction`, `tts`, `download` steps' existing tests still
      pass unchanged.
- [ ] `audio_upload` still runs in pipeline order (still mocked) even
      though its output is no longer consumed by `embed`.

## Build / lint / static analysis

- [ ] `uv run pytest` (build/test gate — this repo has no separate
      lint/typecheck step beyond what pytest covers).

## Manual verification

Performed by: _(fill in)_ — _(date)_

1. Run `run_embed` directly (outside pytest) against the fixture deck with
   a mix of real TTS audio paths and at least one `None` (no-notes) entry.
2. Open the resulting `<...>_with_audio.pptx` in PowerPoint/LibreOffice
   Impress.
3. For each slide that had real narration: confirm the audio plays
   automatically when the slide is entered, and its duration/content
   matches the corresponding TTS clip.
4. For the no-notes slide: confirm a short (~1 second) silent audio
   element is present and set to autoplay — the slide isn't missing audio
   entirely.
5. Confirm no visible speaker/audio icon appears on any slide during
   playback.
6. Re-run the embed step on the same source deck (simulating a
   post-regeneration re-run) and re-open the new output: confirm each
   slide still has exactly one audio element, not two.

## Expected result

- Every slide in the output `.pptx` has exactly one autoplay audio
  element: the real narration clip where notes existed, a short silent
  clip otherwise.
- No visible media icon on any slide.
- Re-running the step is safe: never produces duplicate audio elements.
- No regressions elsewhere in the pipeline.

## Failure conditions

- Any slide missing an audio element, or with more than one.
- Audio that doesn't autoplay on slide entry (requires a manual click).
- A visible speaker/media icon on the slide.
- Re-running the step duplicates audio, crashes, or corrupts the deck.
- Any existing test regresses.

## Evidence the human should provide

- Confirmation of the manual verification steps above (or a note on where
  they diverged), including which viewer (PowerPoint/LibreOffice Impress)
  was used to confirm autoplay behavior.
- `APPROVED` or `CHANGES REQUIRED` per the human-validation gate before
  this phase's implementation PR is merged.

## Result

_(filled in after implementation)_

## Roadmap update

_(Phase 8 marked ✅ in `specs/roadmap.md` once validation passes)_
