import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.domain.llm import generate_slide_deck
from app.domain.ppt_builder import build_pptx
from app.settings import get_settings

from app.services.simple_generation import PreparedGeneration, cleanup_temp_paths


@dataclass
class SimpleGenerationJob:
    job_id: str
    events: list[dict] = field(default_factory=list)
    finished: bool = False
    out_path: Path | None = None
    paths_after_download: list[Path] = field(default_factory=list)


JOBS: dict[str, SimpleGenerationJob] = {}


def _emit(job: SimpleGenerationJob, payload: dict) -> None:
    job.events.append(payload)


async def run_simple_job(job: SimpleGenerationJob, prepared: PreparedGeneration) -> None:
    settings = get_settings()
    job.out_path = prepared.out_path
    job.paths_after_download = list(prepared.tmp_paths)

    try:
        _emit(
            job,
            {
                "type": "progress",
                "stage": "start",
                "percent": 8,
                "message": "已就绪，正在请求 AI 生成大纲…",
            },
        )
        await asyncio.sleep(0)
        _emit(
            job,
            {
                "type": "progress",
                "stage": "llm",
                "percent": 28,
                "message": "正在生成各页标题与要点…",
            },
        )
        deck = await generate_slide_deck(prepared.body, settings.httpx_timeout_s)
        _emit(
            job,
            {
                "type": "preview",
                "deck": deck.model_dump(),
                "topic": prepared.body.topic,
                "audience": prepared.body.audience,
                "template_preset": prepared.body.template_preset,
                "style": prepared.body.style.model_dump(mode="json"),
                "has_cover_image": prepared.cover_image_path is not None,
                "has_logo": prepared.logo_image_path is not None,
            },
        )
        _emit(
            job,
            {
                "type": "progress",
                "stage": "building",
                "percent": 72,
                "message": "正在应用版式、配色与配图，写入 .pptx…",
            },
        )
        build_pptx(
            prepared.body,
            deck,
            prepared.out_path,
            cover_image_path=prepared.cover_image_path,
            logo_image_path=prepared.logo_image_path,
        )
        _emit(
            job,
            {
                "type": "done",
                "percent": 100,
                "message": "生成完成。请核对预览后下载。",
            },
        )
    except Exception as e:
        cleanup_temp_paths(prepared.tmp_paths)
        job.out_path = None
        job.paths_after_download = []
        _emit(job, {"type": "error", "detail": f"生成失败：{e}"})
    finally:
        job.finished = True


def create_job() -> tuple[str, SimpleGenerationJob]:
    job_id = str(uuid.uuid4())
    job = SimpleGenerationJob(job_id=job_id)
    JOBS[job_id] = job
    return job_id, job


def cleanup_after_download(job_id: str) -> None:
    job = JOBS.pop(job_id, None)
    if not job:
        return
    for p in job.paths_after_download:
        if p is not None and p.is_file():
            try:
                p.unlink()
            except OSError:
                pass
