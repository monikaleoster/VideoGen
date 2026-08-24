# Validation — Download Step: Configurable PPTX Path & Shared Tmp Root

This file is filled in during/after implementation (Plan.md task group 6).
Template below defines what "done" means.

## Automated validation

- [ ] `uv run pytest` passes in full, no regressions.
- [ ] `tests/test_workdir.py`: helper behaves correctly with and without
      a root set, and after a root is cleared.
- [ ] `tests/test_download.py`: existing tests unaffected with no
      `tmp_root`; new test confirms work dir nests under a provided one.
- [ ] `tests/test_pipeline_ui.py`: Run request with custom
      `local_pptx_path`/`tmp_root` reaches `download.run_download`
      correctly; blank/absent values fall back to current defaults.
- [ ] Steps touched in plan.md group 4 (`tts`, `embed`, `render`, and
      `notes_extraction` if applicable) each have a passing test showing
      their work dir nests under a shared root when one is set.

## Regression validation

- [ ] Full pipeline (`download` -> ... -> `video_upload`) still completes
      with all fields left blank, identical to pre-change behavior.

## Build / lint / static analysis

- [ ] `uv run pytest` (this repo's build/test gate).

## Manual verification

Performed by: _(fill in)_

1. Blank PPT path / tmp folder fields: Run behaves exactly as before
   (demo fixture, OS temp dir).
2. Custom PPT path: a real, non-fixture `.pptx` is converted correctly.
3. Custom tmp folder: inspect the resulting directory tree by hand,
   confirm `download`'s copied `.pptx` and slide PNGs, plus every
   downstream step's work dir, live under the provided root.

## Expected result

- The two new UI fields work end-to-end; leaving them blank is a no-op
  relative to today's hardcoded behavior.
- Every step's scratch files land under one shared, human-chosen root
  when provided.

## Failure conditions

- A blank field changes behavior from today's baseline.
- Any step's work dir silently stays outside the shared root when one is
  set.
- Any existing test regresses.

## Evidence the human should provide

- Confirmation of the manual verification steps above.
- `APPROVED` or `CHANGES REQUIRED` before this phase's implementation PR
  is merged.

## Result

_(fill in after implementation)_

## Roadmap update

_(this is a UX/infrastructure improvement layered on the already-✅
Phase 4, not a new roadmap phase — note completion here rather than
adding a new roadmap entry, unless the human prefers otherwise.)_
