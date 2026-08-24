# Validation — TTS Step: "Run" No Longer Calls ElevenLabs

This file is filled in during/after implementation (Plan.md task group 5).
Template below defines what "done" means.

## Automated validation

- [ ] `uv run pytest` passes in full, no regressions.
- [ ] `tests/test_tts.py`: `prepare_tts` produces an all-`None` output of
      the correct length and never calls the mocked ElevenLabs client;
      approval gate still blocks/resumes; existing `run_tts` tests
      unaffected.
- [ ] Route-level tests: `POST /pipeline/tts/run` and `/reject` no longer
      require `api_key`/`voice_id`, produce all-`None` audio, don't call
      ElevenLabs.
- [ ] `tests/test_runner.py`: the CLI path (`run_pipeline` -> `run_tts`)
      still generates real (mocked) audio unchanged.

## Regression validation

- [ ] Per-slide `/pipeline/tts/slide/{index}/generate` route unchanged
      (still requires credentials + non-empty text, still calls
      `regenerate_slide`).
- [ ] CLI demo (`uv run python -m videogen.pipeline`) still produces a
      complete end-to-end video with no manual UI interaction.

## Build / lint / static analysis

- [ ] `uv run pytest` (this repo's build/test gate).

## Manual verification

Performed by: _(fill in)_

1. Browser: `tts` Run after `notes_extraction` is done — confirm slide
   rows appear with text and no audio, and no ElevenLabs call happened
   (check logs/mock).
2. Browser: "Generate All" — confirm real audio appears for every slide
   with notes, sequentially.
3. Browser: single "Generate" on one slide — unaffected.
4. CLI: full pipeline run still produces a complete video with real
   per-slide audio.

## Expected result

- Run/Reject on `tts` never call ElevenLabs; Generate All and per-slide
  Generate remain the only audio-generating actions in the UI; the CLI
  demo path is unaffected.

## Failure conditions

- Run or Reject on `tts` triggers any ElevenLabs call.
- Generate All or per-slide Generate stop working.
- The CLI demo path silently becomes prepare-only (no audio produced).
- Any existing test regresses.

## Evidence the human should provide

- Confirmation of the manual verification steps above.
- `APPROVED` or `CHANGES REQUIRED` before this phase's implementation PR
  is merged.

## Result

_(fill in after implementation)_
