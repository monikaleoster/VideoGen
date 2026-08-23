# Requirements — TTS Step: "Run" No Longer Calls ElevenLabs

## Context

Today, clicking "Run" on the `tts` step's card calls `run_tts`, which
sequentially calls the real ElevenLabs API for every slide with
`has_notes=True` — i.e. simply reaching the `tts` step and pressing the
one button it shows in the `pending` state already spends API
credits/quota for the whole deck, with no per-slide review first. The
existing "Generate All" button (visible once slides are populated)
currently just re-triggers the same full `run_tts`/`reject` call, and the
per-slide "Generate" button calls `regenerate_slide` for one slide only.

The human wants "Run" (and, since Reject reuses the same run function,
"Reject") to stop calling ElevenLabs entirely — it should only prepare
the per-slide list (text boxes populated from `notes_extraction`'s
output, no audio yet) and move to `waiting_approval`. Only "Generate All"
and the per-slide "Generate" button should ever call ElevenLabs.

## User-provided requirements (confirmed 2026-08-23, via AskUserQuestion)

- **"Run = prepare only":** the `tts` step's Run action builds the
  per-slide list (one entry per slide, from `notes_extraction`'s `notes`/
  `has_notes`) with `audio_paths`/`durations_sec` left as `None` for
  every slide, and moves straight to `waiting_approval` — no ElevenLabs
  calls, no API key/voice ID required to do this.
- Generate All and per-slide Generate remain the *only* actions that call
  ElevenLabs, unchanged in what they do once triggered.
- This applies specifically to the **approval-gate UI's per-step Run
  button** (routed through `routes.py`'s `STEPS` table / `/pipeline/tts/
  run` and `/pipeline/tts/reject`). It does **not** change the CLI demo
  entry point (`uv run python -m videogen.pipeline`, `__main__.py` ->
  `runner.run_pipeline`), which has no step-by-step UI and no separate
  "Generate" concept — it keeps calling `tts.run_tts` directly for a
  straight end-to-end run, generating all audio automatically as it does
  today. Confirm this split explicitly during implementation review, since
  it's easy to accidentally break the CLI path while fixing the UI path.

## In scope

- `tts.py`: add a new function (e.g. `prepare_tts`) with the same
  `StepState`/`StepStatus`/`asyncio.Event` approval-gate shape as every
  other step, that does **not** call `_synthesize`/ElevenLabs — it builds
  `TtsOutput(audio_paths=[None] * n, durations_sec=[None] * n)` from the
  slide count in its input, sets `state.output`, transitions to
  `WAITING_APPROVAL`, blocks on `state.approval_event`, then `DONE`.
  `run_tts` (the real-generation function) is left unchanged and kept —
  it's still used by `runner.run_pipeline` for the CLI demo path.
- A slimmer input shape for the prepare path (e.g. `TtsPrepareInput`
  carrying just `notes`/`has_notes`, no `api_key`/`voice_id` — those
  aren't needed to prepare an empty slide list).
- `routes.py`:
  - The `STEPS` table's `tts` entry's `run_fn`/`build_input` switch to
    `tts.prepare_tts` / a new `_tts_prepare_input` that no longer
    requires `api_key`/`voice_id` (drop that `HTTPException` check for
    the Run/Reject path specifically — the existing per-slide `/pipeline/
    tts/slide/{index}/generate` route keeps its own `api_key`/`voice_id`
    requirement unchanged).
  - No new backend route needed for "Generate All" — see UI wiring below.
- `templates/index.html`: change the "Generate All" button's handler.
  Today it calls `postAction("tts", ...)` (Run or Reject, i.e. full
  ElevenLabs generation). Instead, it should sequentially call the
  existing per-slide endpoint (`/pipeline/tts/slide/{index}/generate`,
  the same one the individual "Generate" buttons already use) for every
  slide row in order, awaiting each before starting the next (preserving
  the existing "no concurrent burst against ElevenLabs" behavior),
  skipping any slide whose current text box value is blank (mirrors the
  per-slide route's own 422-on-blank-text behavior and today's
  effective "no-notes slides get no audio" outcome, without needing the
  UI to special-case `has_notes` directly).

## Out of scope

- Any change to `run_tts` itself, or to `runner.run_pipeline`/
  `__main__.py`'s CLI demo flow — that path is intentionally unchanged.
- Any change to the per-slide `/pipeline/tts/slide/{index}/generate`
  route's behavior or requirements (still requires `api_key`, `voice_id`,
  non-empty `text`).
- Retry/rate-limit handling — unchanged from Phase 7's confirmed
  no-auto-retry scope decision.

## Validation bar

- Clicking "Run" on the `tts` step (once `notes_extraction` is `done`)
  populates the per-slide rows with text and no audio, reaches
  `waiting_approval`, and makes **zero** calls to the (mocked, in tests)
  ElevenLabs client.
- Clicking "Reject" behaves the same way — re-prepares without calling
  ElevenLabs (since it reuses the same `run_fn`).
- Clicking "Generate All" sequentially generates real audio for every
  slide with non-blank text, in order, same end result as today's
  behavior.
- Clicking a single slide's "Generate" button is unaffected.
- The CLI demo (`uv run python -m videogen.pipeline`) still produces a
  complete video with real per-slide audio, end to end, with no manual
  "Generate" step required — confirming `run_tts`/`run_pipeline` weren't
  broken by this change.
