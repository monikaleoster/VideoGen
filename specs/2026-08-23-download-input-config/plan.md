# Plan — Download Step: Configurable PPTX Path & Shared Tmp Root

Numbered task groups. Complete and validate each group before moving on.

## 1. Shared work-dir helper
- Objective: one place that decides "where does a step's scratch
  directory live" so every step can be switched over without duplicating
  the root/no-root branching logic.
- Tasks:
  1.1. Create `src/videogen/pipeline/workdir.py` with a module-level
       `_tmp_root: Path | None = None`, `set_tmp_root(path: str | None) ->
       None` (parses/normalizes, or clears when `path` is falsy), and
       `make_work_dir(prefix: str) -> Path` (creates `_tmp_root` with
       `mkdir(parents=True, exist_ok=True)` if set, then
       `tempfile.mkdtemp(prefix=prefix, dir=str(_tmp_root) if _tmp_root
       else None)`).
  1.2. Unit tests (`tests/test_workdir.py`): no root set -> behaves like
       bare `tempfile.mkdtemp`; root set -> created dir is nested under
       it; root cleared after being set -> reverts to OS default.
- Dependencies: none.
- Files affected: `src/videogen/pipeline/workdir.py` (new),
  `tests/test_workdir.py` (new).
- Independent: yes.

## 2. Wire `download.py` to real input + the shared helper
- Tasks:
  2.1. `DownloadInput` gains nothing new structurally (already carries
       `local_pptx_path`) — confirm the value passed in by `routes.py`
       is the user-supplied one, not a hardcoded default (default lives
       in `routes.py`, not the step module, per existing convention).
  2.2. Add an optional `tmp_root: str | None` to `DownloadInput`.
  2.3. In `run_download`: call `workdir.set_tmp_root(step_input.tmp_root)`
       before creating the work dir; replace the direct
       `Path(tempfile.mkdtemp(prefix="videogen_download_"))` call with
       `workdir.make_work_dir("videogen_download_")`.
- Dependencies: group 1.
- Files affected: `src/videogen/pipeline/download.py`.
- Validation: `tests/test_download.py` — existing tests pass with
  `tmp_root=None`; a new test asserts the work dir lands under a
  provided `tmp_root`.
- Independent: no — needs group 1.

## 3. Route/UI wiring
- Tasks:
  3.1. `routes.py`'s `_download_input`: read `local_pptx_path` and
       `tmp_root` from `request_data`, falling back to
       `str(_DEMO_PPTX_PATH)` and `None` respectively when missing or
       blank/whitespace-only.
  3.2. `templates/index.html`: add a `data-role="download-inputs"` block
       to the `download` step's card (only rendered for that step, same
       `{% if step.name == "download" %}` pattern as `tts`'s
       credentials block) with two text inputs:
       `data-role="pptx-path"` and `data-role="tmp-root"`.
  3.3. JS: extend `postAction` (or add a `downloadInputs(row)` helper
       analogous to `ttsCredentials`) so the `download` step's Run
       request body includes `{ local_pptx_path, tmp_root }` read live
       from those two inputs.
- Dependencies: group 2.
- Files affected: `src/videogen/pipeline/routes.py`,
  `templates/index.html`.
- Validation: `tests/test_pipeline_ui.py` — a Run request with custom
  values reaches `download.run_download` with them; a Run request with
  blank/absent values falls back to the demo path / `None`.
- Independent: no — needs group 2's `DownloadInput.tmp_root` field.

## 4. Extend the shared root to other steps
- Tasks:
  4.1. `tts.py`: replace `Path(tempfile.mkdtemp(prefix="videogen_tts_"))`
       (both call sites — `run_tts`'s work dir and `regenerate_slide`'s
       fallback when `_current_work_dir is None`) with
       `workdir.make_work_dir("videogen_tts_")`.
  4.2. `embed.py` / `render.py`: check each for a direct
       `tempfile.mkdtemp()` call and switch it to `workdir.make_work_dir`
       the same way, if present.
  4.3. If `specs/2026-08-23-notes-text-files/` has already landed on this
       branch (check `src/videogen/pipeline/notes_extraction.py` for a
       work-dir call before starting this task), wire its `.txt`-file
       work dir through the same helper too; otherwise skip — that
       phase's own plan will pick this up when it's implemented after
       this one.
- Dependencies: group 1 (helper must exist); otherwise independent of
  groups 2-3 (touches different files) but should land after them so a
  single PR demonstrates the shared root working end-to-end.
- Files affected: `src/videogen/pipeline/tts.py`,
  `src/videogen/pipeline/embed.py`, `src/videogen/pipeline/render.py`,
  possibly `src/videogen/pipeline/notes_extraction.py`.
- Validation: existing test suites for each of these steps still pass
  unmodified with no root set; one new test per touched step confirms
  its work dir nests under a root when one is set for the run (reuse the
  same `workdir.set_tmp_root` call a test can make directly, no need to
  drive it through the full HTTP flow for every step).

## 5. End-to-end + regression tests
- Tasks:
  5.1. A UI-level test: submit `download` Run with a real custom
       `local_pptx_path` + `tmp_root`, then continue through
       `notes_extraction`/`tts`/etc. and confirm every subsequent
       created work dir is nested under the same `tmp_root`.
  5.2. Full `uv run pytest` run, confirm no regressions anywhere.
- Dependencies: groups 1-4.
- Files affected: `tests/test_pipeline_ui.py` or a new
  `tests/test_shared_tmp_root.py`.
- Independent: no — final integration check.

## 6. Validation pass
- Tasks:
  6.1. Manual run through the browser UI: blank fields (regression
       check), then custom PPTX path + custom tmp folder, inspecting the
       resulting directory tree by hand.
  6.2. Fill in `specs/2026-08-23-download-input-config/validation.md`.
- Dependencies: groups 1-5.
- Files affected: `specs/2026-08-23-download-input-config/validation.md`.
- Independent: no — final step.

## Delegable task groups

Group 1 (the helper + its unit tests) is fully independent and can be
delegated/started first. Groups 2-3 depend on it and on each other in
sequence. Group 4's per-step edits (4.1 `tts.py`, 4.2 `embed.py`/
`render.py`) are independent *of each other* once group 1 exists, so
they can be split across agents, but all of group 4 should land only
after groups 2-3 are merged to avoid conflicting `workdir.py` API
assumptions. Group 5-6 are sequential final steps.
