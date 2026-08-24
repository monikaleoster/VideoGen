# Plan — TTS Step: "Run" No Longer Calls ElevenLabs

Numbered task groups. Complete and validate each group before moving on.

## 1. `prepare_tts` in `tts.py`
- Objective: a Run/Reject path for the browser UI that never touches
  ElevenLabs, alongside the existing (unchanged) `run_tts` used by the
  CLI demo path.
- Tasks:
  1.1. Add `TtsPrepareInput` dataclass: `notes: list[str]`,
       `has_notes: list[bool]` (no credentials).
  1.2. Add `async def prepare_tts(step_input: TtsPrepareInput) ->
       TtsOutput`: same `state.status = RUNNING` / `state.output = None`
       / `state.approval_event.clear()` opening as every other step; no
       work-dir creation, no `_synthesize` calls; builds
       `TtsOutput(audio_paths=[None] * n, durations_sec=[None] * n)`
       where `n = len(step_input.notes)`; sets `state.output`, `status =
       WAITING_APPROVAL`; `await state.approval_event.wait()`; `status =
       DONE`; return.
  1.3. Leave `run_tts`, `TtsInput`, `regenerate_slide`,
       `_current_work_dir` untouched — `runner.py`'s CLI-path call to
       `tts.run_tts(...)` keeps working exactly as before.
- Dependencies: none.
- Files affected: `src/videogen/pipeline/tts.py`.
- Validation: unit tests in group 3.
- Independent: yes.

## 2. Route wiring
- Tasks:
  2.1. `routes.py`: add `_tts_prepare_input(request_data)` building
       `tts.TtsPrepareInput(notes=notes_extraction.state.output.notes,
       has_notes=notes_extraction.state.output.has_notes)` — no
       `api_key`/`voice_id` check.
  2.2. Change the `STEPS` table's `tts` entry to use
       `tts.prepare_tts` / `_tts_prepare_input` instead of
       `tts.run_tts` / `_tts_input`. Remove `_tts_input` if nothing else
       references it (confirm via search before deleting).
  2.3. Leave `/pipeline/tts/slide/{index}/generate` and its handler
       (`generate_tts_slide`) completely unchanged — still requires
       `api_key`/`voice_id`/non-empty `text`, still calls
       `tts.regenerate_slide`.
- Dependencies: group 1.
- Files affected: `src/videogen/pipeline/routes.py`.
- Validation: route tests in group 3.
- Independent: no.

## 3. Tests
- Tasks:
  3.1. `tests/test_tts.py`: new tests for `prepare_tts` — given N notes,
       produces `audio_paths`/`durations_sec` of length N, all `None`;
       ElevenLabs client (`_synthesize`) is asserted **not called**;
       approval gate still blocks/resumes via `state.approval_event`.
       Existing `run_tts` tests untouched (still assert real generation).
  3.2. `tests/test_pipeline_ui.py` (or wherever route-level `tts` tests
       live): `POST /pipeline/tts/run` with no `api_key`/`voice_id` in
       the body now succeeds (previously would 422) and produces an
       all-`None` output; the mocked ElevenLabs client is not called;
       `POST /pipeline/tts/reject` behaves the same way.
  3.3. `tests/test_runner.py`: confirm `run_pipeline` (the CLI path)
       still calls the real `tts.run_tts` and produces real (mocked)
       audio — this is the regression check that the split didn't
       silently make the CLI path prepare-only too.
  3.4. Full `uv run pytest`, confirm no regressions.
- Dependencies: groups 1-2.
- Files affected: `tests/test_tts.py`, `tests/test_pipeline_ui.py`,
  `tests/test_runner.py`.
- Independent: no.

## 4. UI: "Generate All" wiring
- Tasks:
  4.1. `templates/index.html`: replace the `generateAllBtn`'s handler
       (`postAction("tts", ttsStep.status === "pending" ? "run" :
       "reject")`) with a new `generateAllSlides(row)` function that:
       iterates the current slide rows in index order, reads each row's
       `data-role="slide-text"` value, skips it if blank/whitespace-only,
       otherwise `await`s the same per-slide fetch `generateSlide` already
       performs (`POST /pipeline/tts/slide/{index}/generate`) before
       moving to the next row (sequential, matching the existing
       no-concurrent-burst behavior).
  4.2. No changes needed to `renderTtsSlides`'s row-building logic — the
       rows themselves (text input, Generate button, audio player) are
       unchanged; only what the "Generate All" button triggers changes.
- Dependencies: groups 1-3 (needs the backend split done and tested
  first, though this task only touches the template file).
- Files affected: `templates/index.html`.
- Validation: manual browser check in group 5.
- Independent: no — should land after the backend to avoid a UI that
  calls a Run/Reject path expecting the old behavior.

## 5. Validation pass
- Tasks:
  5.1. Manual browser check: `notes_extraction` done -> `tts` Run
       (confirm slide rows appear, no audio, no ElevenLabs call) ->
       "Generate All" (confirm real audio appears for every slide with
       notes) -> single "Generate" on one slide (confirm it still works
       standalone).
  5.2. Manual CLI check: `uv run python -m videogen.pipeline` with real
       (or mocked, if no credentials available in this environment)
       ElevenLabs credentials, confirm it still produces a complete video
       with real per-slide audio, no behavior change from before this
       phase.
  5.3. Fill in `specs/2026-08-23-tts-run-no-autogenerate/validation.md`.
- Dependencies: groups 1-4.
- Files affected:
  `specs/2026-08-23-tts-run-no-autogenerate/validation.md`.
- Independent: no — final step.

## Delegable task groups

Group 1 (`prepare_tts`) is fully independent and can start immediately.
Group 2 depends on it. Group 3 (tests) needs groups 1-2 done. Group 4
(UI) is a template-only change that can be drafted in parallel with group
3 once group 2's route shape is settled, but should not be merged ahead
of group 3's regression coverage. Group 5 is final.
