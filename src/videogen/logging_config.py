"""Central logging setup, shared by the CLI entry point and the FastAPI app.

Every pipeline module logs through `logging.getLogger(__name__)`, so this
just needs to configure the root/`videogen` logger once, however the app
is started (`uv run python -m videogen.pipeline` or `uvicorn`/the web UI).

Level is controlled by the `VIDEOGEN_LOG_LEVEL` env var (default INFO) so
DEBUG-level observability can be turned on without a code change, e.g.:

    VIDEOGEN_LOG_LEVEL=DEBUG uv run uvicorn videogen.app:app
"""

import logging
import os

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    level_name = os.environ.get("VIDEOGEN_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # Root stays at INFO regardless — DEBUG only applies to our own
    # "videogen" logger tree, so turning on DEBUG doesn't flood the output
    # with third-party libraries' internal debug logging (PIL, urllib3,
    # elevenlabs's HTTP client, etc.).
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("videogen").setLevel(level)
