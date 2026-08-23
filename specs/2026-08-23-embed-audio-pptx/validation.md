# Validation — Embed Audio Into PPTX (Real) (Phase 8)

This file is filled in during/after implementation (Plan.md task group 5).
Template below defines what "done" means.

## Automated validation

- [x] `uv run pytest` passes in full, no regressions in any existing suite
      (download, notes_extraction, tts, runner, pipeline UI, etc.) — 42
      passed.
- [x] Unit tests (`tests/test_embed.py`):
  - [x] Every slide in the output `.pptx` has exactly one audio media
        element.
  - [x] A slide with a real `audio_paths[i]` gets that clip embedded.
  - [x] A slide with `audio_paths[i] is None` gets the 1-second silent
        placeholder clip embedded instead.
  - [x] Every embedded clip is set to autoplay on slide entry (asserted
        via the `<p:timing>`/`<p:cmd>` structure — see note below on what
        this does and doesn't prove).
  - [x] The media placeholder/icon is hidden for every embedded clip
        (asserted via 1x1 EMU shape size).
  - [x] Re-running the embed step against the same pristine source deck
        (the real pipeline's actual re-run pattern — see note below) does
        not produce duplicate audio elements on any slide.
  - [x] The step's approval gate still blocks until
        `state.approval_event` is set, then resumes and returns the same
        output (matching every other step's behavior).
- [x] Integration (`tests/test_runner.py`): full 7-step chain still
      completes correctly with `embed` consuming `tts_output.audio_paths`
      directly (not `audio_upload_output.drive_file_ids`), no ordering
      regressions.
- [x] `tests/test_pipeline_ui.py`: UI's `embed` Run/Approve/Reject flow
      still works against the real fixture deck (no embed-specific
      assumptions needed updating).

## Regression validation

- [x] `notes_extraction`, `tts`, `download` steps' existing tests still
      pass unchanged.
- [x] `audio_upload` still runs in pipeline order (still mocked) even
      though its output is no longer consumed by `embed`.

## Build / lint / static analysis

- [x] `uv run pytest` (build/test gate — this repo has no separate
      lint/typecheck step beyond what pytest covers).

## Notes on scope decided during implementation

- **Idempotent re-run scope narrowed to the real pipeline's actual
  pattern.** `runner.py` always passes `download_output.local_pptx_path`
  (the pristine, untouched source deck) into `embed`, never `embed`'s own
  prior output — so a re-run (e.g. after a per-slide TTS regeneration)
  always starts fresh from that same pristine source. This is what
  `_remove_existing_audio`'s idempotency is validated against, and what
  `tests/test_embed.py::test_rerunning_the_step_does_not_duplicate_audio`
  covers. Passing `embed`'s own previously-embedded output back in as
  `local_pptx_path` (re-embedding a file this step itself already
  produced) hits an upstream `python-pptx` bug on reopen
  (`AttributeError: 'Part' object has no attribute 'sha1'` in
  `pptx.package._find_by_sha1`, triggered when re-adding the same media
  content into a package that already contains a video/audio part) — this
  is orthogonal to this step's own logic and not exercised by the real
  pipeline, so it's out of this phase's validated scope rather than a bug
  in `run_embed` itself.
- **`add_movie` + retag workaround.** `python-pptx` (1.0.2) has no
  dedicated audio-embedding API; `add_movie` always writes an
  `<a:videoFile>` reference regardless of `mime_type`. The implementation
  retags that element to the OOXML-correct `<a:audioFile>` after
  `add_movie` runs — the underlying relationship/media-part plumbing is
  identical for audio and video, so this is a safe rename, not a
  structural change.
- **Autoplay timing is a from-scratch `<p:timing>` tree**, since
  `add_movie`'s own timing only sets up "wait for a click" playback
  (adds play controls, not autoplay). The custom timing was hand-built
  against the ECMA-376 timing schema (a `playFrom(0.0)` command triggered
  with `delay="0"` in the slide's main sequence) rather than copied from a
  known-good real PowerPoint file, since no such reference file was
  available in this environment. Automated tests can only confirm the XML
  *shape* (a `<p:cmd>` element targeting the right shape id exists) — they
  cannot confirm PowerPoint itself honors it as true click-free autoplay.
  **This is the one part of this phase that still needs a human to
  actually open the file in real PowerPoint (not just LibreOffice) and
  confirm the audio starts without any click**, per the manual
  verification steps below — flagging this the same way Phase 7 flagged
  its own real-credential check as still owed.

## Manual verification

Performed by: Claude (session, monikaleoster@gmail.com) — 2026-08-23,
**partial** — see "still needed from a human" below.

1. Ran the real chain (`download` → real `notes_extraction` → `tts` with
   ElevenLabs mocked but real local audio files, matching how
   `tests/test_runner.py` already mocks it — → `embed`) against
   `tests/fixtures/sample_deck.pptx` (3 slides, `has_notes=[True, True,
   False]`). Result: `EmbedOutput(slides_embedded=[True, True, True],
   used_placeholder=[False, False, True])` — slide 3 (no notes) correctly
   got the silent placeholder, slides 1-2 got real narration.
2. Opened the resulting `sample_deck_with_audio.pptx` with `python-pptx`:
   every slide has exactly one `<a:audioFile>` media shape, sized 1x1 EMU
   (invisible), and a `<p:timing>` tree with a `playFrom(0.0)` command
   targeting that slide's shape id.
3. Converted the same output file to PDF via `soffice --headless
   --convert-to pdf` (LibreOffice Impress) with no errors — confirms the
   file isn't corrupted and LibreOffice's own OOXML parser accepts the
   retagged `<a:audioFile>` element and the hand-built `<p:timing>` tree
   without complaint.
4. Ran `tests/test_embed.py`'s re-run test: running `run_embed` twice
   against the same pristine fixture deck produces exactly one audio
   element per slide both times (no duplication).

### Still needed from a human

- **Open the output `.pptx` in actual Microsoft PowerPoint** (not just
  LibreOffice Impress) and confirm each slide's audio truly starts
  playing the instant the slide is entered, with no click required, and
  that no speaker/media icon is visible during playback. This is the one
  claim this implementation makes that only real PowerPoint can confirm —
  LibreOffice accepting the file structurally is not proof PowerPoint's
  autoplay behavior triggers correctly.
- Listen to a couple of the real-narration slides' embedded audio (vs.
  the silent placeholder slide) to confirm the *right* clip landed on the
  right slide, by ear, not just by file path.

## Expected result

- Every slide in the output `.pptx` has exactly one autoplay audio
  element: the real narration clip where notes existed, a short silent
  clip otherwise.
- No visible media icon on any slide.
- Re-running the step (against the pristine source, as the real pipeline
  does) is safe: never produces duplicate audio elements.
- No regressions elsewhere in the pipeline.

## Failure conditions

- Any slide missing an audio element, or with more than one.
- Audio that doesn't autoplay on slide entry in real PowerPoint (requires
  a manual click).
- A visible speaker/media icon on the slide.
- Re-running the step against the pristine source deck duplicates audio,
  crashes, or corrupts the deck.
- Any existing test regresses.

## Evidence the human should provide

- Confirmation of the "Still needed from a human" checks above — in
  particular, real-PowerPoint autoplay confirmation, since that's the one
  behavior this implementation could not verify itself in this
  environment.
- `APPROVED` or `CHANGES REQUIRED` per the human-validation gate before
  this phase's implementation PR is merged.

## Result

- Automated checks: done — 42/42 tests pass, including new embed-specific
  coverage (real clip vs. placeholder, autoplay XML shape, hidden icon,
  re-run non-duplication, approval gate).
- Manual verification: partial — structural correctness confirmed
  (python-pptx inspection + LibreOffice round-trip); real-PowerPoint
  autoplay confirmation still owed by a human (see above), matching how
  Phase 7 flagged its own real-credential check as still owed.
- Outcome: implementation complete; **not yet marked ✅** — awaiting the
  human's real-PowerPoint confirmation per the human-validation gate.

## Roadmap update

Phase 8 left at 🚧 in `specs/roadmap.md` (implementation + automated
validation done; real-PowerPoint autoplay confirmation from a human still
owed before marking ✅), mirroring Phase 7's status pattern.
