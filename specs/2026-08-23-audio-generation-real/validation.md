# Validation — Audio Generation (Real, ElevenLabs) (Phase 7)

This file is filled in during/after implementation (Plan.md task group 6).
Template below defines what "done" means.

## Automated validation

- [ ] `uv run pytest` passes in full, no regressions in any existing
      suite.
- [ ] Unit tests (`tests/test_tts.py`), ElevenLabs client mocked:
  - [ ] A slide with `has_notes=True` produces a real audio file (from
        the mocked bytes) at a real path, and a duration measured from
        that file (not a hardcoded/fake number).
  - [ ] A slide with `has_notes=False` produces `audio_paths[i] is None`
        and `durations_sec[i] is None`, and the mocked ElevenLabs client
        is asserted **not called** for that slide.
  - [ ] A simulated ElevenLabs error (mock raises) propagates out of
        `run_tts` — the step does not swallow it or produce a fake
        fallback output.
  - [ ] The step's approval gate still blocks until
        `state.approval_event` is set, then resumes and returns the same
        output.
  - [ ] Calls are made sequentially, not concurrently (assert call order
        / no overlapping in-flight calls against the mock).
- [ ] `tests/test_runner.py` / `tests/test_pipeline_ui.py`: full pipeline
      chain still completes correctly with the new `TtsInput` shape, no
      ordering regressions.

## Regression validation

- [ ] `download` and `notes_extraction` steps' existing tests still pass
      unmodified.

## Build / lint / static analysis

- [ ] `uv run pytest` (this repo's build/test gate).

## Manual verification

Performed by: <fill in> — <date>

1. Run the full pipeline from the browser UI against the fixture deck;
   confirm the `tts` step's new API key / voice ID fields appear before
   its Run button and are required.
2. **If real ElevenLabs credentials are available in this environment:**
   run the `tts` step for real against 1-2 sample notes; confirm the
   returned audio's quality and duration are as expected by listening to
   the output file(s). **If no real credentials are available:** state
   that explicitly here rather than fabricating a result — this step is
   the one part of this phase's validation the automated (mocked) tests
   cannot substitute for, and it should be completed by a human with
   real credentials before this phase is considered fully validated.
3. Trigger a deliberate failure (e.g. an invalid API key) and confirm the
   step visibly fails rather than silently producing fake output, and
   that the human can manually re-run it via the existing Reject action
   once corrected.
4. Confirm a slide with no notes (the fixture's "Thank You" slide) is
   skipped — no ElevenLabs call attempted, `None` in both output lists —
   and does not block or break the rest of the run.
5. Run `uv run python -m videogen.pipeline` with
   `ELEVENLABS_API_KEY`/`ELEVENLABS_VOICE_ID` unset — confirm it fails
   with a clear error naming those variables, not a silent fake result.

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

Not yet run — implementation has not started. This section is filled in
after Plan.md's task group 6.

## Roadmap update

Not yet applied — `specs/roadmap.md` Phase 7 status stays ⬜ until this
validation is complete and the human has signed off.
