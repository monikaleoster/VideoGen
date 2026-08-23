"""Real download step: local .pptx path -> LibreOffice-rendered slide images.

Deviates from the original roadmap plan (real Google Drive auth/download) —
per specs/2026-08-23-download-and-slide-images/requirements.md, this phase
takes a local filesystem path to an already-present .pptx (as if it had
already been downloaded) and does the real LibreOffice-headless conversion
to slide-image PNGs. Real Google Drive integration is deferred.
"""

import asyncio
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from videogen.pipeline.base import StepState, StepStatus

SLIDE_WIDTH_PX = 1920
SLIDE_HEIGHT_PX = 1080


@dataclass
class DownloadInput:
    local_pptx_path: str


@dataclass
class DownloadOutput:
    local_pptx_path: str
    slide_image_paths: list[str]
    slide_count: int


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[DownloadOutput] = StepState()


def _convert_to_slide_images(pptx_path: Path, work_dir: Path) -> list[Path]:
    """Convert `pptx_path` to one 1920x1080 PNG per slide inside `work_dir`.

    Two real subprocesses: LibreOffice headless (pptx -> pdf), then
    pdftoppm (pdf -> per-page PNGs at an exact pixel size). A fresh
    UserInstallation profile per call keeps concurrent conversions from
    fighting over LibreOffice's profile lock.
    """
    profile_dir = work_dir / "lo_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "soffice",
            "--headless",
            "--norestore",
            f"-env:UserInstallation=file://{profile_dir}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(work_dir),
            str(pptx_path),
        ],
        check=True,
        capture_output=True,
    )

    pdf_path = work_dir / f"{pptx_path.stem}.pdf"
    if not pdf_path.exists():
        raise RuntimeError(f"LibreOffice did not produce a PDF at {pdf_path}")

    image_prefix = work_dir / "slide"
    subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-scale-to-x",
            str(SLIDE_WIDTH_PX),
            "-scale-to-y",
            str(SLIDE_HEIGHT_PX),
            str(pdf_path),
            str(image_prefix),
        ],
        check=True,
        capture_output=True,
    )

    raw_images = sorted(
        work_dir.glob("slide-*.png"),
        key=lambda p: int(p.stem.rsplit("-", 1)[-1]),
    )
    if not raw_images:
        raise RuntimeError("pdftoppm did not produce any slide images")

    final_paths = []
    for i, raw in enumerate(raw_images, start=1):
        final_path = work_dir / f"slide_{i:02d}.png"
        raw.rename(final_path)
        final_paths.append(final_path)
    return final_paths


async def run_download(step_input: DownloadInput) -> DownloadOutput:
    """Run the real conversion, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()

    source_path = Path(step_input.local_pptx_path)
    work_dir = Path(tempfile.mkdtemp(prefix="videogen_download_"))
    local_copy = work_dir / source_path.name
    shutil.copy2(source_path, local_copy)

    # LibreOffice/pdftoppm are blocking subprocess calls — run them off the
    # event loop thread so the WebSocket status push keeps working live.
    slide_images = await asyncio.to_thread(_convert_to_slide_images, local_copy, work_dir)

    output = DownloadOutput(
        local_pptx_path=str(local_copy),
        slide_image_paths=[str(p) for p in slide_images],
        slide_count=len(slide_images),
    )
    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output
