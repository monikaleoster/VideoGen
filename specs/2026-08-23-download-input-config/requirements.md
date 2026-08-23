# Requirements — Download Step: Configurable PPTX Path & Shared Tmp Root

## Context

Today the `download` step's input is entirely hardcoded: `routes.py` and
`__main__.py` both point at the checked-in
`tests/fixtures/sample_deck.pptx`, and every step that needs scratch space
(`download`, `tts`, and — once
`specs/2026-08-23-notes-text-files/` lands — `notes_extraction`, plus
`embed`/`render`) calls `tempfile.mkdtemp(prefix=...)` independently,
scattering each run's working files across the OS temp directory with no
shared root and no way to point them somewhere the human chooses (e.g. a
non-ephemeral disk, or a location they want to inspect/clean up by hand).

This phase makes both the PPTX source path and a shared tmp root
user-supplied, entered through the approval-gate UI, per the confirmed
decisions below.

## User-provided requirements (confirmed 2026-08-23, via AskUserQuestion)

- **Where the inputs live:** two new text fields on the `download` step's
  card in the approval-gate UI (`templates/index.html`), matching the
  existing pattern used for `tts`'s API key / voice ID fields — read live
  from the DOM at Run time, sent in the POST body, never persisted
  server-side beyond the in-flight run.
  - Field 1: PPT file path (local filesystem path to a `.pptx`).
  - Field 2: tmp folder (local filesystem path to use as the shared
    scratch root for this run).
- **Tmp folder scope:** a *shared root for all steps*, not just
  `download`. Every step that currently calls `tempfile.mkdtemp()`
  directly (`download`, `tts`, and `notes_extraction`'s new per-slide
  `.txt` files once that phase lands, plus `embed`/`render` if they also
  create work dirs) creates its work directory nested under this root
  instead of the bare OS temp directory.
- **Fallback:** if either field is left blank, behavior is unchanged from
  today — PPT path falls back to the checked-in demo fixture
  (`tests/fixtures/sample_deck.pptx`), tmp root falls back to the OS
  default temp directory (`tempfile.gettempdir()`), i.e. plain
  `tempfile.mkdtemp(prefix=...)` with no `dir=` override.
- **CLI demo entry point (`__main__.py`):** unaffected. It keeps using
  the hardcoded demo fixture path and the OS default temp dir — the UI
  fields are the only new input surface (confirmed: "UI fields, per run",
  not "both UI and env vars").

## In scope

- A small shared helper (e.g. `src/videogen/pipeline/workdir.py`)
  exposing:
  - `set_tmp_root(path: str | None) -> None` — records the current run's
    shared root (or clears it back to "use OS default").
  - `make_work_dir(prefix: str) -> Path` — creates and returns a fresh
    work directory: nested under the current root (via
    `tempfile.mkdtemp(prefix=prefix, dir=str(root))`, creating `root`
    first if needed) when a root is set, otherwise today's behavior
    (`tempfile.mkdtemp(prefix=prefix)`, OS default location).
- `download.py`: accept an optional PPTX path and optional tmp root as
  real step input (not hardcoded), route the tmp root through
  `workdir.set_tmp_root(...)` before creating its own work dir via
  `workdir.make_work_dir(...)` instead of a direct `tempfile.mkdtemp()`
  call.
- `routes.py`'s `_download_input`: read `local_pptx_path` and `tmp_root`
  from the request body; fall back to the existing hardcoded demo path /
  `None` (OS default) respectively when absent or blank.
- `templates/index.html`: add the two text inputs to the `download`
  step's card; JS reads their live values at Run time and includes them
  in the POST body (mirroring `ttsCredentials`).
- Every other step that currently calls `tempfile.mkdtemp()` directly
  (`tts.py`'s `run_tts`/`regenerate_slide` work dir, `embed.py`,
  `render.py` if applicable) switches to `workdir.make_work_dir(...)` so
  they land under the same shared root once one is set for the run.
  `notes_extraction.py` does not need updating here unless
  `specs/2026-08-23-notes-text-files/` has already landed on this
  branch — if it has, wire its new per-slide `.txt` work dir through the
  same helper too.

## Out of scope

- Real Google Drive auth/download — still deferred (per Phase 4's
  original deviation).
- The CLI demo entry point (`__main__.py`) gaining its own path/tmp-root
  input (env vars or flags) — explicitly not requested.
- Per-step individual tmp-root overrides — this phase is one shared root
  for the whole run, not per-step configuration.
- Validating the *contents* of the user-supplied PPTX path (e.g. "is this
  really a `.pptx`") beyond what already happens today (LibreOffice/
  `python-pptx` erroring out naturally on a bad file) — no new
  file-type/extension validation is added.

## Validation bar

- Running `download` with both fields blank behaves exactly as today
  (demo fixture, OS temp dir) — no regression.
- Running `download` with a custom PPTX path converts that real file
  (not the demo fixture).
- Running `download` with a custom tmp folder places the copied `.pptx`
  and slide-image PNGs under `<tmp_root>/videogen_download_*/`, not the
  OS default temp dir.
- With a tmp root set for the run, subsequent steps that create work dirs
  (`tts`, `embed`, `render`, and `notes_extraction`'s `.txt` files if
  that phase has landed) also nest under the same `<tmp_root>`, verified
  by inspecting the created paths.
- Existing tests for `download`, `tts`, `embed`, `render` continue to
  pass unmodified in the no-root-set (default) case.
