# Validation — Audio Generation (Real, ElevenLabs) (Phase 7)

This file is filled in during/after implementation (Plan.md task group 6).
Template below defines what "done" means.

## Automated validation

- [x] `uv run pytest` passes in full, no regressions in any existing
      suite — 31 passed.
- [x] Unit tests (`tests/test_tts.py`), ElevenLabs client mocked:
  - [x] A slide with `has_notes=True` produces a real audio file (from
        the mocked bytes) at a real path, and a duration measured from
        that file (not a hardcoded/fake number) — verified via a real
        ffprobe read of a real (silent) MP3.
  - [x] A slide with `has_notes=False` produces `audio_paths[i] is None`
        and `durations_sec[i] is None`, and the mocked ElevenLabs client
        is asserted **not called** for that slide.
  - [x] A simulated ElevenLabs error (mock raises) propagates out of
        `run_tts` — the step does not swallow it or produce a fake
        fallback output; verified the step does not reach
        `WAITING_APPROVAL` for a failed run.
  - [x] The step's approval gate still blocks until
        `state.approval_event` is set, then resumes and returns the same
        output.
  - [x] Calls are sequential — `test_mixed_slides_only_calls_api_for_slides_with_notes`
        asserts exactly 2 calls for a 3-slide mixed run, in slide order
        (the implementation's `for` loop awaits each call before the
        next, so there is no concurrency to race).
- [x] `tests/test_runner.py` / `tests/test_pipeline_ui.py`: full pipeline
      chain still completes correctly with the new `TtsInput` shape
      (ElevenLabs client mocked via `_synthesize`), no ordering
      regressions.

## Regression validation

- [x] `download` and `notes_extraction` steps' existing tests still pass
      unmodified.

## Build / lint / static analysis

- [x] `uv run pytest` (this repo's build/test gate).

## Bug found and fixed along the way (required to make this phase's own validation possible, not scope creep)

- **The approval-gate UI's `/pipeline/{step}/run` and `/reject` routes
  hung forever on a step failure.** Both routes only polled
  `step.state.status` for `WAITING_APPROVAL`/`DONE`; a step whose task
  raised an exception (exactly what real `tts` now does on any
  ElevenLabs failure, per this phase's own "fail visibly, don't retry"
  requirement) would never reach either status, so the HTTP request
  hung indefinitely and the exception was only ever logged as "Task
  exception was never retrieved" — invisible to the caller. This
  directly contradicted this phase's own requirement that a failure be
  visible, not silently swallowed. Fixed `_await_step_settled` (and the
  reject route's pre-wait loop) to check the background task for a
  raised exception on every poll tick and, if found, reset the step back
  to `pending` and raise an `HTTPException(502, ...)` with the real error
  — the step is then immediately re-runnable via the same Run action,
  matching the "human retries manually" scope decision. Confirmed via a
  real (network-blocked-in-this-sandbox) ElevenLabs call: before the fix,
  the request hung; after, it returns `502` with the underlying error
  message and the step resets to `pending`.

## Manual verification

Performed by: Claude (session, monikaleoster@gmail.com) — 2026-08-23

1. Confirmed the index page (`GET /`) includes the `tts` step's API key
   (password-type) and voice ID input fields, and that the JS sends their
   live values with the Run/Reject request body.
2. **Real ElevenLabs credentials are not available in this sandbox** (no
   API key was provided, and this environment's outbound network policy
   blocks `api.elevenlabs.io` at the proxy — confirmed via a real attempt,
   which surfaced a proxy 403 rather than a fake success). This step is
   the one part of this phase's validation the automated (mocked) tests
   cannot substitute for; **a human with a real ElevenLabs API key and
   voice ID should run the `tts` step for real against 1-2 sample notes
   and confirm audio quality/duration before this phase is considered
   fully validated.**
3. Triggered a deliberate failure (an invalid API key, which this
   sandbox's network policy turned into a proxy error) via a real HTTP
   request against the running app: the request returned
   `502 {"detail": "Step 'tts' failed: 403 Forbidden"}` rather than
   hanging or silently succeeding, and the step's status reset to
   `pending`, confirming it's immediately re-runnable via the same Run
   action (the "human retries manually" scope decision) rather than
   needing a separate unstick mechanism. (This surfaced and led to the
   route-hang bug fix above — before the fix, this same request hung.)
4. Confirmed a slide with no notes (the fixture's "Thank You" slide) is
   skipped — ran the full pipeline through `download` and
   `notes_extraction`, confirmed via `tests/test_tts.py`'s mixed-slide
   test that the mocked ElevenLabs client is called exactly twice for
   the fixture's 3 slides (2 with notes, 1 without), with `None` in both
   output lists for the skipped slide.
5. Ran `uv run python -m videogen.pipeline` with
   `ELEVENLABS_API_KEY`/`ELEVENLABS_VOICE_ID` unset: exited with code 1
   and a clear error naming both variables, no silent fake result.

## Expected result

- Slides with notes get real ElevenLabs audio and a real measured
  duration; slides without notes are cleanly skipped and flagged as such.
- Failures are visible, not swallowed; the human's existing Reject/re-run
  flow is the only retry mechanism, per the confirmed scope decision.
- No regressions elsewhere in the pipeline.

## Failure conditions

- Any slide silently gets fake/placeholder audio instead of a real
  ElevenLabs call (except deliberately-skipped no-notes slides).
- An ElevenLabs error is caught and hidden rather than surfaced.
- A skipped slide is indistinguishable from a real (but very short) clip.
- Any existing test regresses.

## Evidence the human should provide

- Confirmation of the manual verification steps above, including
  real-credential audio quality/duration if available.
- `APPROVED` or `CHANGES REQUIRED` per the human-validation gate before
  this phase's implementation PR is merged.

## Result

- Automated checks: done — 31/31 tests pass.
- Manual verification: done for everything not requiring real ElevenLabs
  network access, which this sandbox cannot reach; **real-credential
  audio-quality/duration verification (item 2 above) is still owed by a
  human before this phase is fully validated.**
- Outcome: ready to merge pending that one human-only check.

## Roadmap update

Phase 7 marked 🚧 (not ✅) in `specs/roadmap.md` — implementation and
automated (mocked) validation are done, but real-credential audio
quality/duration verification is still owed by a human before this
phase is considered fully validated and the status flips to ✅.
