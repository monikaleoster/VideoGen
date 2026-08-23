# Validation Plan — Audio Generation (Real, ElevenLabs) (Phase 7)

Traces to `specs/2026-08-23-audio-generation-real/requirements.md` and
`plan.md`.

## Automated validation

### Unit test validation

- `uv run pytest` passes in full, with the new/updated `tts` tests
  (`tests/test_tts.py` or equivalent) covering:
  - A `has_notes: True` slide produces a real `.mp3` file path + duration,
    via a mocked ElevenLabs client call (assert the mock received the
    expected voice ID sourced from env and the voice settings passed in
    the step's input).
  - A `has_notes: False` slide results in **zero** ElevenLabs mock calls
    and a "no audio" record for that slide, distinguishable from a
    generated clip.
  - A mocked ElevenLabs failure (exception or error response) causes the
    step to fail: the mock is asserted called **exactly once** for that
    slide (proving no retry), and `state.status` never reaches
    `WAITING_APPROVAL` for that run.
  - An all-`has_notes: False` run makes zero calls, produces an
    all-"no audio" result, and still reaches `WAITING_APPROVAL` -> `DONE`
    through the normal approval gate (this is a valid outcome, not a
    failure).
  - The approval gate itself (block on `state.approval_event`, resume to
    `DONE` once set) works unchanged, for a run where all calls succeed.
  - A missing `ELEVENLABS_API_KEY` (or voice ID) env var fails clearly
    before any ElevenLabs call is attempted (assert zero mock calls).
- No test in the suite makes a live network call — verified by mock
  call-count/argument assertions, not merely by tests passing (a test that
  happens to pass without asserting the mock was used would not satisfy
  this).

### Integration test validation

- `tests/test_runner.py`'s full 7-step chain still completes correctly
  end-to-end with `tts`'s new output shape threaded through
  `audio_upload` and `render` without crashing, using mocked ElevenLabs
  calls (same approach as the unit tests — no live network in the
  integration path either).
- Confirm `notes_extraction`'s `has_notes` output reaches `tts` correctly
  through `runner.py`'s wiring (a slide flagged `has_notes: False` by
  `notes_extraction` is the same slide skipped by `tts` in the same run).

### E2E test validation

Not applicable as an automated suite for this phase — the roadmap's actual
end-to-end validation ("generate audio for 1–2 sample notes, confirm audio
quality and duration") requires a real ElevenLabs API key and is performed
as **manual verification** below, per the confirmed test-strategy decision
in requirements.md (mocked unit/integration tests only; no live/opt-in
automated smoke test in this phase).

### Regression validation

- Existing test suites for `download`, `notes_extraction`, `audio_upload`,
  `embed`, `render`, `video_upload` still pass unchanged (this phase
  touches only `tts.py` and the wiring call sites listed in `plan.md`).
- `uv run python -m videogen.pipeline` still runs the full mock/real mix
  end-to-end without hanging or crashing (watch for the same kind of race
  condition Phase 6 found and fixed in the approval-simulation polling
  helpers — confirm `tts`'s real (fast, if all calls are mocked/stubbed in
  this check) completion doesn't reintroduce it).

### Build validation

- `uv sync` succeeds with `elevenlabs` and `python-dotenv` added to
  `pyproject.toml`/`uv.lock`.
- The FastAPI app and CLI entry point both start without error whether or
  not a `.env` file / the required env vars are present (absence is only
  an error at the point `run_tts` actually needs the credentials, per
  requirements.md's edge case).

### Lint/static analysis validation

- Whatever lint/type-check tooling the repo already runs (if any is
  configured — check for a `ruff`/`mypy` config) passes on the changed
  files. If no such tooling is configured in this repo yet, this step is
  a no-op — do not introduce new tooling as part of this phase.

## Manual verification

The human performing this must have a real ElevenLabs API key and a real
voice ID.

1. Set `ELEVENLABS_API_KEY` and the voice-ID env var in a local `.env`
   (do not commit it).
2. Run `run_tts` directly (or via the CLI/UI) against 1–2 real sample
   notes text strings — e.g. using `tests/fixtures/sample_deck.pptx`'s
   real extracted notes from `notes_extraction`, or a couple of short
   hand-written strings.
3. Confirm each generated `.mp3` file exists on disk at the expected path
   and is playable.
4. Listen to the generated audio and confirm:
   - It clearly speaks the input notes text (no truncation, no garbled
     audio).
   - It sounds like the configured voice ID (not a default/fallback
     voice).
   - Its duration is plausible for the length of the input text (not 0
     seconds, not wildly longer than a normal speaking pace would
     produce).
5. Run once against a slide with empty notes (`has_notes: False`) in the
   same batch and confirm no ElevenLabs call was made for it (e.g. via
   logs, or by confirming no audio file was written for that slide) while
   the other slides' audio still generated normally.
6. Temporarily use an invalid API key or voice ID and confirm the step
   fails clearly (a visible error, not a hang or a silent "success" with
   no audio) and does not retry (only one failed attempt visible in
   logs/output).

### Expected result

- Real, correctly-voiced, correctly-timed `.mp3` audio for every
  `has_notes: True` slide; no ElevenLabs calls for `has_notes: False`
  slides; a clear, non-retried failure on bad credentials.

### Failure conditions

- Generated audio is silent, garbled, truncated, or clearly the wrong
  voice.
- An ElevenLabs call is made for a `has_notes: False` slide.
- A failure is retried (multiple call attempts visible for the same
  slide/credential error) or is silently swallowed (step reaches
  `WAITING_APPROVAL` despite a failed call).
- The step hangs instead of failing or completing.

### Evidence the human should provide

- Confirmation (pass/fail) for each of the 6 manual steps above.
- The generated `.mp3` file(s) or a description of what was heard, for at
  least one successful run.
- Any error message text observed during the bad-credentials check (step
  6), to confirm it's a clear failure and not a hang.

## Human decision

Please confirm one:

- `APPROVED` — merge the implementation
- `CHANGES REQUIRED` — provide feedback
