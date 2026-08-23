# Requirements — Real Video Render + Pipeline Logging

## Context

The human reported "I don't see video is generated." Investigation found
`render.py` was still the Phase 2 mock: it returned a hardcoded fake path
(`/tmp/videogen/render/final_video.mp4`) and never invoked `ffmpeg` —
`specs/roadmap.md` Phase 5 had been marked ✅ prematurely ("done against
placeholders... re-validation against real images pending as this phase
is reached" — that re-validation was never actually done). This work
completes that re-validation with real inputs (real slide images from
Phase 4, real audio from Phase 7), and separately adds observability
logging across the whole pipeline per the same request.

## User-provided requirements (confirmed 2026-08-23)

- **No-audio slide fallback:** a slide with no narration
  (`audio_paths[i] is None`) gets a fixed-duration (3s) silent segment in
  the final video — it still appears, just without narration — rather
  than being dropped or crashing the render. (Recommended default,
  unopposed.)
- **Logging:** every pipeline step logs its own start/finish, key
  inputs/outputs, and real subprocess calls (ffmpeg, LibreOffice,
  ElevenLabs) at INFO, with more granular detail (exact commands, byte
  counts, timings) at DEBUG. Standard Python `logging` module, visible in
  whatever console runs the server/CLI — no new log file or external
  service, no structured/JSON format.

## In scope

- Replace `src/videogen/pipeline/render.py`'s stub body with real logic:
  - For each slide, render one video segment: its image held static, its
    real audio track if `audio_paths[i]` is set (`ffmpeg -loop 1 -i
    <image> -i <audio> ... -shortest`), or a fixed 3-second silent
    fallback if not (`ffmpeg -loop 1 -i <image> -f lavfi -i anullsrc ...
    -t 3`).
  - Concatenate segments in slide order via ffmpeg's concat demuxer into
    the final MP4, in a fresh per-run temp directory (matching
    `download`/`tts`/`embed`'s existing `tempfile.mkdtemp()` precedent).
  - Measure the final video's real duration via `ffprobe` — never a
    computed/guessed value.
  - Let any failure (missing image/audio file, ffmpeg error) propagate —
    no retry, no partial output, consistent with every other real step's
    pattern in this codebase.
- Add a shared `configure_logging()` (`src/videogen/logging_config.py`),
  called once from both entry points (`app.py` for the web UI/uvicorn,
  `__main__.py` for the CLI demo), so logging works identically
  regardless of how the app is started. Level controlled by the
  `VIDEOGEN_LOG_LEVEL` env var (default `INFO`); `DEBUG` only elevates
  the `videogen` logger tree, not third-party libraries, so turning on
  DEBUG doesn't flood output with e.g. PIL's or the ElevenLabs client's
  own internal debug logs.
- Add `logging.getLogger(__name__)` + meaningful log lines to every
  pipeline module (`download`, `notes_extraction`, `tts`, `audio_upload`,
  `embed`, `render`, `video_upload`, `runner`, `ui`, `routes`): step
  start/finish at INFO with key parameters/output summaries, granular
  subprocess/API-call detail at DEBUG. The ElevenLabs API key is never
  logged, at any level.
- Tests: real rendering, with real (generated) slide images and audio
  fixtures, producing a real playable MP4 with the correct total
  duration (sum of real per-slide durations + fixed fallback durations);
  a slide with no audio gets the fixed-duration silent segment; a missing
  image file fails the step without producing a partial output; the
  approval gate still works.

## Explicitly out of scope

- Any change to `audio_upload`/`video_upload`'s mock Drive behavior
  (Phase 9, still deferred; only their logging was touched here).
- A structured/JSON log format, log file, or external logging service.
- Configurable segment transitions, fades, or any other visual polish
  beyond a static image + audio per segment.

## Constraints (from specs/tech-stack.md)

- `ffmpeg` (subprocess) for pairing each slide image with its audio clip
  into a video segment and concatenating segments into the final MP4
  without dropped frames or audio desync, per tech-stack.md's stated
  approach.
- The step still follows the same `StepState`/`StepStatus`/
  `asyncio.Event` approval-gate shape as every other step.
- pytest + pytest-asyncio, testable with real (generated) fixtures and no
  network access required.

## Open questions

None outstanding.
