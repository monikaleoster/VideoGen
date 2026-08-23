# Requirements — Audio Generation (Real, ElevenLabs) (Phase 7)

## Context

Phases 0–6 are done and merged: scaffold, all 7 mocked pipeline steps, the
approval-gate UI, the real `download` step (local `.pptx` -> LibreOffice
slide images), and the real `notes_extraction` step (`python-pptx` speaker
notes, per-slide `has_notes` flag). This phase replaces the mock `tts` step
(`src/videogen/pipeline/tts.py`) with real ElevenLabs text-to-speech, per
`specs/roadmap.md` Phase 7.

## User-provided requirements (confirmed 2026-08-23)

- **Empty-notes slides:** a slide flagged `has_notes: False` by
  `notes_extraction` is skipped for audio generation — no ElevenLabs call is
  made for it. Its output record reflects "no audio clip" rather than an
  empty/silent file. This step still produces a result and still gates on
  human approval the same as every other step; skipping is per-slide, not a
  reason to skip the step's approval gate.
- **Voice settings:** stability/similarity (and any other per-voice
  ElevenLabs generation settings this phase uses) are **user-configurable
  per run**, not hardcoded. They are passed as part of the step's input,
  with the same env-var-driven pattern deferred per the credentials
  decision below only for the API key and voice ID (see next point) —
  stability/similarity are values the caller can vary per invocation.
- **Credentials:** the ElevenLabs API key and voice ID are supplied via
  environment variables / a local `.env` (via `python-dotenv`), matching
  `specs/tech-stack.md`'s stated secrets convention. No per-run override
  input for these two values in this phase.
- **Chunking:** out of scope for v1. Each slide's full notes text is sent
  to ElevenLabs as a single request, uncapped. Revisit only if a real deck
  actually hits an ElevenLabs input-length limit in practice.
- **Retry / failure handling — deviates from `tech-stack.md` and the
  roadmap's Phase 7 line, confirmed with the human 2026-08-23:** the step
  does **not** retry on any failure, transient or otherwise (no
  rate-limit/429 retry, no 5xx retry, no backoff). Any ElevenLabs call
  failure (network error, non-2xx response, timeout) is reported as a
  step-level failure — the step does not silently continue or swallow the
  error. `specs/tech-stack.md` and `specs/roadmap.md` Phase 7's current
  wording ("rate-limit-aware, retry on transient failure") are updated by
  this phase's spec commit to match this decision (see "Repository
  constraint updates" below); this requirements.md is the record of that
  deviation and why (explicit human decision, not an oversight).
- **Output format:** each generated slide's audio is saved as a real
  `.mp3` file on local disk, in a local per-run temp/output directory
  (matching the `slide_XX_audio.mp3` naming convention `tech-stack.md`
  already specifies for the later Drive-upload naming), for the next step
  (`audio_upload`) to pick up. Not in-memory bytes only.
- **Testing:** the ElevenLabs client/HTTP layer is mocked in tests — no
  live network access required to run the test suite, per
  `specs/tech-stack.md`'s "testable in isolation" principle and
  `mission.md`'s "every step stands alone" principle. No live/opt-in
  smoke test against the real API is included in this phase's automated
  suite; the roadmap's "generate audio for 1–2 sample notes, confirm audio
  quality and duration" validation is done as **manual** verification
  (see `validation.md`), run by a human with a real API key.

## Repository constraint updates

This phase's requirements deliberately diverge from two existing documents.
Both are updated as part of this spec (not the implementation) so the specs
stay the source of truth:

- `specs/tech-stack.md`: "Calls must respect ElevenLabs rate limits and
  retry on transient failures" is replaced with wording reflecting the
  no-retry, report-the-failure decision above.
- `specs/roadmap.md` Phase 7: "rate-limit-aware, retry on transient
  failure" is replaced with wording reflecting the same decision.

## In scope

- Replace `src/videogen/pipeline/tts.py`'s stub body with real logic:
  - New input shape carrying: the list of per-slide notes text (as today),
    the parallel `has_notes` flags from `notes_extraction`'s output (or
    equivalent), and per-run voice settings (stability, similarity — at
    minimum; exact ElevenLabs parameter set follows the `elevenlabs` SDK's
    generation-settings shape).
  - Voice ID and API key are read from environment variables (via
    `python-dotenv`), not from step input.
  - For each slide with `has_notes: True`, call the ElevenLabs API once
    (single voice, no chunking) to synthesize audio, write the result to
    an `.mp3` file in a local per-run working directory, and record its
    path and duration.
  - For each slide with `has_notes: False`, skip the ElevenLabs call
    entirely; record "no audio" for that slide in a way downstream code
    and tests can distinguish from "audio was generated" (e.g. `None` in
    `audio_paths`, paired with the existing `has_notes` flag or an
    equivalent per-slide indicator) — exact shape decided during
    implementation, consistent with `notes_extraction`'s `has_notes`
    pattern.
  - On any ElevenLabs call failure (this includes both a definite
    rate-limit response and any other failure — no differentiated retry
    behavior for either), the step fails: it raises/surfaces the error
    rather than catching and continuing, and does not transition to
    `WAITING_APPROVAL` for that run. Whatever partial audio was already
    generated in this run is left as-is (no automatic cleanup requirement
    in this phase).
  - Keep the same `StepState`/`StepStatus`/`asyncio.Event` approval-gate
    shape as every other step for the slides that do complete — this
    phase only changes what happens *inside* `run_tts` up to that gate.
- Add `elevenlabs` (or direct HTTP via an existing HTTP client) and
  `python-dotenv` as project dependencies (`pyproject.toml` / `uv.lock`),
  matching `tech-stack.md`'s stated approach; wire `.env` loading into the
  app so `ELEVENLABS_API_KEY` / voice ID env vars are available at runtime.
- Update `src/videogen/pipeline/runner.py`'s call site to pass
  `notes_extraction`'s `has_notes` output through to `tts`'s new input
  shape, plus voice-setting values (source of those values — e.g. a fixed
  default in the runner, a CLI flag — decided during implementation,
  consistent with how other per-run parameters like `local_pptx_path`
  already flow through `runner.py`/`__main__.py`).
- Update `src/videogen/pipeline/ui.py` and `src/videogen/pipeline/routes.py`
  if they hardcode a `tts` input shape that no longer matches (matching the
  pattern of the Phase 6 wiring fix).
- Tests: mocked-ElevenLabs unit tests covering — a slide with notes
  produces an audio file path + duration; a `has_notes: False` slide is
  skipped with no ElevenLabs call made; an ElevenLabs call failure
  surfaces as a step failure (no retry attempted, verified via call-count
  assertions on the mock); the step's approval gate (block/resume via
  `asyncio.Event`) still works exactly as before for a successful run.

## Explicitly out of scope

- Any retry, backoff, or rate-limit-aware waiting logic — explicitly
  decided against for this phase (see above).
- Chunking long notes text into multiple ElevenLabs calls.
- Multiple voices or per-speaker voice switching (per `mission.md`'s
  stated non-goal).
- A live/opt-in automated test that calls the real ElevenLabs API — audio
  quality/duration validation for this phase is manual only.
- Any change to steps other than `tts` (and the minimal wiring changes in
  `runner.py`/`ui.py`/`routes.py` needed to pass `has_notes` and voice
  settings through) — `download`, `notes_extraction`, `audio_upload`,
  `embed`, `render`, `video_upload` are untouched beyond that wiring.
- Real Google Drive integration — still deferred per Phase 4's recorded
  scope decision, unaffected by this phase.
- Any change to how a `has_notes: False` slide is handled *downstream* of
  `tts` (e.g. `render`'s "graceful fallback for a slide with no audio" from
  Phase 5) — this phase only produces the "no audio for this slide" signal,
  it does not change how later steps consume it beyond accepting `None`/an
  equivalent in `audio_paths` without crashing the pipeline chain itself.

## Acceptance criteria

- Given per-slide notes text and `has_notes` flags matching
  `notes_extraction`'s real output shape, `run_tts`:
  - Generates a real `.mp3` file (via ElevenLabs, mocked in tests) for
    every slide with `has_notes: True`, using the voice ID/API key from
    environment variables and the stability/similarity settings passed in
    the step's input.
  - Makes zero ElevenLabs calls for any slide with `has_notes: False`, and
    records "no audio" for it distinguishably from a generated clip.
  - On a simulated ElevenLabs failure (mocked), the step fails without
    retrying (assert the mock was called exactly once for that slide) and
    without proceeding to `WAITING_APPROVAL`.
  - For a run where every ElevenLabs call succeeds, the step reaches
    `WAITING_APPROVAL`, blocks on `state.approval_event`, and resumes to
    `DONE` once the event is set — unchanged from every other step's gate
    behavior.
- `uv run pytest` passes with the above covered by mocked-ElevenLabs tests
  and no live network access.
- Manual validation (`validation.md`): a human with a real ElevenLabs API
  key and voice ID runs the step against 1–2 real sample notes and
  confirms audio quality and duration are as expected.

## Edge cases

- A slide with `has_notes: False` — no ElevenLabs call, no crash, later
  steps still receive a well-formed (if partial) result for that slide.
- ElevenLabs returns a rate-limit (429) response — treated identically to
  any other failure: reported, not retried (per the confirmed deviation
  above).
- ElevenLabs returns a non-2xx error, or the request times out/raises a
  network exception — same as above, reported and step fails.
- A run where every single slide has `has_notes: False` — the step makes
  zero ElevenLabs calls, produces an all-"no audio" result, and still
  reaches `WAITING_APPROVAL` normally (this is not treated as a failure
  case; it's a valid, if narration-free, run).
- Missing `ELEVENLABS_API_KEY` / voice ID env var at runtime — the step
  fails clearly (e.g. a clear error before attempting any call) rather
  than making a call with an empty/`None` credential.

## Constraints (from specs/tech-stack.md, as updated by this phase)

- `elevenlabs` Python SDK or direct HTTP calls for text-to-speech, single
  voice per run, driven by a user-supplied voice ID and API key read from
  environment variables via `python-dotenv`.
- The step still follows the same `StepState`/`StepStatus`/
  `asyncio.Event` approval-gate shape as every other step.
- pytest + pytest-asyncio, testable with mocked ElevenLabs calls and no
  network access required.
- File naming for generated audio stays predictable and slide-indexed
  (e.g. `slide_01_audio.mp3` or equivalent local working-directory name),
  never freeform or timestamp-based, per `tech-stack.md`'s conventions
  section.

## Decisions made with the human

- Empty-notes slides: skip audio generation (not fail, not
  silent/placeholder audio).
- Voice settings: user-configurable per run, not fixed.
- Chunking: none for v1.
- Credentials: environment variables / `.env` only, no per-run override.
- Retry policy: **no retry — report the failure.** This is a confirmed
  deviation from the current wording of `tech-stack.md` and
  `specs/roadmap.md` Phase 7; both documents are updated by this spec to
  match.
- Test strategy: mock the ElevenLabs client/HTTP layer; audio
  quality/duration validation against the real API is manual, not
  automated.
- Output format: real `.mp3` files on local disk, not in-memory-only
  bytes.

## Open questions

None outstanding — scope was confirmed with the human before writing this
implementation plan (see "Decisions made with the human" above). The exact
shape of "no audio" in `TtsOutput` (e.g. `None` entries in `audio_paths`
vs. a separate `has_audio: list[bool]` mirroring `notes_extraction`'s
`has_notes`) is left as an implementation-time detail consistent with the
existing `has_notes` pattern, not a product-requirements question.
