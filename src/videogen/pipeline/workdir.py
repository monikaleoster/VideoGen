"""Shared scratch-directory helper, per
specs/2026-08-23-download-input-config/requirements.md: every step that
needs a fresh work directory calls `make_work_dir` instead of `tempfile.
mkdtemp()` directly, so that once a run sets a shared tmp root (via
`set_tmp_root`), every step's work dir nests under that same root. With no
root set, behavior is unchanged from before this module existed — a bare
`tempfile.mkdtemp(prefix=...)` in the OS default temp location.
"""

import tempfile
from pathlib import Path

# Module-level so the CLI/HTTP routes and every step module share the same
# current run's root. `None` means "use the OS default temp dir", today's
# behavior.
_tmp_root: Path | None = None


def set_tmp_root(path: str | None) -> None:
    """Record the current run's shared tmp root, or clear it back to the OS
    default when `path` is `None` or blank."""
    global _tmp_root
    _tmp_root = Path(path) if path else None


def make_work_dir(prefix: str) -> Path:
    """Create and return a fresh work directory.

    Nested under the current shared root (created first if needed) when one
    is set via `set_tmp_root`; otherwise today's behavior — a bare
    `tempfile.mkdtemp(prefix=prefix)` in the OS default temp location.
    """
    if _tmp_root is not None:
        _tmp_root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=prefix, dir=str(_tmp_root)))
    return Path(tempfile.mkdtemp(prefix=prefix))
