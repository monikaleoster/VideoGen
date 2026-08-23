# Validation — Mock Pipeline, All 7 Steps (Phase 2)

## How this phase succeeds

Per specs/roadmap.md's Phase 2 validation criteria: run the full mock
pipeline start to finish; confirm every step blocks on approval in order
and none skip ahead. Concretely, this phase is done when:

- [ ] `uv run pytest` passes, including unit tests for all six new stub
      steps, the runner's ordering/chaining tests, and Phase 0/Phase 1's
      existing tests, with no regressions.
- [ ] Each of the seven steps, run as part of the full pipeline, reaches
      `WAITING_APPROVAL` and provably does not proceed until its own
      `asyncio.Event` is set — no step ever starts before the previous
      step reaches `DONE`.
- [ ] Each step's fake output is threaded into the next step's input
      (download → notes extraction → TTS → audio upload → embed → render
      → video upload), confirmed by at least one consistent field carried
      through the chain (e.g. slide count).
- [ ] The CLI runner (`uv run python -m videogen.pipeline`) drives all
      seven steps end-to-end unattended, logging every status transition
      via Python's `logging` module with enough detail (step name,
      timestamp, fake output summary) to follow the whole run from
      terminal output alone.
- [ ] No step-specific logic leaked into `runner.py` — each step's fake
      data generation lives in its own module; the runner only
      orchestrates.
- [ ] Phase 1's existing `/steps/notes-extraction/*` HTTP routes still
      work unchanged (left untouched per requirements.md).

## Merge readiness checklist

- [ ] All items in "How this phase succeeds" are checked.
- [ ] CI (`.github/workflows/test.yml`) is green on the PR.
- [ ] `specs/roadmap.md` Phase 2 status updated to ✅.
- [ ] No leftover debug prints, TODOs without a follow-up phase
      reference, or dead code from earlier attempts.
- [ ] Manual verification section below is complete.

## Manual verification

Performed by: _(name, date — fill in once implementation lands)_

1. **CLI path — full run**
   - Command run: `uv run python -m videogen.pipeline`
   - Observed output: _(paste full log output showing all seven steps'
     status transitions in order)_
   - Confirmed no step's `RUNNING` line appears before the previous
     step's `DONE` line: _(yes/no + evidence)_
   - Confirmed each step's logged fake-output summary is well-shaped
     (non-empty, plausible fields per requirements.md): _(yes/no)_

2. **Chaining spot-check**
   - Picked one field to trace end-to-end (e.g. slide count) and
     confirmed it stays consistent from `download`'s output through
     `render`'s output in the log: _(yes/no + evidence)_

3. **Blocking proof**
   - Confirmed (via test output or manual timing) that at least one step
     genuinely blocked on its Event rather than merely completing fast:
     _(yes/no + evidence)_

4. **Regression check**
   - Phase 0's `/health` and `/ws/echo`, and Phase 1's
     `/steps/notes-extraction/*` routes, still work unchanged:
     _(yes/no + evidence)_
   - Full `uv run pytest` run: _(paste pass count)_

## Result

_(PASS/FAIL — fill in once implementation and manual verification are
complete)_
