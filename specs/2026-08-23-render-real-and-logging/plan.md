# Plan — Real Video Render + Pipeline Logging

## 1. Real render step
- Objective: replace the mock with real ffmpeg-based rendering.
- Tasks: per-slide segment rendering (real audio or silent fallback),
  concatenation, real duration measurement via ffprobe, failure
  propagation.
- Files: `src/videogen/pipeline/render.py`.
- Validation: unit tests with generated image/audio fixtures.
- Independent: yes.

## 2. Central logging config
- Objective: one `configure_logging()` shared by both entry points.
- Tasks: `src/videogen/logging_config.py`; wire into `app.py` and
  `__main__.py`, replacing `__main__.py`'s standalone `basicConfig` call.
- Files: `src/videogen/logging_config.py`, `src/videogen/app.py`,
  `src/videogen/pipeline/__main__.py`.
- Validation: manual — confirm DEBUG env var elevates only `videogen.*`
  loggers, not third-party libraries.
- Independent: yes.

## 3. Per-module logging
- Objective: meaningful INFO/DEBUG logs in every pipeline module.
- Tasks: add a logger + log calls to `download`, `notes_extraction`,
  `tts` (never logging the API key), `audio_upload`, `embed`, `render`,
  `video_upload`, `runner`, `ui`, `routes`.
- Files: all of the above.
- Validation: manual — run the CLI pipeline end-to-end with
  `VIDEOGEN_LOG_LEVEL=DEBUG` and confirm every step's transitions and key
  data are visible and legible.
- Independent: depends on group 2 for the shared config, otherwise
  parallel-safe per module.

## 4. Tests
- Rewrite `tests/test_render.py` for the real implementation (real
  generated image/audio fixtures, real duration assertions, missing-file
  failure case).
- Run the full suite, confirm no regressions.
- Files: `tests/test_render.py`.

## 5. Validation pass
- Manual: run the CLI pipeline end-to-end (ElevenLabs client mocked, no
  real network access needed for this check), confirm a real, playable
  MP4 file exists with the correct duration and both audio+video
  streams.
- Fill in `validation.md`, update `specs/roadmap.md` Phase 5.
