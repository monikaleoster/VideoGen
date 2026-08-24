# Requirements — Notes Extraction: Per-Slide Text Files + UI Links

## Context

`notes_extraction` (Phase 6, real) currently extracts each slide's
speaker notes purely in memory (`NotesExtractionOutput.notes: list[str]`)
and never writes anything to disk. The approval-gate UI only shows the
raw JSON output blob (the generic `<pre data-role="output">` block). The
human wants each slide's notes saved as its own text file, and a link to
that file exposed in the UI — mirroring the existing pattern for `tts`'s
per-slide audio (`FileResponse` route + `<audio>`/link element per slide
row).

## User-provided requirements (confirmed 2026-08-23, via AskUserQuestion)

- **One `.txt` file per slide, always** — including slides with
  `has_notes=False` (empty notes get an empty file, not a skipped one).
  This keeps the per-slide file/link pattern uniform, same reasoning as
  `tts`'s "every slide gets a result, some just have `None` audio."
- **Where the files live:** a work directory created by the
  `notes_extraction` step itself, the same way `download` and `tts`
  already create their own scratch directories. If
  `specs/2026-08-23-download-input-config/` (the shared-tmp-root work)
  has already landed on this branch, use its `workdir.make_work_dir(...)`
  helper so these files nest under the same shared root as everything
  else; otherwise create an independent `tempfile.mkdtemp(prefix=
  "videogen_notes_")` directory, matching the pattern every other step
  uses today.
- **UI:** add a link per slide (not just the file's existence) so a
  human can open/download the raw notes text directly from the browser,
  the same way each `tts` slide row exposes its audio player.

## In scope

- `notes_extraction.py`:
  - After extracting `notes`/`has_notes` (unchanged logic), write each
    slide's already-stripped notes text to its own file, e.g.
    `slide_{i:02d}_notes.txt`, in the step's work directory — including
    an empty file for slides with `has_notes=False`.
  - Add `notes_file_paths: list[str]` to `NotesExtractionOutput`,
    parallel to `notes`/`has_notes`, one path per slide (never `None` —
    every slide gets a file per the confirmed decision).
- `routes.py`: new route
  `GET /pipeline/notes_extraction/slide/{index}/notes` serving the
  slide's `.txt` file via `FileResponse(..., media_type="text/plain")`,
  mirroring `get_tts_slide_audio`'s shape (404 if no output yet, 404 if
  `index` out of range).
- `templates/index.html`: under the `notes_extraction` step's card, add
  a small per-slide list (one row per slide) with a link to
  `/pipeline/notes_extraction/slide/{i}/notes`, labeled with the slide
  number and a "(no notes)" marker when `has_notes[i]` is false — same
  rebuild-only-when-slide-count-changes approach `renderTtsSlides` uses,
  but simpler (no text input, no Generate button — just a link, since
  this phase doesn't add per-slide notes editing).

## Out of scope

- Editing notes text through the UI (that's a `tts`-side per-slide
  override already, via the existing text input on the `tts` card — this
  phase only adds a way to *view/download* the raw extracted text, not
  edit it in place).
- Combining all slides' notes into one manifest file — explicitly
  rejected in favor of one file per slide.
- Any change to the extraction logic itself (whitespace-stripping rules,
  empty-notes flagging) — unchanged from Phase 6.

## Validation bar

- Running `notes_extraction` against the real fixture deck produces one
  `.txt` file per slide on disk, byte-for-byte matching that slide's
  `notes[i]` value (including an empty file for the no-notes slide).
- Each file is reachable and correctly served (`text/plain`, correct
  content) via the new route, at both `waiting_approval` and `done`
  status.
- The UI shows a working link for every slide once `notes_extraction`
  has run, before the step is approved.
- Existing `notes_extraction` tests (extraction correctness, empty-notes
  flagging, approval gate) continue to pass unmodified aside from the
  new `notes_file_paths` field appearing in the output.
