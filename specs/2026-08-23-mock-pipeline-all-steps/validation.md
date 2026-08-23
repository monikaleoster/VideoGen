# Validation — Mock Pipeline, All 7 Steps (Phase 2)

## How this phase succeeds

Per specs/roadmap.md's Phase 2 validation criteria: run the full mock
pipeline start to finish; confirm every step blocks on approval in order
and none skip ahead. Concretely, this phase is done when:

- [x] `uv run pytest` passes, including unit tests for all six new stub
      steps, the runner's ordering/chaining tests, and Phase 0/Phase 1's
      existing tests, with no regressions.
- [x] Each of the seven steps, run as part of the full pipeline, reaches
      `WAITING_APPROVAL` and provably does not proceed until its own
      `asyncio.Event` is set — no step ever starts before the previous
      step reaches `DONE`.
- [x] Each step's fake output is threaded into the next step's input
      (download → notes extraction → TTS → audio upload → embed → render
      → video upload), confirmed by at least one consistent field carried
      through the chain (e.g. slide count).
- [x] The CLI runner (`uv run python -m videogen.pipeline`) drives all
      seven steps end-to-end unattended, logging every status transition
      via Python's `logging` module with enough detail (step name,
      timestamp, fake output summary) to follow the whole run from
      terminal output alone.
- [x] No step-specific logic leaked into `runner.py` — each step's fake
      data generation lives in its own module; the runner only
      orchestrates.
- [x] Phase 1's existing `/steps/notes-extraction/*` HTTP routes still
      work unchanged (left untouched per requirements.md).

## Merge readiness checklist

- [x] All items in "How this phase succeeds" are checked.
- [ ] CI (`.github/workflows/test.yml`) is green on the PR.
- [x] `specs/roadmap.md` Phase 2 status updated to ✅.
- [x] No leftover debug prints, TODOs without a follow-up phase
      reference, or dead code from earlier attempts.
- [x] Manual verification section below is complete.

## Manual verification

Performed by: Claude (agent session), 2026-08-23

1. **CLI path — full run**
   - Command run: `uv run python -m videogen.pipeline`
   - Observed output: all seven steps (download, notes_extraction, tts,
     audio_upload, embed, render, video_upload) logged RUNNING →
     WAITING_APPROVAL (with fake-output summary) → simulated-approval →
     DONE, in that fixed order, ending with:
     `Pipeline run complete: final video at https://drive.google.com/file/d/fake-drive-id-video-01/view`
   - Confirmed no step's `RUNNING` line appears before the previous
     step's `DONE` line: yes — each step's `DONE` line is immediately
     followed by the next step's `RUNNING` line, with no interleaving
     (verified in the captured terminal output, e.g. `[download] DONE`
     directly precedes `[notes_extraction] RUNNING`).
   - Confirmed each step's logged fake-output summary is well-shaped
     (non-empty, plausible fields per requirements.md): yes — e.g.
     `DownloadOutput(local_pptx_path=..., slide_image_paths=[...5 paths],
     slide_count=5)`, `TtsOutput(audio_paths=[...5], durations_sec=[4.0,
     4.5, 5.0, 5.5, 6.0])`, etc.

2. **Chaining spot-check**
   - Picked slide count as the field to trace end-to-end and confirmed it
     stays consistent from `download`'s output through the chain in the
     log: yes — `download` produced `slide_count=5` with 5
     `slide_image_paths`; `notes_extraction` produced `slide_count=5` with
     5 notes; `tts` produced 5 `audio_paths`/`durations_sec`;
     `audio_upload` produced 5 `drive_file_ids`/`drive_urls`; `embed`
     produced `slides_embedded` with 5 entries; `render`'s
     `duration_sec=25.0` is the sum of all 5 per-slide durations. Also
     covered directly by `tests/test_runner.py::
     test_chained_output_threads_through_the_pipeline`, which asserts the
     slide count at every hop.

3. **Blocking proof**
   - Confirmed via test output that every step genuinely blocks on its
     Event rather than merely completing fast:
     `tests/test_{download,tts,audio_upload,embed,render,video_upload,
     notes_extraction}.py::test_step_blocks_until_approved` each start
     the step, wait for `WAITING_APPROVAL`, sleep 0.05s, and assert the
     task is still not done — all pass. `tests/test_runner.py::
     test_steps_run_in_fixed_order_and_none_skip_ahead` additionally
     asserts a step's `RUNNING` transition never occurs before the
     previous step's `DONE` transition, across the whole chain.

4. **Regression check**
   - Phase 0's `/health` and `/ws/echo`, and Phase 1's
     `/steps/notes-extraction/*` routes, still work unchanged: yes —
     `tests/test_app.py` (2 tests) and `tests/test_notes_extraction_routes.py`
     (3 tests) pass unmodified.
   - Full `uv run pytest` run: `22 passed, 1 warning in 4.56s`.

## Result

PASS
