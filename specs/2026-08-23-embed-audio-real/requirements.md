# Requirements — Embed Audio into PPTX (Real) (Phase 8)

## Context

Phases 0-7 are done and merged: scaffold, all 7 mocked pipeline steps,
the approval-gate UI, real `download`, real `notes_extraction`, and real
`tts` (ElevenLabs). This phase replaces the mock `embed` step with real
`python-pptx`-based logic: insert each slide's generated audio clip into
the deck and make it play automatically when the slide is shown, per
`specs/roadmap.md` Phase 8.

## User-provided requirements (confirmed 2026-08-23)

- **Playback trigger:** audio starts automatically as soon as the slide
  is shown — no click required. This is PowerPoint's "Start: Automatically"
  / "With Previous" timing, not the default "On Click" behavior a naive
  media-insert produces (see Technical constraint below).
- **Slides with no audio:** a slide whose `tts` output entry is `None`
  (no notes, per Phase 6/7) is left completely untouched — no audio
  shape inserted, no autoplay timing added, slide otherwise unchanged.
- **Output file:** `embed` writes a **new** `.pptx` file — it does not
  modify the original in place. Naming/location: `<original_name>
  _with_audio.pptx` in the same per-run temp directory `download` and
  `tts` already use (`tempfile`-based, matching their precedent).
- **Failure handling:** consistent with Phase 7's confirmed pattern — no
  automatic retry. A failure partway through (e.g. a slide's audio path
  points at a missing/corrupt file, or a `python-pptx` error) propagates
  and fails the step visibly; the human re-runs manually via the existing
  Reject/Run action. No partial-embed fallback logic.
- **Validation method:** automated — an XML/structure check (via
  `python-pptx`'s XML access, e.g. `slide.part._element` /
  `lxml` inspection) confirming, for every slide with audio: the audio
  media relationship exists, and the slide's timing tree has an autoplay
  trigger (not an on-click-only trigger) referencing that media shape. No
  separate manual PowerPoint/LibreOffice inspection required for this
  phase's sign-off — deviates from the roadmap's original "open the
  resulting `.pptx`" wording, which implied manual-only.

## Technical constraint discovered during spec research (not a product
## decision — documented so the deviation from a naive implementation is
## understood)

`python-pptx` has no dedicated `add_audio` method — only
`shapes.add_movie(file, left, top, width, height, poster_frame_image,
mime_type)`, which works for audio too (with `mime_type="audio/mpeg"`),
but:
- It requires an explicit position/size and poster-frame image (no
  auto-sizing).
- Its built-in timing helper (`_add_video_timing`) only adds click-to-play
  controls to the slide's `p:timing` tree — it does **not** produce
  autoplay-on-entry. Real "starts automatically when the slide is shown"
  requires directly constructing/editing the slide's `<p:timing>` XML
  subtree (via `lxml`, since `python-pptx` doesn't expose this) so the
  media node's trigger condition is `onBegin`/"with previous" rather than
  `onClick`. This is a known, somewhat manual OOXML-level workaround (not
  unique to this project) — flagged here as a technical recommendation
  for the plan, not a product requirement change.

## In scope

- Replace `src/videogen/pipeline/embed.py`'s stub body with real logic:
  - For each slide with a non-`None` audio path: open the target `.pptx`
    (the original, unmodified, from `download`'s output), insert the
    slide's MP3 as a media shape (e.g. via `add_movie` with
    `mime_type="audio/mpeg"` and a minimal/invisible poster image, or an
    equivalent lower-level insertion if `add_movie`'s constraints prove
    awkward — implementation detail, not a requirement), and set that
    media's timing trigger to autoplay-on-entry (not on-click).
  - Slides with a `None` audio path are left untouched.
  - Save the result as a new file (not overwriting the source), following
    the naming/location convention above.
  - On any error (missing/corrupt audio file, `python-pptx`/XML error),
    let the exception propagate — the step fails visibly, no retry, no
    partial output.
  - Keep the same `StepState`/`StepStatus`/`asyncio.Event` approval-gate
    shape as every other step.
- **Wiring correction (technical necessity, not a product decision):**
  `EmbedInput` currently carries `drive_file_ids: list[str]` — fake IDs
  from the still-mocked `audio_upload` step, which carries no real local
  file paths through its output. Real embedding needs the actual local
  MP3 paths, which only exist on `tts`'s output. `EmbedInput.drive_file_ids`
  is replaced with `audio_paths: list[str | None]`, sourced directly from
  `tts`'s output; `runner.py` and `ui.py`'s wiring are updated so `embed`
  receives `tts`'s output rather than `audio_upload`'s. `audio_upload`
  itself is untouched (still a stub, unaffected by this rewiring — it
  keeps running and gating in the pipeline as before, just no longer on
  `embed`'s critical input path).
- Tests: real embedding, with a mocked/small silent MP3 fixture, produces
  a new `.pptx` where every slide with audio has a real audio media
  relationship and an autoplay (not on-click) timing trigger, verified by
  XML inspection; a slide with no audio is unchanged; a missing/corrupt
  audio file causes the step to fail without producing a partial output;
  the approval gate still works.

## Explicitly out of scope

- Manual PowerPoint/LibreOffice playback verification for this phase's
  automated sign-off (the human may still do this separately if desired,
  but it is not required to consider the automated validation complete).
- Any change to `audio_upload`, `render`, or `video_upload` beyond the
  `embed`-input-source rewiring above.
- Real Google Drive integration (`audio_upload`'s real Drive uploads are
  Phase 9's concern, still deferred).
- Any visual/audible poster-frame design for the inserted media shape
  beyond whatever minimal placeholder makes `add_movie` (or its
  equivalent) work — this is a narration track, not a video, so its
  on-slide visual representation is not a design concern for this phase.

## Constraints (from specs/tech-stack.md)

- `python-pptx` for embedding generated audio (set to autoplay) back into
  the deck, per tech-stack.md's stated approach.
- The step still follows the same `StepState`/`StepStatus`/
  `asyncio.Event` approval-gate shape as every other step.
- pytest + pytest-asyncio, testable with a real (silent) MP3 fixture and
  no network access required.

## Open questions

None outstanding — scope was confirmed with the human before writing this
implementation plan (see "User-provided requirements" above). The exact
low-level XML approach for the autoplay timing trigger is left as an
implementation detail to be worked out during Phase 5 of this spec's
Plan.md, not a product-requirements question.
