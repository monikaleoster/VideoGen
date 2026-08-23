# Mission

## What this is

VideoGen turns a Google Drive slide deck into a fully narrated MP4 video,
automatically — but never unattended. It takes each slide's speaker notes,
generates narration audio for them, embeds that audio back into the deck,
and renders one final video, pausing for a human to approve the result of
every major step before moving to the next.

## Why it exists

Turning a deck into a narrated video today means manually exporting notes,
recording or generating audio per slide, syncing it to the right slide, and
stitching everything into a video. It's slow and easy to get subtly wrong.
VideoGen automates the whole chain end-to-end, while keeping a human in the
loop at each stage — because TTS and rendered video quality can vary, and
that variance shouldn't ship without a person looking at it first.

## Who it's for

Anyone who already has a slide deck with speaker notes in Google Drive and
wants a narrated video out the other end, without manually producing and
syncing audio themselves.

## Core principles

- **Human approval is the trust boundary.** No step auto-advances. Every
  step produces a visible result (a count, a duration, a sample) that a
  person explicitly approves or rejects before the pipeline continues.
- **Google Drive is the source of truth.** Inputs are read from Drive and
  every artifact the pipeline produces (audio clips, updated deck, final
  video) is written back to Drive, in the same folder as the source.
- **Every step stands alone.** Each of the seven pipeline steps (download,
  notes extraction, TTS, audio upload, embed, render, video upload) must be
  independently runnable, testable, and replaceable — a step is a unit,
  not a stage that only makes sense inside the full run.
- **Prove the shape before the substance.** Build and validate the full
  orchestration and approval-gate flow with mocked steps first, then
  replace mocks with real implementations one at a time. Integration risk
  is de-risked early, not discovered last.

## Out of scope for now

These are deliberate non-goals, not oversights — revisit them only if the
mission above stops being served without them:

- Multiple voices or per-speaker voice switching (single voice for v1).
- Slide transition animations or effects in the rendered video.
- Automatic retry/regeneration of a rejected TTS clip (manual re-run only).
- Live PowerPoint recording — video is assembled from static slide images
  plus audio, not a screen capture.

## What success looks like

- A real deck run end-to-end produces a final MP4 where every slide's
  audio matches its notes and its visible on-screen duration.
- No step ever proceeds without an explicit human approval.
- Every step can be run and validated on its own, with sample inputs,
  independent of the rest of the pipeline.
