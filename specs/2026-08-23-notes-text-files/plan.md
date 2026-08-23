# Plan — Notes Extraction: Per-Slide Text Files + UI Links

Numbered task groups. Complete and validate each group before moving on.

## 1. Write per-slide `.txt` files
- Objective: `notes_extraction` produces real files on disk alongside its
  existing in-memory output.
- Tasks:
  1.1. Check whether `specs/2026-08-23-download-input-config/`'s
       `src/videogen/pipeline/workdir.py` helper already exists on this
       branch. If yes, create the work dir via
       `workdir.make_work_dir("videogen_notes_")`; if not, use
       `Path(tempfile.mkdtemp(prefix="videogen_notes_"))` directly
       (matching `download.py`'s pre-shared-root pattern) — do not block
       this phase on the other one landing first.
  1.2. In `_extract_notes` (or a small wrapper around it), after
       computing each slide's stripped `notes` text, write it to
       `work_dir / f"slide_{i:02d}_notes.txt"` (UTF-8, no trailing
       newline added beyond what's already in the stripped text) for
       every slide, including empty-notes ones (empty file).
  1.3. Add `notes_file_paths: list[str]` to `NotesExtractionOutput` and
       populate it in `run_notes_extraction`.
- Dependencies: none (soft dependency on the workdir helper's presence,
  handled by the branch above rather than a hard blocking dependency).
- Files affected: `src/videogen/pipeline/notes_extraction.py`.
- Validation: unit tests in group 3.
- Independent: yes.

## 2. Serve the files
- Tasks:
  2.1. `routes.py`: add
       `GET /pipeline/notes_extraction/slide/{index}/notes` returning
       `FileResponse(path, media_type="text/plain")`, following
       `get_tts_slide_audio`'s exact error shape: 404 if
       `notes_extraction.state.output is None` or `index` out of range,
       404 if the file is somehow missing on disk.
- Dependencies: group 1 (needs `notes_file_paths` to exist).
- Files affected: `src/videogen/pipeline/routes.py`.
- Validation: route test in group 3.
- Independent: no.

## 3. Tests
- Tasks:
  3.1. `tests/test_notes_extraction.py`: extend existing extraction tests
       to assert `notes_file_paths` has one entry per slide, each file
       exists, and each file's content exactly matches `notes[i]`
       (including the empty-notes slide's empty file).
  3.2. `tests/test_pipeline_ui.py` or a new route test: the new
       `GET /pipeline/notes_extraction/slide/{index}/notes` route returns
       200 with correct `text/plain` content for a valid index post-run,
       404 before any run and for an out-of-range index.
  3.3. Full `uv run pytest`, confirm no regressions.
- Dependencies: groups 1-2.
- Files affected: `tests/test_notes_extraction.py`,
  `tests/test_pipeline_ui.py` (or new test file).
- Independent: no.

## 4. UI links
- Tasks:
  4.1. `templates/index.html`: add a `data-role="notes-slides"` container
       under the `notes_extraction` step's card (guarded by
       `{% if step.name == "notes_extraction" %}`, same pattern as
       `tts`'s `data-role="tts-slides"`).
  4.2. JS: a `renderNotesSlides(row, notesStep)` function, called from
       the main `render(snapshot)` loop when `name === "notes_extraction"`
       (mirroring the existing `if (name === "tts")` branch), rebuilding
       rows only when slide count changes (same guard `renderTtsSlides`
       uses): one row per slide with "Slide N" label, "(no notes)" suffix
       when `has_notes[i]` is false, and an `<a>` linking to
       `/pipeline/notes_extraction/slide/{i}/notes` (target `_blank`, no
       fetch needed — a plain anchor).
- Dependencies: groups 1-2 (needs real data/route to link against).
- Files affected: `templates/index.html`.
- Validation: manual browser check in group 5; any existing
  `test_pipeline_ui.py` template-rendering assertions still pass.
- Independent: no.

## 5. Validation pass
- Tasks:
  5.1. Run `notes_extraction` against the real fixture deck, manually
       open each slide's link, confirm content matches by eye.
  5.2. Fill in `specs/2026-08-23-notes-text-files/validation.md`.
- Dependencies: groups 1-4.
- Files affected: `specs/2026-08-23-notes-text-files/validation.md`.
- Independent: no — final step.

## Delegable task groups

Group 1 is fully independent and can start immediately. Group 2 depends
on group 1's output shape. Group 4 (UI) can be drafted in parallel with
group 2 once group 1's field name (`notes_file_paths`) is settled, since
the UI only needs to know the URL pattern, not the route's
implementation. Group 3 (tests) needs groups 1-2 done first. Group 5 is
final.
