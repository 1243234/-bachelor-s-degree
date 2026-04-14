import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask

from app.domain.llm import generate_slide_deck
from app.domain.preset_templates import PRESET_LABELS, get_preset_preview_tokens
from app.domain.slide_style import (
    BODY_COLOR_LABELS,
    BODY_SIZE_LABELS,
    PALETTE_LABELS,
    TITLE_COLOR_LABELS,
    TITLE_SIZE_LABELS,
    get_body_color_preview_tokens,
    get_palette_preview_tokens,
    get_title_color_preview_tokens,
)
from app.domain.ppt_builder import build_pptx
from app.domain.topic_extract import extract_topic_via_llm
from app.services.simple_generation import cleanup_temp_paths, prepare_generation_from_form
from app.services.simple_job_runner import cleanup_after_download, create_job, run_simple_job
from app.services.simple_job_runner import JOBS as SIMPLE_JOBS
from app.settings import get_settings

router = APIRouter(tags=["simple"])


@router.get("/normalize-topic")
async def normalize_topic_preview(topic: str = Query("", max_length=500)) -> dict[str, str]:
    """供前端失焦时同步规范化：与生成链路相同，对主题做 LLM 信息抽取（未配置 Key 时仅裁剪空白）。"""
    t = topic.strip()
    if not t:
        return {"topic": ""}
    s = get_settings()
    timeout = min(30.0, s.httpx_timeout_s)
    out = await extract_topic_via_llm(
        t,
        api_base_url=s.deepseek_api_base,
        model=s.deepseek_model,
        api_key=s.deepseek_api_key or "",
        timeout_s=timeout,
    )
    return {"topic": out}


@router.get("/preset-preview-styles")
async def preset_preview_styles() -> dict:
    """内置幻灯片主题色 + 可选预设配色（供预览）。"""
    return {
        "presets": get_preset_preview_tokens(),
        "labels": PRESET_LABELS,
        "palettes": get_palette_preview_tokens(),
        "palette_labels": PALETTE_LABELS,
        "title_colors": get_title_color_preview_tokens(),
        "title_color_labels": TITLE_COLOR_LABELS,
        "body_colors": get_body_color_preview_tokens(),
        "body_color_labels": BODY_COLOR_LABELS,
        "title_size_labels": TITLE_SIZE_LABELS,
        "body_size_labels": BODY_SIZE_LABELS,
    }


def _cleanup(*paths: Path) -> None:
    cleanup_temp_paths(list(paths))


async def _prepare(
    topic: str,
    audience: str,
    slide_count: int,
    template_preset: str,
    style_palette: str | None,
    style_title_size: str | None,
    style_body_size: str | None,
    style_title_color: str | None,
    style_body_color: str | None,
    cover_image: UploadFile | None,
    logo_image: UploadFile | None,
):
    return await prepare_generation_from_form(
        topic=topic,
        audience=audience,
        slide_count=slide_count,
        template_preset=template_preset,
        style_palette=style_palette,
        style_title_size=style_title_size,
        style_body_size=style_body_size,
        style_title_color=style_title_color,
        style_body_color=style_body_color,
        cover_image=cover_image,
        logo_image=logo_image,
    )


@router.post("/generate")
async def simple_generate(
    topic: str = Form(..., min_length=1, max_length=500),
    audience: str = Form("大学生"),
    slide_count: int = Form(8, ge=3, le=30),
    template_preset: str = Form("simple"),
    style_palette: str | None = Form("theme"),
    style_title_size: str | None = Form("theme"),
    style_body_size: str | None = Form("theme"),
    style_title_color: str | None = Form("theme"),
    style_body_color: str | None = Form("theme"),
    cover_image: UploadFile | None = File(None),
    logo_image: UploadFile | None = File(None),
) -> FileResponse:
    prepared = await _prepare(
        topic,
        audience,
        slide_count,
        template_preset,
        style_palette,
        style_title_size,
        style_body_size,
        style_title_color,
        style_body_color,
        cover_image,
        logo_image,
    )
    settings = get_settings()
    try:
        deck = await generate_slide_deck(prepared.body, settings.httpx_timeout_s)
        build_pptx(
            prepared.body,
            deck,
            prepared.out_path,
            cover_image_path=prepared.cover_image_path,
            logo_image_path=prepared.logo_image_path,
        )
    except Exception as e:
        cleanup_temp_paths(prepared.tmp_paths)
        raise HTTPException(status_code=502, detail=f"生成失败：{e}") from e

    cleanup_inputs = [p for p in prepared.tmp_paths if p != prepared.out_path]
    return FileResponse(
        path=prepared.out_path,
        filename="teaching.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        background=BackgroundTask(_cleanup, prepared.out_path, *cleanup_inputs),
    )


@router.post("/jobs")
async def create_generation_job(
    topic: str = Form(..., min_length=1, max_length=500),
    audience: str = Form("大学生"),
    slide_count: int = Form(8, ge=3, le=30),
    template_preset: str = Form("simple"),
    style_palette: str | None = Form("theme"),
    style_title_size: str | None = Form("theme"),
    style_body_size: str | None = Form("theme"),
    style_title_color: str | None = Form("theme"),
    style_body_color: str | None = Form("theme"),
    cover_image: UploadFile | None = File(None),
    logo_image: UploadFile | None = File(None),
) -> dict[str, str]:
    prepared = await _prepare(
        topic,
        audience,
        slide_count,
        template_preset,
        style_palette,
        style_title_size,
        style_body_size,
        style_title_color,
        style_body_color,
        cover_image,
        logo_image,
    )
    job_id, job = create_job()
    asyncio.create_task(run_simple_job(job, prepared))
    return {"job_id": job_id}


@router.get("/jobs/{job_id}/events")
async def job_events_stream(job_id: str):
    job = SIMPLE_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在或已过期。")

    async def event_gen():
        idx = 0
        while True:
            while idx < len(job.events):
                payload = job.events[idx]
                idx += 1
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if payload.get("type") in ("error", "done"):
                    return
            if job.finished and idx >= len(job.events):
                break
            await asyncio.sleep(0.12)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/jobs/{job_id}/download")
async def download_job_result(job_id: str) -> FileResponse:
    job = SIMPLE_JOBS.get(job_id)
    if not job or not job.finished or job.out_path is None or not job.out_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="暂无可下载文件，请等待生成完成或重新生成。",
        )
    out_path = job.out_path
    return FileResponse(
        path=out_path,
        filename="teaching.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        background=BackgroundTask(cleanup_after_download, job_id),
    )
