# Plan — Local PPTX → Slide Images (Phase 4)

Numbered task groups. Complete and validate each group before moving on.

## 1. Sample deck fixture
1.1. Create `tests/fixtures/sample_deck.pptx` — a small (3-slide) real
     `.pptx` for tests and manual verification to point at.

## 2. Real `download` step
2.1. Replace `DownloadInput`'s `drive_link: str` field with
     `local_pptx_path: str`.
2.2. In `run_download`: create a fresh per-run temp directory
     (`tempfile.mkdtemp`), copy the source `.pptx` into it.
2.3. Convert to PDF via a real LibreOffice-headless subprocess call
     (`soffice --headless --convert-to pdf`), using a fresh
     `-env:UserInstallation` profile dir per call to avoid profile-lock
     conflicts between concurrent/successive runs.
2.4. Convert the PDF to one 1920x1080 PNG per slide via `pdftoppm -png
     -scale-to-x 1920 -scale-to-y 1080`, then rename the tool's own
     `slide-N.png` output to our `slide_XX.png` convention.
2.5. Run both subprocess calls off the event loop thread
     (`asyncio.to_thread`) so the WebSocket status push keeps working
     live during the (real, non-trivial) conversion time.
2.6. Keep the same `StepState`/`StepStatus`/`asyncio.Event` approval-gate
     shape as every other step — only the internals of `run_download`
     change.

## 3. Wire the new input shape through
3.1. Update `runner.run_pipeline`'s parameter from `drive_link: str` to
     `local_pptx_path: str`, and its call to `download.run_download`.
3.2. Update `ui.py`'s `_download_input()` to point at the checked-in
     sample deck fixture instead of a fake Drive-link string.

## 4. CI environment
4.1. Add a step to `.github/workflows/test.yml` installing
     `libreoffice-impress` and `poppler-utils` via `apt-get` before
     running tests — `ubuntu-latest` runners don't have these by default,
     and `run_download` now genuinely needs both.

## 5. Tests
5.1. `tests/test_download.py`: point both existing tests at the sample
     fixture; the "resumes and completes" test additionally opens each
     produced PNG and asserts its dimensions are exactly 1920x1080 (not
     just that a path string was returned) — this step's whole point is
     doing real conversion, so a test that never inspects a real pixel
     wouldn't catch a regression to fake data.
5.2. `tests/test_runner.py`: update `run_pipeline(...)` calls to the new
     `local_pptx_path` parameter, pointed at the same fixture; raise
     timeouts to accommodate real subprocess time.
5.3. `tests/test_pipeline_ui.py`: update the one hardcoded
     `slide_count == 5` assumption (leftover from the old fake stub) to
     `== 3`, matching the real fixture's actual slide count.
5.4. Run the full `uv run pytest` suite, confirm no regressions.

## 6. Validation pass
6.1. Run the real conversion manually against the sample fixture (and,
     time permitting, a second small deck) outside of pytest, confirming
     image count/order/resolution by hand.
6.2. Fill in specs/2026-08-23-download-and-slide-images/validation.md.
6.3. Update Phase 4's status in specs/roadmap.md to ✅.
