# Requirements — Local PPTX → Slide Images (Phase 4)

## Context

Phases 0-3 are done and merged: scaffold, all 7 mocked pipeline steps
(including a stub `download` step), and the approval-gate UI. This phase
replaces the mock `download` step with the first real (non-stub) logic in
the pipeline: converting an actual `.pptx` file into slide-image PNGs via
LibreOffice, per specs/roadmap.md Phase 4 and specs/mission.md's
"prove the shape before the substance" principle — the mock pipeline
already proved the shape (Phases 0-3); this is the first substance swap.

## Scope decisions (confirmed with user)

- **Input:** a local filesystem path to an already-present `.pptx` file,
  not a Google Drive link. Real Google Drive auth/download is explicitly
  deferred, not built in this phase — this is a deliberate deviation from
  the roadmap's original Phase 4 wording (updated in `specs/roadmap.md`
  to match).
- **Conversion:** real LibreOffice-headless (`soffice --headless
  --convert-to`) conversion of the local `.pptx` to slide images. Not a
  stub — this must actually invoke LibreOffice and produce real PNGs from
  a real deck.
- **Image format/resolution:** PNG, 1920x1080.
- **Storage:** a fresh per-run temporary directory (not one fixed shared
  path, not the deck's own folder) — keeps concurrent/repeated runs
  isolated, matches `tempfile`-style working-directory conventions.

## In scope

- Replace `src/videogen/pipeline/download.py`'s stub body with real logic:
  - Take a local `.pptx` path as input (`DownloadInput.local_pptx_path`
    replaces the old `DownloadInput.drive_link` field — the input shape
    changes to match the new local-file reality).
  - Create a fresh per-run temp directory (e.g. via `tempfile.mkdtemp()`),
    copy or reference the source `.pptx` there for a consistent working
    area.
  - Invoke LibreOffice headless to convert the `.pptx` to one PNG per
    slide at 1920x1080, in slide order.
  - Return `DownloadOutput` with the real slide image paths and slide
    count (same output shape as before — downstream steps 2-7 don't
    change).
- Update `src/videogen/pipeline/ui.py`'s `_download_input()` (the Phase 3
  UI's hardcoded demo input) to pass a real sample `.pptx` path instead of
  a fake Drive link string, so the UI's `download` step actually exercises
  the new real logic.
- Update `src/videogen/pipeline/runner.py`'s `run_pipeline(drive_link:
  str)` signature/call site to match the new `DownloadInput` shape (a
  local path, not a Drive link) — parameter renamed accordingly.
- A small real sample `.pptx` fixture file (a handful of slides) checked
  into the repo (e.g. `tests/fixtures/sample_deck.pptx`) for tests and
  manual verification to point at.
- Tests: real conversion produces the correct image count in the correct
  order, at 1920x1080; the step's approval gate (block/resume via
  `asyncio.Event`) still works exactly as before; the per-run temp
  directory is actually created and used.

## Out of scope

- Real Google Drive auth, file download, or any Drive API calls —
  deferred to a later phase (not renumbered here; this phase is
  local-file-only per the scope decision above).
- Any change to steps 2-7 (`notes_extraction` through `video_upload`) —
  their fake logic is untouched; only `download`'s internals change.
- Cleanup/garbage-collection of per-run temp directories after a run
  completes — out of scope for this phase, temp dirs are left in place
  (standard OS temp-dir lifecycle applies).

## Constraints (from specs/tech-stack.md)

- LibreOffice headless invoked as a subprocess (`soffice --headless
  --convert-to`), per tech-stack.md's stated approach.
- The step still follows the same `StepState`/`StepStatus`/
  `asyncio.Event` approval-gate shape as every other step — this phase
  only changes what happens *inside* `run_download`, not the interface
  Phase 3's UI and the other steps depend on.
- pytest + pytest-asyncio, testable with a real sample `.pptx` and no
  network access required (per mission.md's "every step stands alone,
  testable in isolation").
