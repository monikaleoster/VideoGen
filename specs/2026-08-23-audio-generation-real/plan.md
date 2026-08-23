# Implementation Plan — Audio Generation (Real, ElevenLabs) (Phase 7)

Traces to `specs/2026-08-23-audio-generation-real/requirements.md`.

## 1. Task Group 1 — Dependencies & config plumbing

**Objective:** Add the packages and env-var loading this phase needs before
any step logic changes.

- Task 1.1: Add `elevenlabs` and `python-dotenv` to `pyproject.toml`
  dependencies; update `uv.lock` (`uv add elevenlabs python-dotenv`).
- Task 1.2: Wire `.env` loading (e.g. `load_dotenv()` at app/CLI startup) so
  `ELEVENLABS_API_KEY` and the voice-ID env var are available wherever
  `run_tts` executes (CLI entry point in `__main__.py`, and the FastAPI app
  startup for the HTTP path).
- Task 1.3: Add a `.env.example` (or extend an existing one) documenting
  the two required env vars, without committing real secrets.

**Dependencies:** None — first group.

**Files/components affected:** `pyproject.toml`, `uv.lock`,
`src/videogen/pipeline/__main__.py`, FastAPI app startup (wherever it
lives, e.g. `src/videogen/pipeline/app.py` or similar), new/updated
`.env.example`.

**Validation criteria:** `uv sync` succeeds; app/CLI startup doesn't error
when `.env` is absent (env vars simply unset, surfaced later per Task 2.4
not here).

**Independent:** Yes — no dependency on the other groups; can be done
first in isolation.

---

## 2. Task Group 2 — Real `tts` step implementation

**Objective:** Replace `src/videogen/pipeline/tts.py`'s stub with real
ElevenLabs calls per the confirmed requirements (skip on `has_notes:
False`, no retry, real `.mp3` output, user-configurable voice settings,
env-sourced credentials).

- Task 2.1: Define the new `TtsInput` shape: per-slide `notes: list[str]`,
  `has_notes: list[bool]` (or equivalent), and voice-settings fields
  (stability, similarity, at minimum) as required input — no per-run
  API-key/voice-ID fields.
- Task 2.2: Implement the ElevenLabs call path: for each `has_notes: True`
  slide, call the ElevenLabs client with the given voice settings, write
  the returned audio to an `.mp3` file in a local per-run working
  directory (naming convention consistent with `slide_XX_audio.mp3`), and
  capture its duration (via the SDK response if available, otherwise via
  a lightweight audio-length probe of the written file).
- Task 2.3: Implement the skip path for `has_notes: False` slides — zero
  ElevenLabs calls, "no audio" recorded distinguishably (decide exact
  `TtsOutput` shape here, consistent with `notes_extraction`'s
  `has_notes` pattern, per requirements.md's "Open questions" note).
- Task 2.4: Implement failure handling: any ElevenLabs call exception
  (including a 429/rate-limit response) propagates as a step failure with
  no retry attempt; missing/empty API key or voice ID env var is checked
  and fails clearly before any call is attempted.
- Task 2.5: Keep the existing `StepState`/`StepStatus`/`asyncio.Event`
  gate: `RUNNING` -> (all calls complete) -> `WAITING_APPROVAL` -> (await
  approval) -> `DONE`, matching every other step's shape exactly. A
  failure during the `RUNNING` phase must not transition to
  `WAITING_APPROVAL`.
- Task 2.6: Run ElevenLabs calls off the event loop thread if the SDK is
  blocking (same `asyncio.to_thread` pattern `notes_extraction` uses for
  `python-pptx`), so the WebSocket status push keeps working during TTS.

**Dependencies:** Task Group 1 (needs `elevenlabs`/`python-dotenv`
installed and env loading wired).

**Files/components affected:** `src/videogen/pipeline/tts.py`.

**Validation criteria:** Covered by Task Group 3's unit tests; manually,
`run_tts` against real fixture notes with a real API key produces valid
`.mp3` files (deferred to `validation.md`'s manual steps).

**Independent:** No — depends on Task Group 1's dependency/env plumbing
being in place, but is otherwise self-contained (touches only `tts.py`).

---

## 3. Task Group 3 — Wiring (`runner.py`, `ui.py`, `routes.py`)

**Objective:** Thread `notes_extraction`'s real `has_notes` output and a
source of voice-settings values through to `tts`'s new input shape,
everywhere `run_tts` is currently called with the old `TtsInput(notes=...)`
shape.

- Task 3.1: Update `src/videogen/pipeline/runner.py`'s `run_pipeline` call
  site to pass `has_notes` from `notes_output` and voice-settings values
  into the new `TtsInput`. Decide during implementation where
  voice-settings values come from for a full pipeline run (e.g. a
  `run_pipeline` parameter with a sane default, consistent with how
  `local_pptx_path` is already threaded through) — this is a wiring
  detail, not a new product decision, since requirements.md already
  settled that voice settings are per-run input.
- Task 3.2: Update `src/videogen/pipeline/ui.py`'s demo/manual-run wiring
  if it hardcodes the old `TtsInput` shape.
- Task 3.3: Update `src/videogen/pipeline/routes.py`'s legacy single-step
  demo route (per the Phase 6 precedent) if it constructs `TtsInput`
  directly with the old shape.
- Task 3.4: Update `src/videogen/pipeline/__main__.py` if it constructs
  `TtsInput` or otherwise needs updating for the new shape (per the Phase
  6 precedent of `__main__.py` needing a matching fix).

**Dependencies:** Task Group 2 (needs the new `TtsInput`/`TtsOutput` shape
to exist).

**Files/components affected:** `src/videogen/pipeline/runner.py`,
`src/videogen/pipeline/ui.py`, `src/videogen/pipeline/routes.py`,
`src/videogen/pipeline/__main__.py`.

**Validation criteria:** `uv run python -m videogen.pipeline` and the
FastAPI UI both still run the full 7-step chain end-to-end without
crashing (with ElevenLabs mocked/stubbed for this non-live smoke check, or
run manually with real credentials per `validation.md`).

**Independent:** No — depends on Task Group 2's finished `tts.py` shape.

---

## 4. Task Group 4 — Unit tests (mocked ElevenLabs)

**Objective:** Cover the acceptance criteria from requirements.md with
tests that mock the ElevenLabs client/HTTP layer — no live network access.

- Task 4.1: Test — a slide with `has_notes: True` produces an audio file
  path + duration; the mock is called with the expected voice
  ID/settings (voice ID via env var patched in the test).
- Task 4.2: Test — a slide with `has_notes: False` results in zero mock
  calls and a "no audio" record for that slide.
- Task 4.3: Test — a mocked ElevenLabs failure (raise, or a 429-style
  response depending on how the SDK surfaces it) causes the step to fail,
  the mock is asserted called exactly once (no retry), and the step does
  not reach `WAITING_APPROVAL`.
- Task 4.4: Test — a run where every slide has `has_notes: False`
  produces an all-"no audio" result, makes zero calls, and still reaches
  `WAITING_APPROVAL`/`DONE` via the normal approval gate.
- Task 4.5: Test — the approval gate itself (block on `approval_event`,
  resume to `DONE`) still works exactly as before for a successful run,
  matching the existing pattern from `tests/test_notes_extraction.py` /
  the original `tts` stub's test (if one exists) adapted to the new input
  shape.
- Task 4.6: Test — missing API key/voice ID env var fails clearly before
  any ElevenLabs call is attempted.
- Task 4.7: Update `tests/test_runner.py` if it constructs `TtsInput`
  directly or asserts on the old stub's fake-duration output.

**Dependencies:** Task Group 2 (needs the real `tts.py` implementation to
test against). Can run in parallel with Task Group 3 once Task Group 2 is
done, since tests target `tts.py` directly and don't require the wiring
changes — except Task 4.7, which depends on Task Group 3's `runner.py`
changes.

**Files/components affected:** new/updated `tests/test_tts.py` (or
equivalent), `tests/test_runner.py`.

**Validation criteria:** `uv run pytest` passes; no test makes a live
network call (verify via mock assertions, not just "tests pass").

**Independent:** Partially — Tasks 4.1–4.6 can be delegated to an
independent test-writing agent once Task Group 2 lands; Task 4.7 needs
Task Group 3 to have landed first.

---

## 5. Task Group 5 — Repository doc updates

**Objective:** Make `specs/tech-stack.md` and `specs/roadmap.md` match the
confirmed no-retry decision, per requirements.md's "Repository constraint
updates" section.

- Task 5.1: Update `specs/tech-stack.md`'s ElevenLabs integration bullet
  to remove "retry on transient failures" and reflect the no-retry,
  report-the-failure decision.
- Task 5.2: Update `specs/roadmap.md` Phase 7's line to remove
  "rate-limit-aware, retry on transient failure" and reflect the same
  decision (status stays ⬜ until this phase's implementation PR merges,
  flipped to ✅ at that point per the existing convention seen on Phases
  0–6).

**Dependencies:** None functionally, but should land alongside the rest of
this spec commit so the docs and the requirements they describe don't
drift apart even temporarily.

**Files/components affected:** `specs/tech-stack.md`, `specs/roadmap.md`.

**Validation criteria:** Manual read-through — no remaining "retry"
language describing this step's behavior anywhere in either doc.

**Independent:** Yes — pure doc edits, no code dependency.

---

## Task groups safe to delegate to independent agents

- **Task Group 4** (unit tests) can be delegated to a separate testing
  agent once Task Group 2's `tts.py` lands, in parallel with Task Group 3
  (wiring) — both depend on Task Group 2 but not on each other, except for
  Task 4.7 which waits on Task Group 3.
- **Task Group 5** (doc updates) is fully independent and can be done at
  any point, in parallel with everything else.
- Task Groups 1, 2, and 3 are sequential (each depends on the previous)
  and should not be parallelized.
