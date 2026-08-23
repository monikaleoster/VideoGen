# Plan — Embed Audio Into PPTX (Real) (Phase 8)

Numbered task groups. Complete and validate each group before moving on.

## 1. Silent placeholder clip generation
- Objective: produce a reusable 1-second silent audio clip for slides with
  `has_notes=False`, without any network access.
- Tasks:
  1.1. Add a small helper (e.g. in `embed.py` or a shared audio-util
       module) that shells out to `ffmpeg` to generate a 1-second silent
       MP3/WAV clip into the run's working directory, matching the
       codec/format conventions `tts.py` already uses for real clips so
       `render`/Phase 10 don't need to special-case placeholder audio.
  1.2. Generate the clip once per pipeline run and reuse it for every
       no-notes slide in that run (not regenerated per slide).
- Dependencies: none.
- Files affected: `src/videogen/pipeline/embed.py` (or a new shared
  helper module if reused elsewhere later).
- Validation: generated clip is a valid audio file, ~1 second duration,
  playable/probeable via `ffprobe`.
- Independent: yes — can be built and unit-tested standalone.

## 2. Real `embed` step
- Objective: replace the stub with real `python-pptx`-backed audio
  embedding, autoplay-on-entry, icon hidden, safe to re-run.
- Tasks:
  2.1. Change `EmbedInput` to carry `local_pptx_path: str` and
       `audio_paths: list[str | None]` (from `tts_output.audio_paths`),
       dropping `drive_file_ids`.
  2.2. In `run_embed`: open the deck with `python-pptx`. For each slide in
       order:
       - If that slide already has an embedded audio/movie media element
         from a prior run of this step, remove it first (idempotent
         re-run, no duplicates).
       - Pick the clip: `audio_paths[i]` if set, otherwise the shared
         silent placeholder from task group 1.
       - Insert the clip via `python-pptx`'s movie/media-embedding API,
         configure the slide's `<p:timing>` autoplay-on-entry trigger, and
         hide the media placeholder shape (no visible icon).
  2.3. Save to a new `<base>_with_audio.pptx` path (mirroring the current
       stub's naming), leaving the source `.pptx` untouched.
  2.4. Build `EmbedOutput` with `updated_pptx_path: str` and
       `slides_embedded: list[bool]` (real narration embedded) plus
       whatever additional field distinguishes "real clip" from "silent
       placeholder" per slide for tests/UI (exact shape decided during
       implementation, e.g. `used_placeholder: list[bool]`).
  2.5. Keep the same `StepState`/`StepStatus`/`asyncio.Event`
       approval-gate shape as every other step.
- Dependencies: task group 1 (needs the silent-clip helper).
- Files affected: `src/videogen/pipeline/embed.py`.
- Validation: unit tests in group 4.
- Independent: no — depends on group 1.

## 3. Wire the new input/output shape through
- Tasks:
  3.1. Update `runner.py`'s call to `embed.run_embed` to pass
       `download_output.local_pptx_path` and `tts_output.audio_paths`
       instead of `audio_upload_output.drive_file_ids`. `audio_upload`
       still runs before `embed` in the pipeline order; its output is
       simply no longer threaded into `embed`.
  3.2. Update `ui.py`'s demo/manual-run wiring if it hardcodes any
       embed-step input shape that no longer matches.
- Dependencies: task group 2.
- Files affected: `src/videogen/pipeline/runner.py`,
  `src/videogen/pipeline/ui.py`.
- Validation: `uv run pytest` full suite still passes end-to-end.
- Independent: no — depends on group 2.

## 4. Tests
- Tasks:
  4.1. `tests/test_embed.py` (new): real embedding against the fixture
       deck + real/fake audio paths produces a `.pptx` where every slide
       has exactly one audio media element; a slide with a real
       `audio_paths[i]` gets that clip, a slide with `audio_paths[i] is
       None` gets the silent placeholder; autoplay-on-entry is set for
       every embedded clip; the media placeholder is hidden.
  4.2. Re-run test: running `run_embed` twice on the same input (or once
       on an already-embedded output path) does not produce duplicate
       audio elements on any slide — the second run's slide still has
       exactly one audio element (the latest one).
  4.3. Approval-gate test: the step still blocks on
       `state.approval_event` and resumes correctly, matching every other
       step's tested behavior.
  4.4. `tests/test_runner.py`: update the full-chain test for `embed`'s
       new input shape (`audio_paths` instead of `drive_file_ids`).
  4.5. `tests/test_pipeline_ui.py`: update any hardcoded embed-related
       assumptions left over from the stub.
  4.6. Run the full `uv run pytest` suite, confirm no regressions.
- Dependencies: task groups 1-3.
- Files affected: `tests/test_embed.py` (new), `tests/test_runner.py`,
  `tests/test_pipeline_ui.py`.
- Validation: all tests pass, including new re-run/idempotency and
  no-notes-placeholder assertions.
- Independent: no — depends on the implementation being in place.

## 5. Validation pass
- Tasks:
  5.1. Run real embedding manually against the fixture deck (with a mix
       of real and no-notes slides) outside pytest; open the resulting
       `.pptx` and confirm autoplay audio is present and correct per
       slide (real clip vs. 1-second silence), and the icon isn't shown.
  5.2. Fill in `specs/2026-08-23-embed-audio-pptx/validation.md`.
  5.3. Update Phase 8's status in `specs/roadmap.md` to ✅.
- Dependencies: task groups 1-4.
- Files affected: `specs/2026-08-23-embed-audio-pptx/validation.md`,
  `specs/roadmap.md`.
- Independent: no — final step.

## Delegable task groups

Group 1 (silent-clip helper) is independent and can be built/tested before
group 2's embed logic is finalized. Groups 2-5 are sequential given their
dependencies (2 needs 1; 3 needs 2; 4 needs 3; 5 needs 4).
