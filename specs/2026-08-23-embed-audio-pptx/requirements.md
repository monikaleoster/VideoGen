# Requirements — Embed Audio Into PPTX (Real) (Phase 8)

## Context

Phases 0-7 are done and merged: scaffold, all 7 mocked pipeline steps, the
approval-gate UI, the real `download` step (local `.pptx` -> slide images),
the real `notes_extraction` step (`python-pptx` speaker notes + `has_notes`
flag), and the real `tts` step (ElevenLabs narration per slide, `None` for
slides with `has_notes=False`). This phase replaces the mock `embed` step
with real `python-pptx` logic that inserts each slide's narration audio and
sets it to autoplay on slide entry, per `specs/roadmap.md` Phase 8 and
`specs/tech-stack.md`'s stated use of `python-pptx` for embedding audio.

## User-provided requirements (confirmed 2026-08-23)

- **No-audio slides:** a slide with `has_notes=False` (no TTS clip was
  generated for it in Phase 7) gets a short, fixed-duration silent audio
  clip embedded instead of being left without any autoplay audio element.
  Recommended duration: 1 second of silence. This keeps every slide
  uniform (always has an autoplay audio element) for whatever Phase 10's
  final render/duration logic expects, rather than branching per-slide on
  "has embedded audio or not."
- **Re-run / idempotency:** the embed step must be safely re-runnable. If
  a slide already has embedded audio from a previous run of this step
  (e.g. after a human rejects a slide's TTS output, it's regenerated via
  Phase 7's per-slide regenerate, and the embed step runs again), the step
  removes that slide's previously-embedded audio and inserts the current
  clip — it does not fail, and does not leave two audio elements on one
  slide.
- **Step shape:** same pattern as every other pipeline step — one `embed`
  step in the runner with its own `StepState`/`StepStatus`/
  `asyncio.Event` approval gate, shown in the approval-gate UI like
  `notes_extraction`/`tts`. Not per-slide gating.
- **Media visibility:** the embedded audio's icon/media placeholder is
  hidden on the slide during playback (not the default visible speaker
  icon) — autoplay audio should be inaudible-until-played... audible
  automatically but visually unobtrusive, matching a clean final-video
  look.
- **I/O scope:** this step reads Phase 7's audio directly from local temp
  files within the same pipeline run (not from Drive — Drive upload is
  Phase 9, still deferred) and reads/writes a local `.pptx` copy only. No
  Drive interaction in this phase.

## In scope

- Replace `src/videogen/pipeline/embed.py`'s stub body with real logic:
  - Take the real local `.pptx` path (from `download`'s output) and the
    real per-slide audio paths from `tts`'s output
    (`list[str | None]`, `None` where `has_notes=False`) as input —
    **not** `drive_file_ids` (the current stub's input references the
    mock `audio_upload` step's fake Drive IDs; since Phase 9's real Drive
    upload doesn't exist yet, this phase must read local audio paths
    directly from `tts_output.audio_paths` instead). This is a technical
    consequence of the confirmed "local only" I/O scope, not a new
    product decision.
  - For each slide, open the deck with `python-pptx`, insert the slide's
    audio clip (the real TTS clip if `audio_paths[i]` is set, otherwise a
    generated 1-second silent clip) as a slide media element, configure
    it to autoplay on slide entry, and hide its icon/placeholder.
  - Before inserting, remove any audio media element already present on
    that slide (from a prior run of this step) so re-running is safe and
    never produces duplicate audio on one slide.
  - Save the result to a new local `.pptx` path (mirroring the
    `_with_audio.pptx` naming the stub already uses) rather than
    overwriting the source deck in place, so the original downloaded
    `.pptx` stays untouched.
  - Output records, per slide, whether real narration or the silent
    placeholder was embedded (e.g. a parallel `slides_embedded: list[bool]`
    — reusing/adapting the stub's existing field — plus enough
    information for tests/UI to distinguish real vs. placeholder audio;
    exact field shape is an implementation detail for Plan.md).
  - Keep the same `StepState`/`StepStatus`/`asyncio.Event` approval-gate
    shape as every other step — this phase only changes what happens
    *inside* `run_embed`.
- Update `src/videogen/pipeline/runner.py`'s call site: `embed` now takes
  `tts_output.audio_paths` instead of `audio_upload_output.drive_file_ids`.
  `audio_upload` still runs before `embed` in the pipeline order (per
  `specs/roadmap.md`'s step ordering) but its (still-mock) output is no
  longer threaded into `embed`.
- Update `src/videogen/pipeline/ui.py`'s demo/manual-run wiring if it
  hardcodes any embed-step input shape that no longer matches.
- Generate the 1-second silent audio clip via `ffmpeg` (already a project
  dependency per `specs/tech-stack.md`), consistent with how the project
  already shells out to `ffmpeg`/`ffprobe` in `tts.py`.
- Tests: real embedding produces a `.pptx` where every slide has exactly
  one autoplay audio element (real clip or silent placeholder as
  appropriate); re-running the step on an already-embedded deck replaces
  rather than duplicates; the step's approval gate still works exactly as
  before.

## Explicitly out of scope

- Real Google Drive upload of the updated `.pptx` — still Phase 9, per
  `specs/roadmap.md`.
- Any change to steps other than `embed` (and the minimal wiring changes
  in `runner.py`/`ui.py` needed to pass local audio paths through instead
  of Drive IDs) — `download`, `notes_extraction`, `tts`, `audio_upload`,
  `render`, `video_upload` are untouched beyond that wiring.
- Slide transition animations/effects (per `specs/mission.md`'s stated
  non-goals).
- Any product decision about *whether* a no-notes slide should have
  narration at all — that was decided in Phase 6/7 (`has_notes=False`
  means no TTS call); this phase only decides what audio element (if any
  minimal placeholder) is embedded on the resulting slide so every slide
  is uniform for later phases.
- Multiple voices/per-speaker audio — out of scope per `specs/mission.md`.

## Constraints (from specs/tech-stack.md)

- `python-pptx` for embedding generated audio (set to autoplay), per
  tech-stack.md's stated approach.
- The step still follows the same `StepState`/`StepStatus`/
  `asyncio.Event` approval-gate shape as every other step.
- pytest + pytest-asyncio, testable with a real sample `.pptx` and no
  network access required (per mission.md's "every step stands alone,
  testable in isolation") — the silent-clip generation via `ffmpeg` is
  local-only and needs no network access either.

## Technical recommendations (not hard requirements — flagged for review)

- 1-second duration for the silent placeholder clip. Confirmed as the
  starting value; can be revisited if Phase 10's end-to-end validation
  shows it needs to differ.
- Silent clip generated once per pipeline run (not once per no-notes
  slide) and reused across all no-notes slides in that run, to avoid
  redundant `ffmpeg` invocations. Implementation detail, not a product
  requirement.

## Open questions

None outstanding — scope was confirmed with the human before writing this
implementation plan (see "User-provided requirements" above).
