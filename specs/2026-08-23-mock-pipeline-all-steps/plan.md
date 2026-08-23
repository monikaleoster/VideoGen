# Plan — Mock Pipeline, All 7 Steps (Phase 2)

Numbered task groups. Each group should leave the repo in a working,
test-passing state.

## 1. Six new stub step modules

1.1. Create `src/videogen/pipeline/download.py`:
   - `DownloadInput` (e.g. `drive_link: str`).
   - `DownloadOutput` (e.g. `local_pptx_path: str`, `slide_image_paths:
     list[str]`, `slide_count: int`) — fake but plausible paths.
   - Async step function following Phase 1's `notes_extraction.py` shape:
     `RUNNING` → `asyncio.sleep` → fake output → `WAITING_APPROVAL` →
     await Event → `DONE`.
   - Module-level `state: StepState[DownloadOutput]`.

1.2. Update `src/videogen/pipeline/notes_extraction.py`'s
   `NotesExtractionInput` if needed so it can be constructed from
   `DownloadOutput`'s fields (e.g. accept `slide_count` /
   `slide_image_paths` instead of only `deck_name`) — keep this a minimal
   change, not a rewrite of Phase 1's proven step.

1.3. Create `src/videogen/pipeline/tts.py`:
   - `TtsInput` (per-slide notes list, from notes extraction's output).
   - `TtsOutput` (e.g. `audio_paths: list[str]`, `durations_sec:
     list[float]`) — one fake path/duration per slide.

1.4. Create `src/videogen/pipeline/audio_upload.py`:
   - `AudioUploadInput` (the TTS step's audio paths).
   - `AudioUploadOutput` (e.g. `drive_file_ids: list[str]`,
     `drive_urls: list[str]`) — fake per-slide Drive references.

1.5. Create `src/videogen/pipeline/embed.py`:
   - `EmbedInput` (download's pptx path + audio_upload's per-slide audio
     references).
   - `EmbedOutput` (e.g. `updated_pptx_path: str`, `slides_embedded:
     list[bool]`).

1.6. Create `src/videogen/pipeline/render.py`:
   - `RenderInput` (download's slide image paths + tts's audio paths).
   - `RenderOutput` (e.g. `video_path: str`, `duration_sec: float`).

1.7. Create `src/videogen/pipeline/video_upload.py`:
   - `VideoUploadInput` (render's video path).
   - `VideoUploadOutput` (e.g. `drive_file_id: str`, `drive_url: str`).

1.8. Unit tests for each of the six new steps
   (`tests/test_download.py`, `tests/test_tts.py`,
   `tests/test_audio_upload.py`, `tests/test_embed.py`,
   `tests/test_render.py`, `tests/test_video_upload.py`), mirroring
   Phase 1's `tests/test_notes_extraction.py`:
   - Step reaches `WAITING_APPROVAL` and does not proceed while its Event
     is unset (assert via timeout/task-state, not sleep-and-hope).
   - Setting the Event lets the step resume to `DONE` with well-shaped
     fake output.

## 2. Pipeline runner

2.1. Create `src/videogen/pipeline/runner.py`:
   - A `PipelineRun` holder (or similar) referencing all seven steps'
     `StepState` instances for one run.
   - An async `run_pipeline(...)` function that runs the seven steps in
     roadmap order, awaiting each step's completion (`DONE`) before
     starting the next, and threading each step's fake output into the
     next step's input per requirements.md's chaining decision.
   - Keep runner logic to orchestration only — no step-specific fake-data
     generation belongs here (that stays inside each step module).

2.2. Runner tests (`tests/test_runner.py`):
   - All seven steps execute in the fixed order; use a shared list/log
     appended to by each step (or inspect `StepState.status` transitions)
     to assert ordering.
   - A step never reaches `RUNNING` before the previous step reaches
     `DONE` (assert timing/ordering, not just end-state).
   - At least one chained field is asserted at each hop (e.g.
     `download`'s `slide_count` matches the length of `notes_extraction`'s
     fake notes list, which matches the length of `tts`'s
     `audio_paths`, through to `render`'s output referencing the same
     slide count).
   - Full run completes end-to-end when every step's Event is set in
     sequence, ending with `video_upload` reaching `DONE`.

## 3. CLI runner with logging

3.1. Update `src/videogen/pipeline/__main__.py`:
   - Configure `logging` (module-level logger, INFO level, a formatter
     that includes timestamp + step name) instead of Phase 1's `print`
     calls.
   - Drive the full `run_pipeline(...)` runner instead of just
     `notes_extraction`.
   - For each step: log `RUNNING` start, log `WAITING_APPROVAL` with a
     summary of the fake output produced, simulate approval after a short
     delay (log that this is simulated/CLI-only, same caveat Phase 1
     documented), log `DONE`.
   - Log overall run start and run completion (e.g. final video's fake
     Drive URL) so the full run's progress is traceable end-to-end from
     terminal output alone.

3.2. Smoke-test the CLI manually (see validation.md) — not a pytest test.

## 4. Wire-up check and docs

4.1. Run the full test suite (`uv run pytest`) — confirm Phase 0 and
     Phase 1's tests still pass alongside the new ones.

4.2. Update `specs/roadmap.md`: flip Phase 2's status from ⬜ to ✅ once
     validation.md's checklist is complete.

4.3. Fill in `validation.md` with results, including the manual
     verification section.
