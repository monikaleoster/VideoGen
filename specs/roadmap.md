# Roadmap

Build order, in small, independently-validatable phases. Each phase should
be small enough to build and validate in one sitting. Do not start a phase
until the previous one is validated — this is the "prove the shape before
the substance" principle from mission.md.

Status legend: ✅ done · 🚧 in progress · ⬜ not started

## Phase 0 — Project scaffold
- Set up `pyproject.toml` with `uv`, base FastAPI app, pytest config.
- One health-check route + one WebSocket echo route, nothing pipeline
  specific yet.
- **Validate:** `uv run` starts the server; health route responds; a
  WebSocket client can connect and receive an echoed message.
- Status: ✅

## Phase 1 — Mock pipeline, single step
- Define the pipeline step interface (input, output, status message) and
  implement it for exactly one step (e.g. notes extraction) as a stub that
  returns fake data after a short delay.
- Wire one `asyncio.Event` gate around it: the step reports "done, waiting
  for approval" and blocks until unblocked.
- **Validate:** run the single stub step via a route/CLI call, confirm it
  blocks, confirm it resumes after the Event is manually set.
- Status: ✅

## Phase 2 — Mock pipeline, all 7 steps
- Extend Phase 1's pattern to stub all seven steps (download, notes
  extraction, TTS, audio upload, embed, render, video upload), chained by
  a single pipeline runner.
- Each step still returns fake data; each has its own approval gate.
- **Validate:** run the full mock pipeline start to finish; confirm every
  step blocks on approval in order and none skip ahead.
- Status: ✅

## Phase 3 — Approval-gate UI
- Build the minimal server-rendered HTML/JS UI: live status via WebSocket,
  per-step detail display, Approve/Reject buttons.
- Reject re-runs just that step (manual re-run, no auto-regeneration, per
  mission.md non-goals).
- **Validate:** drive the full mock pipeline from the browser; confirm
  status/detail messages render correctly and Approve/Reject both work.
- Status: ✅

## Phase 4 — Local PPTX → slide images
- Deviation from the original plan: instead of real Google Drive auth and
  download, the `download` step takes a local filesystem path to an
  already-present `.pptx` (as if it had already been downloaded). Real
  Google Drive integration is deferred — not built in this phase.
- Implement real LibreOffice-headless conversion of that local `.pptx` to
  one PNG image per slide (1920x1080).
- Swap this in for the mock "download" step only.
- **Validate:** given a real local `.pptx` file, image count matches slide
  count, correct order, readable resolution (1920x1080 PNGs).
- Status: ✅

## Phase 5 — Video generation (already validated, re-validate)
- Re-validate the existing video generation step (slide images + audio →
  final MP4) against real images from Phase 4, replacing the placeholder
  images used previously. Real ffmpeg per-slide segment rendering
  (static image + real audio track), concatenated in order; a slide with
  no audio gets a fixed 3-second silent fallback segment rather than
  being dropped. Real duration measured via ffprobe.
- **Validate:** output duration/sync matches expected values, both audio
  and video streams present, graceful fallback for a slide with no audio.
- Status: ✅ (re-validated against real Phase 4/7 inputs 2026-08-23 — see
  `specs/2026-08-23-render-real-and-logging/`; previously marked done
  against placeholders only, which was misleading — the step was still a
  full stub until this work)

## Phase 6 — Notes extraction (real)
- Replace the mock notes-extraction step with real `python-pptx` parsing
  of speaker notes per slide.
- Handle empty-notes slides by flagging them, not crashing.
- **Validate:** run against a real `.pptx`; notes map correctly to slide
  index, including the empty-notes edge case.
- Status: ✅

## Phase 7 — Audio generation (real, ElevenLabs)
- Replace the mock TTS step with real ElevenLabs calls: single voice,
  fixed stability/similarity settings (not user-configurable), voice ID
  and API key entered per run through the approval-gate UI (in-memory
  only, never persisted — deliberate deviation from tech-stack.md's more
  general env-var/`.env` secrets wording, confirmed with the human; see
  `specs/2026-08-23-audio-generation-real/requirements.md`). No retry on
  failure, including rate limits — any failure is reported, not retried
  (also a confirmed deviation from the original plan). A slide with no
  notes (per Phase 6's `has_notes` flag) is skipped, not sent to
  ElevenLabs. The CLI demo entry point (`__main__.py`, no UI) falls back
  to `ELEVENLABS_API_KEY`/`ELEVENLABS_VOICE_ID` env vars as a narrow,
  CLI-only exception.
- **Validate:** generate audio for 1–2 sample notes; confirm audio quality
  and duration are as expected.
- Status: ✅ (real-credential audio quality/duration check completed and
  approved by the human 2026-08-23)

## Phase 8 — Embed audio into PPTX (real)
- Replace the mock embed step with real `python-pptx` logic: insert each
  slide's audio clip and set it to autoplay on slide entry (a manual
  `p:timing` XML edit — `add_movie` alone only wires click-to-play).
  Slides with no audio (Phase 6/7's `None` entries) are left untouched.
  Output is a new local `_with_audio.pptx` file, original never modified
  — no Drive involvement. Failures propagate visibly, no auto-retry.
  Wiring correction: `embed`'s real audio-path input comes from `tts`'s
  output directly, not the still-mocked `audio_upload` step's fake Drive
  IDs (see `specs/2026-08-23-embed-audio-real/requirements.md`).
- Depends on Phases 6 and 7 both being real.
- **Validate:** automated XML/structure check confirming an autoplay
  trigger (not click-only) on every audio-bearing slide; a real
  PowerPoint/LibreOffice playback check is optional corroboration, not
  required for this phase's sign-off (confirmed deviation from the
  original "open the resulting .pptx" wording, which implied manual-only
  validation).
- Status: ✅

## Phase 9 — Drive upload (audio + final video)
- Replace the mock upload steps with real Drive uploads for generated
  audio clips and the final MP4, using the predictable naming convention
  (`slide_01_audio.mp3`, etc.) into the source file's folder.
- **Validate:** files land in the correct Drive folder with correct names.
- Status: ⬜

## Phase 10 — Full real-pipeline dry run
- With every mock replaced (Phases 4–9 all real), run the complete
  pipeline end-to-end on a real deck through the Phase 3 UI.
- **Validate:** matches mission.md's definition of success — final MP4
  where every slide's audio matches its notes and duration, no step
  skipped approval, each step still independently re-runnable.
- Status: ⬜

## Phase 11 — Download step: configurable PPTX path & shared tmp root
- UX/infrastructure improvement on top of Phase 4: the `download` step's
  PPTX path and a shared tmp-root directory (used by every step's scratch
  work dir, not just `download`) become user-supplied via two new UI
  fields, instead of a hardcoded demo fixture path and independent
  per-step OS temp dirs. Blank fields fall back to today's behavior. The
  CLI demo entry point is unaffected.
- **Validate:** custom path/tmp-root fields work end-to-end; every
  downstream step's work dir nests under the shared root; blank fields
  regress to nothing (identical to pre-change behavior).
- Status: ✅ (see `specs/2026-08-23-download-input-config/`; fully
  automatable validation bar — custom path/tmp-root, shared nesting across
  `download`/`tts`/`embed`, and blank-fields no-regression all covered by
  automated tests, 54/54 passing)

## Phase 12 — Notes extraction: per-slide text files + UI links
- UX improvement on top of Phase 6: each slide's extracted notes are also
  written to their own `.txt` file (one per slide, always, including
  empty ones), served via a new route, and linked from the approval-gate
  UI — mirroring the existing per-slide audio link pattern from `tts`.
- **Validate:** one file per slide, byte-for-byte matching extracted
  text; every slide has a working UI link, including the no-notes one.
- Status: ✅ (see `specs/2026-08-23-notes-text-files/`; fully automatable
  validation bar — one file per slide byte-for-byte matching extracted
  text (including the empty no-notes file), route serving at both
  `waiting_approval` and `done`, 404s, and the UI link container all
  covered by automated tests, 59/59 passing)

## Phase 13 — TTS step: "Run" stops auto-generating audio
- UX/cost-safety improvement on top of Phase 7: the approval-gate UI's
  `tts` Run/Reject actions no longer call ElevenLabs — they only prepare
  the per-slide list (text, no audio). Only "Generate All" and per-slide
  "Generate" call ElevenLabs. The CLI demo entry point's full-pipeline
  run is explicitly unaffected — it keeps generating audio automatically
  end to end.
- **Validate:** Run/Reject never call ElevenLabs; Generate All and
  per-slide Generate unaffected; CLI demo path unaffected.
- Status: ✅ (see `specs/2026-08-23-tts-run-no-autogenerate/`; automated
  tests confirm Run/Reject build the per-slide list with zero ElevenLabs
  calls, Generate All/per-slide Generate are unaffected, and the CLI demo
  path (`run_tts`/`run_pipeline`) still auto-generates all audio end to
  end)

## Open questions to resolve along the way

Carried over from the PRD — resolve when the relevant phase is reached,
not before:
- Phase 3 (Reject behavior): fully manual re-run, or regenerate
  automatically with a note attached?
- ~~Phase 7 (voice settings): fixed stability/similarity settings, or
  user-configurable per run?~~ Resolved 2026-08-23: fixed settings (see
  `specs/2026-08-23-audio-generation-real/requirements.md`).
- ~~Phase 7 (chunking): max deck size / notes length before ElevenLabs
  input needs to be chunked?~~ Resolved 2026-08-23: no chunking for v1
  (see `specs/2026-08-23-audio-generation-real/requirements.md`).
