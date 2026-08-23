# Validation — Project Scaffold (Phase 0)

This file is filled in once implementation (plan.md) is complete. It's the
merge gate for this feature branch: nothing here should stay unchecked
when the PR is proposed for merge.

## Automated checks

- [ ] `uv sync` installs cleanly with no dependency resolution errors.
- [ ] `uv run pytest` passes, including:
  - [ ] `GET /health` test (200, `{"status": "ok"}`)
  - [ ] `/ws/echo` WebSocket test (sent text == received text)
- [ ] GitHub Actions workflow (`test.yml`) runs `uv sync` + `uv run pytest`
      and is green on the PR.

## Manual verification

Run these by hand against the running server before considering this
phase done — automated tests cover the contract, this confirms it also
works the way a human would actually hit it:

1. Start the server: `uv run uvicorn videogen.app:app --reload`.
2. `curl -s localhost:8000/health` → confirm it prints exactly
   `{"status":"ok"}` (or equivalent JSON) with a 200 status.
3. Connect to `ws://localhost:8000/ws/echo` with a WebSocket client
   (e.g. `websocat`, or a quick Python script using `websockets`), send a
   sample string, confirm the identical string comes back.
4. Send a second message on the same connection without reconnecting,
   confirm it still echoes (loop doesn't only handle one message).
5. Disconnect the client and confirm the server doesn't error/crash in
   its logs.

## Result

- Automated checks: _pending_
- Manual verification: _pending_
- Outcome: _pending_ (fill in once all boxes above are checked: ready to
  merge, or what's still blocking)

## Roadmap update

Once this phase is fully validated, mark Phase 0 as ✅ in
specs/roadmap.md.
