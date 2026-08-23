# Plan — Project Scaffold (Phase 0)

Numbered task groups. Complete and validate each group before moving to
the next.

## 1. Project setup
1.1. Initialize `pyproject.toml` via `uv init` (or hand-write it) targeting
     Python 3.11+.
1.2. Add dependencies: `fastapi`, `uvicorn[standard]`.
1.3. Add dev dependencies: `pytest`, `pytest-asyncio`, `httpx` (for
     `TestClient`/WebSocket test support).
1.4. Create `src/videogen/__init__.py` and confirm `uv run python -c
     "import videogen"` works (package is importable under the `src/`
     layout).

## 2. FastAPI app skeleton
2.1. Create `src/videogen/app.py` (or `main.py`) with a bare `FastAPI()`
     instance.
2.2. Add an entrypoint (`src/videogen/__main__.py` or a `uv run` script)
     so `uv run uvicorn videogen.app:app` starts the server.

## 3. Health-check route
3.1. Add `GET /health` returning `{"status": "ok"}`.
3.2. Write a pytest test using `TestClient` asserting the route returns
     200 and the exact JSON body.

## 4. WebSocket echo route
4.1. Add `/ws/echo`: accept the connection, loop receiving text frames and
     sending each one back verbatim until the client disconnects.
4.2. Write a pytest test using `TestClient`'s WebSocket support: connect,
     send a sample string, assert the same string comes back.

## 5. CI
5.1. Add `.github/workflows/test.yml`: checkout, set up `uv`, `uv sync`,
     `uv run pytest`.
5.2. Confirm the workflow is syntactically valid (actionlint or a manual
     read) — actual green-run confirmation happens once pushed.

## 6. Validation pass
6.1. Run `uv run uvicorn videogen.app:app` locally, confirm `/health`
     responds via `curl` and `/ws/echo` echoes via a quick WebSocket
     client.
6.2. Run `uv run pytest`, confirm both tests pass.
6.3. Fill in specs/2026-08-23-project-scaffold/validation.md with results.
