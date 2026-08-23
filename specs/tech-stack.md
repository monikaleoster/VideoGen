# Tech Stack

## Language & runtime

- **Python 3.11+** for the entire backend and pipeline logic.
- **uv** for environment and dependency management (`uv venv`, `uv add`,
  `uv run`). No `requirements.txt` / plain `pip` workflow — `pyproject.toml`
  + `uv.lock` is the single source of truth for dependencies.

## Web server & orchestration

- **FastAPI** serves the HTTP API and the approval-gate UI.
- **WebSocket** (via FastAPI's native WebSocket support) pushes live
  pipeline status to the browser as each step runs.
- **`asyncio.Event`**, one per pipeline step, is the block/unblock
  mechanism for the approval gate — a step's coroutine awaits its Event
  before continuing; the Approve action in the UI sets it.
- Pipeline steps are implemented as independent, individually callable
  async functions (or a small class per step) orchestrated by a single
  pipeline runner — never as logic inlined into route handlers — so each
  step stays testable and replaceable per the mission's "every step stands
  alone" principle.

## Frontend (approval-gate UI)

- **Server-rendered HTML** via FastAPI (Jinja2 templates) plus **vanilla
  JavaScript** for the WebSocket client and Approve/Reject actions.
- No frontend build step, no SPA framework — kept intentionally minimal
  since the UI's only job is to show step output and capture one decision.

## Integrations

- **Google Drive API** (`google-api-python-client` + `google-auth`) for
  reading the source `.pptx` and uploading every generated artifact
  (audio clips, updated `.pptx`, final `.mp4`) back to the same folder.
- **ElevenLabs API** (`elevenlabs` Python SDK or direct HTTP calls) for
  text-to-speech, single voice per run, fixed stability/similarity
  settings, driven by a user-supplied voice ID and API key entered per
  run through the approval-gate UI and held in memory only for that run —
  a deliberate deviation from this file's general secrets convention
  below, confirmed with the human (see
  `specs/2026-08-23-audio-generation-real/requirements.md`); the CLI demo
  entry point has no UI and falls back to reading
  `ELEVENLABS_API_KEY`/`ELEVENLABS_VOICE_ID` from the environment. Per
  the same Phase 7 decision, calls are **not** retried on failure —
  including rate-limit (429) responses; any failure is reported as a
  step failure rather than retried.

## Slide & media processing

- **`python-pptx`** for reading speaker notes and embedding generated
  audio (set to autoplay) back into the deck.
- **LibreOffice (headless)** for converting `.pptx` slides to images —
  invoked as a subprocess (`soffice --headless --convert-to`).
- **ffmpeg**, via `ffmpeg-python` or direct subprocess calls, for pairing
  each slide image with its audio clip into a video segment and
  concatenating segments into the final MP4 without dropped frames or
  audio desync.

## Testing

- **pytest** (with `pytest-asyncio` for the async pipeline steps) for unit
  and integration tests. Each pipeline step must have tests runnable with
  sample/mock inputs, independent of Drive or ElevenLabs network access.

## Conventions

- File naming for uploaded artifacts is predictable and slide-indexed,
  e.g. `slide_01_audio.mp3` — never freeform or timestamp-based names.
- Secrets are never hardcoded or committed. Google Drive credentials are
  read from environment variables / a local `.env` (via `python-dotenv`).
  The ElevenLabs API key and voice ID are the one exception: per Phase
  7's confirmed scope decision, they're entered per run through the
  approval-gate UI and held in memory only for that run (not `.env`,
  not browser storage); the CLI demo entry point, which has no UI, falls
  back to environment variables for these two values only.
