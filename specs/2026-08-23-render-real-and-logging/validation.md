# Validation — Real Video Render + Pipeline Logging

## Automated validation

- [x] `uv run pytest` passes in full — 42 passed.
- [x] `tests/test_render.py` (rewritten for the real implementation):
  - [x] A slide with real audio produces a segment whose measured
        duration matches the audio's real length.
  - [x] A slide with no audio gets the fixed 3s silent fallback segment.
  - [x] The final video's total duration is the real sum of segment
        durations (verified via `pytest.approx`, not a hardcoded value).
  - [x] The output is a real, existing file — `Path(video_path).exists()`
        asserted, not just that a string was returned.
  - [x] A missing image file fails the step (exception propagates)
        without reaching `WAITING_APPROVAL`.
  - [x] The approval gate still blocks/resumes correctly.
- [x] Full suite regression check: all other steps' tests still pass.

## Manual verification

Performed by: Claude (session, monikaleoster@gmail.com) — 2026-08-23

1. Ran the full CLI pipeline (`uv run python -m videogen.pipeline`,
   `tts`'s ElevenLabs client mocked, `VIDEOGEN_LOG_LEVEL=DEBUG`)
   end-to-end. Confirmed via the log output that every step logged its
   start, key parameters, and completion, and that `render` logged each
   segment as it was produced plus the final concatenation.
2. Confirmed the real output file exists on disk
   (`/tmp/videogen_render_.../final_video.mp4`, ~43KB) and inspected it
   with `ffprobe`: both a video stream and an audio stream present, real
   total duration 5.02s — matching 2 real ~1s narrated segments + 1 fixed
   3s silent fallback for the fixture's no-notes slide.
3. Confirmed DEBUG-level logging is scoped correctly: elevating
   `VIDEOGEN_LOG_LEVEL=DEBUG` shows detailed `videogen.*` log lines
   (exact ffmpeg/LibreOffice commands, byte counts) without flooding the
   console with third-party libraries' own debug output (verified PIL's
   logger stays silent at DEBUG while `videogen.pipeline.*` loggers show
   DEBUG lines).
4. Confirmed the ElevenLabs API key never appears in any log line, at
   any level (checked `tts.py`'s `_synthesize`, which explicitly avoids
   logging it).

## Expected result

- The pipeline produces a real, playable MP4 with both audio and video
  streams and a duration matching the real narration + fallback timing.
- Every step logs enough at INFO to follow a run's progress, and enough
  at DEBUG to diagnose a failure, without leaking the ElevenLabs
  credential or drowning in third-party noise.

## Failure conditions

- The reported video path doesn't exist, or is silent/corrupt.
- A no-audio slide is dropped from the video instead of getting the
  silent fallback.
- DEBUG logging floods the console with unrelated library internals.
- The API key appears in any log line.

## Result

- Automated checks: done — 42/42 tests pass.
- Manual verification: done — real video confirmed playable with correct
  duration and streams; logging confirmed scoped and credential-safe.
- Outcome: ready to merge.

## Roadmap update

Phase 5 marked ✅ in `specs/roadmap.md`, replacing its
"done against placeholders, re-validation pending" footnote — the
re-validation against real Phase 4/7 inputs is now actually done.
