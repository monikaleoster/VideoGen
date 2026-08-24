"""Real render step: slide images + per-slide audio -> final MP4.

Per specs/roadmap.md Phase 5 (re-validated against real inputs): each
slide becomes one video segment (its image held static, its real audio
track if it has one), segments are concatenated in order into the final
video. A slide with no audio (`audio_paths[i] is None`, per Phase 6/7's
`has_notes` flag) gets a graceful fallback: a fixed-duration silent
segment, so it still appears in the output rather than being dropped or
crashing the render.
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from videogen.pipeline import workdir
from videogen.pipeline.base import StepState, StepStatus

logger = logging.getLogger(__name__)

# Fallback duration for a slide with no audio — long enough to read the
# slide, short enough not to pad the video unreasonably.
_SILENT_SEGMENT_DURATION_SEC = 3.0


@dataclass
class RenderInput:
    slide_image_paths: list[str]
    audio_paths: list[str | None]


@dataclass
class RenderOutput:
    video_path: str
    duration_sec: float


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[RenderOutput] = StepState()


def _probe_duration_sec(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _render_segment(image_path: str, audio_path: str | None, out_path: Path) -> None:
    """Render one slide's image (+ its audio, or a silent fallback) to
    `out_path` as a single video segment."""
    if audio_path is not None:
        logger.debug("Rendering segment for %s with audio %s -> %s", image_path, audio_path, out_path)
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(out_path),
        ]
    else:
        logger.debug(
            "Rendering silent %.1fs fallback segment for %s (no audio) -> %s",
            _SILENT_SEGMENT_DURATION_SEC, image_path, out_path,
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-c:v", "libx264",
            "-t", str(_SILENT_SEGMENT_DURATION_SEC),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            str(out_path),
        ]
    subprocess.run(cmd, check=True, capture_output=True)


def _concat_segments(segment_paths: list[Path], out_path: Path, work_dir: Path) -> None:
    concat_list = work_dir / "concat_list.txt"
    concat_list.write_text("".join(f"file '{p}'\n" for p in segment_paths))
    logger.debug("Concatenating %d segments via %s -> %s", len(segment_paths), concat_list, out_path)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(out_path)],
        check=True,
        capture_output=True,
    )


def _render_video(
    slide_image_paths: list[str], audio_paths: list[str | None], work_dir: Path
) -> tuple[str, float]:
    segment_paths = []
    for i, (image_path, audio_path) in enumerate(zip(slide_image_paths, audio_paths, strict=True), start=1):
        segment_path = work_dir / f"segment_{i:02d}.mp4"
        _render_segment(image_path, audio_path, segment_path)
        segment_paths.append(segment_path)
        logger.info("Rendered segment %d/%d (%s)", i, len(slide_image_paths), segment_path.name)

    final_path = work_dir / "final_video.mp4"
    _concat_segments(segment_paths, final_path, work_dir)
    duration = _probe_duration_sec(final_path)
    return str(final_path), duration


async def run_render(step_input: RenderInput) -> RenderOutput:
    """Run the real render, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()

    slide_count = len(step_input.slide_image_paths)
    no_audio_count = sum(1 for a in step_input.audio_paths if a is None)
    logger.info(
        "render starting: %d slides (%d with audio, %d silent fallback)",
        slide_count, slide_count - no_audio_count, no_audio_count,
    )

    work_dir = workdir.make_work_dir(prefix="videogen_render_")

    # ffmpeg/ffprobe work is blocking — run it off the event loop thread so
    # the WebSocket status push keeps working during rendering.
    video_path, duration = await asyncio.to_thread(
        _render_video, step_input.slide_image_paths, step_input.audio_paths, work_dir
    )
    logger.info("render complete: %s (%.1fs)", video_path, duration)

    output = RenderOutput(video_path=video_path, duration_sec=duration)
    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output
