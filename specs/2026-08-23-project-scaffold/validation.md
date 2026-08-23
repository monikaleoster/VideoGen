# Validation — Project Scaffold (Phase 0)

This file is filled in once implementation (plan.md) is complete. It's the
merge gate for this feature branch: nothing here should stay unchecked
when the PR is proposed for merge.

## Automated checks

- [x] `uv sync` installs cleanly with no dependency resolution errors.
- [x] `uv run pytest` passes, including:
  - [x] `GET /health` test (200, `{"status": "ok"}`)
  - [x] `/ws/echo` WebSocket test (sent text == received text)
- [x] GitHub Actions workflow (`test.yml`) added, runs `uv sync` + `uv run
      pytest`; syntax reviewed manually (actionlint unavailable in this
      environment) — green-run confirmation pending once pushed.

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

All five steps above were run by hand against `uv run uvicorn
videogen.app:app` on a local port: `/health` returned `{"status":"ok"}`
with a 200 status; `/ws/echo` echoed both a first and a second message on
the same connection; the server logged the connection opening and shut
down cleanly with no errors on disconnect.

## Result

- Automated checks: done — `uv sync` and `uv run pytest` both clean (2
  passed); CI workflow added, live green-run pending first push.
- Manual verification: done — all 5 steps above confirmed against a
  locally running server.
- Outcome: ready to merge.

## Roadmap update

Once this phase is fully validated, mark Phase 0 as ✅ in
specs/roadmap.md.
