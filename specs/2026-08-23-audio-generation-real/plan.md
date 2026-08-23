# Plan — Audio Generation (Real, ElevenLabs) (Phase 7)

Numbered task groups. Complete and validate each group before moving on.

## 1. ElevenLabs client wrapper
- Objective: a small, testable wrapper around the ElevenLabs TTS call so
  `run_tts` itself stays orchestration-only.
- Tasks:
  1.1. Add the `elevenlabs` SDK (or plain `httpx`/`requests` call, if the
       SDK proves awkward to mock) as a project dependency.
  1.2. Write a function `_synthesize(text, api_key, voice_id) -> bytes`
       (module-private) that calls ElevenLabs with the fixed
       stability/similarity settings and returns raw MP3 bytes. Let any
       API error (auth, rate limit, network) propagate unmodified.
- Dependencies: none.
- Files affected: `pyproject.toml`, `src/videogen/pipeline/tts.py`.
- Validation: unit test with the client call mocked, asserting the
  function is called with the right text/voice/settings and returns the
  mocked bytes; asserting an exception from the mock propagates.
- Independent: yes.

## 2. Real `tts` step
- Objective: replace the stub with real per-slide synthesis, skip logic,
  and duration measurement.
- Tasks:
  2.1. Change `TtsInput` to `notes: list[str]`, `has_notes: list[bool]`,
       `api_key: str`, `voice_id: str`.
  2.2. In `run_tts`: create a fresh per-run temp directory (matching
       `download`'s `tempfile.mkdtemp()` precedent).
  2.3. For each slide, if `has_notes[i]` is `False`: skip the
       ElevenLabs call, append `None` to both `audio_paths` and
       `durations_sec`.
  2.4. If `has_notes[i]` is `True`: call `_synthesize(...)`, write the
       returned bytes to `slide_{i:02d}.mp3` in the temp dir, measure its
       real duration via `ffprobe` (subprocess, off the event loop
       thread via `asyncio.to_thread` alongside the synthesis call),
       append the real path and duration.
  2.5. Calls are made sequentially (one slide at a time, awaited in
       order) — no concurrent burst against the ElevenLabs API.
  2.6. Keep the same `StepState`/`StepStatus`/`asyncio.Event`
       approval-gate shape as every other step.
- Dependencies: task group 1.
- Files affected: `src/videogen/pipeline/tts.py`.
- Validation: unit tests in group 5.
- Independent: no — depends on group 1.

## 3. UI: per-run API key / voice ID fields
- Objective: let the human supply credentials for the `tts` step from
  the browser, held only in that page's in-memory state.
- Tasks:
  3.1. Add two input fields (API key, voice ID) to the `tts` step's
       section in `templates/index.html`, visible before that step's Run
       button; API key field should be a password-type input so it isn't
       shown in plaintext on screen.
  3.2. Wire the JS so those two field values are sent along with the
       `tts` step's "Run" request instead of being read from any stored
       state — nothing written to `localStorage`/cookies/disk.
  3.3. Update `src/videogen/pipeline/ui.py`'s `/pipeline/{step_name}/run`
       route (or the `tts`-specific input-building path) to accept these
       two values from the request body for the `tts` step and build
       `TtsInput` with them, instead of `_tts_input()`'s current
       zero-argument signature. (Other steps' `build_input` callables are
       unaffected — only `tts`'s needs request data.)
- Dependencies: task group 2 (needs the new `TtsInput` shape).
- Files affected: `templates/index.html`, `src/videogen/pipeline/ui.py`.
- Validation: manual — run the pipeline in a browser, confirm the fields
  appear, are required before Run is enabled, and a run with fake
  credentials attempts a real call (surfacing the real API's auth error
  visibly rather than silently mocking success).
- Independent: no — depends on group 2's input shape.

## 4. CLI env-var fallback
- Objective: keep `uv run python -m videogen.pipeline` runnable
  end-to-end for a real ElevenLabs account, per the confirmed CLI
  exception.
- Tasks:
  4.1. In `src/videogen/pipeline/__main__.py`, read
       `ELEVENLABS_API_KEY`/`ELEVENLABS_VOICE_ID` from the environment
       and pass them into the `tts` step's input when building the demo
       `run_pipeline(...)` call chain (or the equivalent per-step input
       construction the CLI uses).
  4.2. If those env vars are unset, fail with a clear error message
       naming the two variables — no silent fallback to fake data.
- Dependencies: task group 2.
- Files affected: `src/videogen/pipeline/__main__.py`.
- Validation: manual — run the CLI with and without the env vars set,
  confirm both behaviors.
- Independent: no — depends on group 2.

## 5. Tests
- Tasks:
  5.1. `tests/test_tts.py`: real step logic with the ElevenLabs client
       call mocked (per group 1's wrapper) —
       - a slide with `has_notes=True` gets a real (mocked-bytes) audio
         file written and a real (measured) duration: use a tiny known
         MP3/silence fixture as the mocked "returned audio" so
         `ffprobe`'s measured duration is deterministic and checkable.
       - a slide with `has_notes=False` gets `None`/`None` and the mocked
         client is asserted **not** called for that slide.
       - a simulated ElevenLabs error (mock raises) propagates out of
         `run_tts` rather than being caught/swallowed.
       - the approval gate still blocks/resumes correctly.
  5.2. `tests/test_runner.py` / `tests/test_pipeline_ui.py`: update any
       calls/assumptions tied to the old stub `TtsInput`/`TtsOutput`
       shape; runner's demo wiring needs some way to supply
       `api_key`/`voice_id` (either the same env-var fallback as the CLI,
       reusing group 4's logic, or a test-only fixture value passed
       directly — whichever keeps these tests network-free).
  5.3. Run the full `uv run pytest` suite, confirm no regressions.
- Dependencies: task groups 1-4.
- Files affected: `tests/test_tts.py` (new), `tests/test_runner.py`,
  `tests/test_pipeline_ui.py`.
- Independent: no — depends on the implementation being in place.

## 6. Validation pass
- Tasks:
  6.1. If real ElevenLabs credentials are available, run one real
       end-to-end synthesis manually and confirm audio quality/duration.
       If no real credentials are available in this environment, note
       that explicitly in `validation.md` rather than fabricating a
       result — the mocked-client tests are the automated substitute,
       not a replacement for the one real manual check this phase's
       roadmap entry calls for.
  6.2. Fill in `specs/2026-08-23-audio-generation-real/validation.md`.
  6.3. Update Phase 7's status in `specs/roadmap.md`.
- Dependencies: task groups 1-5.
- Files affected: `specs/2026-08-23-audio-generation-real/validation.md`,
  `specs/roadmap.md`.
- Independent: no — final step.

## Delegable task groups

Group 1 (client wrapper) is independent enough to build and unit-test on
its own before group 2 needs it. Group 3 (UI) and group 4 (CLI) are
independent of each other once group 2's `TtsInput` shape is settled, and
could be delegated to separate agents in parallel. Group 5 depends on
groups 1-4 all being in place first.
