# Requirements — Project Scaffold (Phase 0)

## Context

This is Phase 0 of specs/roadmap.md: the first buildable slice of VideoGen.
Nothing pipeline-specific exists yet — this phase only proves the base
project can be set up, run, and tested per specs/tech-stack.md, so later
phases (mock pipeline, approval gate, real steps) have a working
foundation to build on. Per specs/mission.md's "prove the shape before the
substance" principle, this phase intentionally contains no pipeline logic.

## Scope decisions (confirmed with user)

- **Layout:** `src/` layout — app code lives under `src/videogen/`, not a
  flat `app/` package. Follows modern Python packaging convention and
  avoids import-path ambiguity as the codebase grows.
- **Health check:** `GET /health` returns `{"status": "ok"}`. No version
  field for now — kept minimal, can be extended later without breaking
  the contract.
- **WebSocket echo:** `/ws/echo` — plain text echo only. Client sends a
  text frame, server sends the identical text back. No JSON envelope yet;
  that shape is deferred to Phase 3 (approval-gate UI) when a real status
  message format is needed.
- **CI:** Add a GitHub Actions workflow (`.github/workflows/test.yml`)
  that runs `uv sync` + `pytest` on push and PR. In scope for this phase,
  not deferred.

## In scope

- `pyproject.toml` managed by `uv`, with FastAPI, uvicorn, pytest,
  pytest-asyncio, websockets (test client) as dependencies.
- `src/videogen/` package containing the FastAPI app.
- `GET /health` route.
- `/ws/echo` WebSocket route.
- pytest test suite covering both routes.
- GitHub Actions workflow running the test suite.

## Out of scope

- Any pipeline step (mock or real) — that starts at Phase 1.
- Any approval-gate logic or UI — that starts at Phase 3.
- Google Drive, ElevenLabs, python-pptx, ffmpeg, or LibreOffice
  integration — none of these are touched in this phase.
- Deployment/hosting configuration beyond CI running tests.

## Constraints (from specs/tech-stack.md)

- Python 3.11+, dependency management via `uv` only (no pip/requirements.txt).
- FastAPI + native WebSocket support (no separate ASGI WS library).
- Tests via pytest + pytest-asyncio.
- No frontend build step / SPA framework — not needed yet in this phase
  since there are no server-rendered templates to add until Phase 3.
