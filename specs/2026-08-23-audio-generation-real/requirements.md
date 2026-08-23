# Requirements — Audio Generation (Real, ElevenLabs) (Phase 7)

## Context

Phases 0-6 are done and merged: scaffold, all 7 mocked pipeline steps, the
approval-gate UI, real `download` (local `.pptx` -> slide images), and
real `notes_extraction` (python-pptx, with a `has_notes` flag per slide).
This phase replaces the mock `tts` step with real ElevenLabs text-to-speech
calls, per `specs/roadmap.md` Phase 7 and `specs/tech-stack.md`'s stated
use of the ElevenLabs API: single voice per run, user-supplied voice ID
and API key, rate-limit-aware.

## User-provided requirements (confirmed 2026-08-23)

- **Voice settings:** fixed stability/similarity settings for every run —
  no per-run override of those two values. (Exact numeric defaults are a
  technical recommendation below, not a product requirement — the human
  only decided "fixed, not configurable.")
- **Chunking:** out of scope this phase. Each slide's notes text is sent
  to ElevenLabs in a single call; no splitting/stitching logic for
  long notes.
- **Empty-notes slides:** a slide Phase 6 flagged with `has_notes=False`
  is skipped entirely by TTS — no ElevenLabs call is made for it, and no
  audio file is produced for that slide.
- **Skipped-slide output representation:** for a skipped slide,
  `TtsOutput.audio_paths[i]` and `TtsOutput.durations_sec[i]` are both
  `None` (not an empty string or `0.0`), so downstream steps and tests can
  tell "no audio, deliberately skipped" apart from a real (possibly short)
  clip without guessing from a sentinel value.
- **Credentials:** the ElevenLabs API key and voice ID are supplied
  per run through the approval-gate UI (new input fields for the `tts`
  step), held in memory only for that run — not persisted to disk,
  browser storage, or `.env`. This is a deliberate deviation from
  tech-stack.md's more general "env vars / `.env`" wording for secrets;
  tech-stack.md's constraint still holds for any credential that *is*
  read from the environment (there is none here), just not for these two
  values, which the human explicitly wants to enter at run time instead.
- **Retry policy:** no automatic retry logic. On a transient failure
  (rate limit, 5xx, network error) the step fails/errors out; the human
  retries manually via the pipeline UI's existing per-step Reject/re-run
  action. No new backoff/retry mechanism is built in this phase.
- **Rate-limit awareness (from tech-stack.md, scoped down given the "no
  auto-retry" decision above):** calls to ElevenLabs are made
  sequentially, one slide at a time — no concurrent burst of requests —
  so the step doesn't proactively trigger rate limiting by parallelizing.
  It does not proactively throttle beyond that; a 429 is simply a
  transient failure per the retry policy above (surfaced as an error, not
  silently swallowed).

## In scope

- Replace `src/videogen/pipeline/tts.py`'s stub body with real logic:
  - `TtsInput` gains: `notes: list[str]`, `has_notes: list[bool]` (from
    `notes_extraction`'s output), `api_key: str`, `voice_id: str`.
  - For each slide where `has_notes[i]` is `True`, call the ElevenLabs
    text-to-speech API with that slide's notes text, the given
    `voice_id`/`api_key`, and the fixed stability/similarity settings.
    Save the returned audio as an MP3 file.
  - For each slide where `has_notes[i]` is `False`, skip the API call;
    `audio_paths[i] = None`, `durations_sec[i] = None`.
  - Store generated audio files in a fresh per-run temporary directory
    (matching the `download` step's precedent from Phase 4), not one
    fixed shared path — avoids collisions across concurrent/successive
    runs.
  - Determine each real clip's actual duration (not a guessed/fake
    value) — **technical recommendation:** via `ffprobe` (already a
    project dependency per tech-stack.md's `ffmpeg`/`ffmpeg-python`
    usage), reading the real MP3's duration rather than trusting an
    ElevenLabs response field that may not always be present.
  - On any ElevenLabs API error (auth failure, rate limit, network
    error, etc.), let the exception propagate so the step fails visibly
    (per the "no auto-retry" decision) rather than swallowing it or
    producing a fake/placeholder output.
  - Keep the same `StepState`/`StepStatus`/`asyncio.Event` approval-gate
    shape as every other step.
- Add API key + voice ID input fields to the approval-gate UI's `tts`
  step (`templates/index.html` + the relevant JS), submitted with that
  step's "Run" action and held only in the browser's in-memory page
  state for that run — not written to `localStorage`, cookies, or any
  server-side file.
- Update `src/videogen/pipeline/runner.py` and `ui.py`'s `_tts_input()`
  wiring to pass `has_notes` through from `notes_extraction`'s output,
  and to source `api_key`/`voice_id` from the new UI fields (`ui.py`) or
  an equivalent CLI-appropriate source for `__main__.py` (see Constraints
  below for the CLI's specific handling).
- Tests: real ElevenLabs calls are **not** exercised in the automated
  test suite (no network access, per tech-stack.md/mission.md's
  "testable in isolation" principle) — instead, the ElevenLabs client
  call is mocked/faked in tests, and tests verify: skipped slides get
  `None`/`None` output and no API call is attempted for them; slides with
  notes get a real (or realistically-shaped, in the mocked case) audio
  file path and duration; a simulated API failure propagates as an error
  rather than being swallowed; the step's approval gate still works.

## Explicitly out of scope

- Any UI/CLI mechanism to persist the API key or voice ID across runs
  (no "remember me," no config file, no env var *as the primary path*
  for the UI flow).
- Chunking/splitting long notes text across multiple ElevenLabs calls.
- Automatic retry or backoff on transient failures.
- Per-run configurable stability/similarity settings.
- Any change to steps other than `tts` (and the minimal wiring changes in
  `runner.py`/`ui.py`/`templates/index.html` needed to pass the new
  inputs through) — `download`, `notes_extraction`, `audio_upload`,
  `embed`, `render`, `video_upload` are untouched beyond that wiring.
- Real Google Drive integration — still deferred per Phase 4's recorded
  scope decision, unaffected by this phase.

## Constraints (from specs/tech-stack.md, and scope decisions above)

- **ElevenLabs API** (`elevenlabs` Python SDK or direct HTTP calls) for
  text-to-speech, single voice per run, per tech-stack.md.
- The step still follows the same `StepState`/`StepStatus`/
  `asyncio.Event` approval-gate shape as every other step.
- pytest + pytest-asyncio; the real network call is mocked in automated
  tests (no ElevenLabs network access required to run the suite).
- **CLI note (confirmed 2026-08-23):** `__main__.py`'s demo entry point
  has no UI to collect an API key/voice ID interactively. As a narrow,
  CLI-only exception to "UI only" (the UI itself still never reads or
  persists env vars for these), the CLI reads
  `ELEVENLABS_API_KEY`/`ELEVENLABS_VOICE_ID` from the environment so
  `uv run python -m videogen.pipeline` can still run the real `tts` step
  end-to-end for anyone with real credentials set.

## Open questions

None outstanding — all scope decisions were confirmed with the human
before writing the implementation plan (see "User-provided requirements"
and the CLI note above).
