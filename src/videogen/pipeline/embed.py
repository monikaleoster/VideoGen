"""Real embed step: insert each slide's narration audio into the deck.

Per specs/2026-08-23-embed-audio-pptx/requirements.md: a slide with real
TTS audio (`audio_paths[i]` set) gets that clip embedded; a slide with no
audio (`audio_paths[i] is None`, i.e. `has_notes=False` in Phase 6/7) gets
a short silent placeholder clip instead, so every slide ends up with
exactly one autoplay audio element. The step is safe to re-run: any audio
already embedded on a slide (from a previous run) is removed before the
current clip is inserted, so it never produces duplicates. Drive upload of
the result is still Phase 9 — this step only reads/writes local files.
"""

import asyncio
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Emu

from videogen.pipeline.base import StepState, StepStatus

_SILENCE_DURATION_SEC = 1.0
_MIME_TYPE = "audio/mpeg"

# 1x1 EMU is far smaller than a single pixel — effectively invisible, so
# the movie shape's default "media loudspeaker" icon never shows.
_ICON_SIZE = Emu(1)


@dataclass
class EmbedInput:
    local_pptx_path: str
    audio_paths: list[str | None]


@dataclass
class EmbedOutput:
    updated_pptx_path: str
    slides_embedded: list[bool]
    used_placeholder: list[bool]


# Module-level state so the CLI and HTTP routes reach the same in-flight run.
state: StepState[EmbedOutput] = StepState()


def _generate_silence(out_path: Path, duration_sec: float = _SILENCE_DURATION_SEC) -> None:
    """Write `duration_sec` of silent audio to `out_path` via `ffmpeg`."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            str(duration_sec),
            "-q:a",
            "9",
            "-acodec",
            "libmp3lame",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )


def _remove_existing_audio(slide) -> None:
    """Remove any audio/video media shape already on `slide`.

    Makes re-running the step idempotent: a slide that already has an
    embedded clip from a previous run ends up with just the new one, never
    both.
    """
    media_tags = (qn("a:videoFile"), qn("a:audioFile"))
    for shape in list(slide.shapes):
        nvPr = shape._element.find(f".//{qn('p:nvPr')}")
        if nvPr is not None and any(nvPr.find(tag) is not None for tag in media_tags):
            shape._element.getparent().remove(shape._element)

    sld = slide._element
    existing_timing = sld.find(qn("p:timing"))
    if existing_timing is not None:
        sld.remove(existing_timing)


def _add_autoplay_timing(slide, shape_id: int) -> None:
    """Set `shape_id`'s media to autoplay on slide entry.

    Replaces the `p:timing` element `add_movie` itself just added (a
    "wait for a click" timing) with one that starts the media playing
    immediately when the slide begins.
    """
    sld = slide._element
    existing_timing = sld.find(qn("p:timing"))
    if existing_timing is not None:
        sld.remove(existing_timing)

    timing_xml = (
        f'<p:timing {nsdecls("p", "a")}>'
        "<p:tnLst><p:par>"
        '<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
        "<p:childTnLst><p:seq concurrent=\"1\" nextAc=\"seek\">"
        '<p:cTn id="2" dur="indefinite" nodeType="mainSeq">'
        "<p:childTnLst><p:par><p:cTn id=\"3\" fill=\"hold\">"
        '<p:stCondLst><p:cond delay="0"/></p:stCondLst>'
        "<p:childTnLst><p:par><p:cTn id=\"4\" fill=\"hold\">"
        '<p:stCondLst><p:cond delay="0"/></p:stCondLst>'
        "<p:childTnLst>"
        '<p:cmd type="call" cmd="playFrom(0.0)">'
        '<p:cBhvr><p:cTn id="5" dur="indefinite" fill="hold"/>'
        f'<p:tgtEl><p:spTgt spid="{shape_id}"/></p:tgtEl>'
        "</p:cBhvr></p:cmd>"
        "</p:childTnLst></p:cTn></p:par></p:childTnLst>"
        "</p:cTn></p:par></p:childTnLst>"
        "</p:cTn>"
        '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
        "</p:seq></p:childTnLst></p:cTn>"
        "</p:par></p:tnLst>"
        "</p:timing>"
    )
    slide._element.append(parse_xml(timing_xml))


def _embed_clip(slide, clip_path: str) -> None:
    """Embed `clip_path` on `slide` as a hidden, autoplaying audio clip."""
    _remove_existing_audio(slide)

    shape = slide.shapes.add_movie(
        clip_path, Emu(0), Emu(0), _ICON_SIZE, _ICON_SIZE, mime_type=_MIME_TYPE
    )

    # add_movie always writes <a:videoFile>, since python-pptx has no
    # dedicated audio-embedding API; the underlying relationship/media-part
    # plumbing is identical for audio, so retagging to the OOXML-correct
    # <a:audioFile> is enough to make PowerPoint treat it as audio.
    video_file_el = shape._element.find(f".//{qn('a:videoFile')}")
    video_file_el.tag = qn("a:audioFile")

    _add_autoplay_timing(slide, shape.shape_id)


async def run_embed(step_input: EmbedInput) -> EmbedOutput:
    """Run the real embed step, blocking on `state.approval_event` until approved."""
    state.status = StepStatus.RUNNING
    state.output = None
    state.approval_event.clear()

    output = await asyncio.to_thread(_embed_all, step_input)

    state.output = output
    state.status = StepStatus.WAITING_APPROVAL

    await state.approval_event.wait()

    state.status = StepStatus.DONE
    return output


def _embed_all(step_input: EmbedInput) -> EmbedOutput:
    work_dir = Path(tempfile.mkdtemp(prefix="videogen_embed_"))
    silence_path = work_dir / "silence.mp3"
    _generate_silence(silence_path)

    prs = Presentation(step_input.local_pptx_path)

    slides_embedded: list[bool] = []
    used_placeholder: list[bool] = []
    for slide, audio_path in zip(prs.slides, step_input.audio_paths, strict=True):
        is_placeholder = audio_path is None
        clip_path = str(silence_path) if is_placeholder else audio_path
        _embed_clip(slide, clip_path)
        slides_embedded.append(True)
        used_placeholder.append(is_placeholder)

    base_path = step_input.local_pptx_path.removesuffix(".pptx")
    updated_pptx_path = f"{base_path}_with_audio.pptx"
    prs.save(updated_pptx_path)

    return EmbedOutput(
        updated_pptx_path=updated_pptx_path,
        slides_embedded=slides_embedded,
        used_placeholder=used_placeholder,
    )
