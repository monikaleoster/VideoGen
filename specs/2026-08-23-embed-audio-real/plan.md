# Plan — Embed Audio into PPTX (Real) (Phase 8)

Numbered task groups. Complete and validate each group before moving on.

## 1. Research/prototype the autoplay-on-entry XML shape
- Objective: nail down, before writing the real step, exactly what XML
  `add_movie` produces and what minimal edit makes it autoplay instead of
  requiring a click.
- Tasks:
  1.1. Insert an audio file via `add_movie` into a scratch `.pptx`,
       inspect the resulting `<p:timing>` tree.
  1.2. Identify the minimal `lxml` edit to change the media's trigger
       condition to `onBegin`/"with previous" (autoplay) instead of the
       default click-triggered control.
  1.3. Confirm the edited file still opens without corruption/repair
       prompts in at least one real viewer if available (LibreOffice
       Impress via headless conversion is a reasonable proxy check even
       without a full manual PowerPoint pass, since this phase's
       validation is automated-XML-first per the confirmed decision).
- Dependencies: none.
- Files affected: none (throwaway scratch script/exploration).
- Validation: a working, understood XML edit recipe to carry into group 2.
- Independent: yes.

## 2. Real `embed` step
- Objective: replace the stub with real per-slide audio embedding.
- Tasks:
  2.1. Change `EmbedInput` to `local_pptx_path: str`,
       `audio_paths: list[str | None]` (drop `drive_file_ids`).
  2.2. In `run_embed`: open the source `.pptx` with `python-pptx`.
  2.3. For each slide with a non-`None` audio path: insert the MP3 via
       `add_movie` (`mime_type="audio/mpeg"`) plus the autoplay XML edit
       from group 1; leave slides with `None` untouched.
  2.4. Save to a new file (`<name>_with_audio.pptx`) in a fresh per-run
       temp dir (matching `download`/`tts`'s `tempfile.mkdtemp()`
       precedent) — never overwrite the source.
  2.5. Build `EmbedOutput` with the new file's path and a
       `slides_embedded: list[bool]` flag per slide (True only where
       audio was actually inserted).
  2.6. Let any error (missing/corrupt audio file, python-pptx/XML error)
       propagate — no retry, no partial output written on failure.
  2.7. Keep the same `StepState`/`StepStatus`/`asyncio.Event`
       approval-gate shape as every other step.
- Dependencies: task group 1.
- Files affected: `src/videogen/pipeline/embed.py`.
- Validation: unit tests in group 4.
- Independent: no — depends on group 1's XML recipe.

## 3. Wire the corrected input source through
- Tasks:
  3.1. Update `runner.py`'s call to `embed.run_embed` to source
       `audio_paths` from `tts_output.audio_paths` instead of
       `audio_upload_output.drive_file_ids`.
  3.2. Update `ui.py`'s `_embed_input()` similarly.
  3.3. `audio_upload` itself is untouched — it still runs and gates in
       the pipeline sequence exactly as before, just no longer feeds
       `embed`'s input.
- Dependencies: task group 2.
- Files affected: `src/videogen/pipeline/runner.py`,
  `src/videogen/pipeline/ui.py`.
- Validation: `uv run pytest` full suite still passes end-to-end.
- Independent: no — depends on group 2's new `EmbedInput` shape.

## 4. Tests
- Tasks:
  4.1. `tests/test_embed.py`: real embedding against a real (silent) MP3
       fixture —
       - a slide with audio gets a real audio media relationship in the
         output `.pptx`, and its timing tree has an autoplay (not
         on-click-only) trigger — verified by XML inspection.
       - a slide with `None` audio is unchanged (no media relationship
         added for it).
       - a missing audio file path causes the step to raise/fail without
         writing a (possibly-corrupt) output file.
       - the output is a genuinely new file — the original `.pptx` is
         untouched (unmodified mtime/content or just: original still has
         no audio relationships).
       - the approval gate still blocks/resumes correctly.
  4.2. `tests/test_runner.py` / `tests/test_pipeline_ui.py`: update any
       calls/assumptions tied to the old `EmbedInput` shape
       (`drive_file_ids` -> `audio_paths`).
  4.3. Run the full `uv run pytest` suite, confirm no regressions.
- Dependencies: task groups 1-3.
- Files affected: `tests/test_embed.py` (new/updated),
  `tests/test_runner.py`, `tests/test_pipeline_ui.py`.
- Independent: no — depends on the implementation being in place.

## 5. Validation pass
- Tasks:
  5.1. Confirm the automated XML checks in group 4 pass — this is the
       confirmed validation method for this phase, no separate manual
       PowerPoint pass required.
  5.2. Fill in `specs/2026-08-23-embed-audio-real/validation.md`.
  5.3. Update Phase 8's status in `specs/roadmap.md`.
- Dependencies: task groups 1-4.
- Files affected: `specs/2026-08-23-embed-audio-real/validation.md`,
  `specs/roadmap.md`.
- Independent: no — final step.

## Delegable task groups

Group 1 (XML research) is independent and could be done standalone before
group 2 needs its output. Groups 2-5 are sequential given their
dependencies.
