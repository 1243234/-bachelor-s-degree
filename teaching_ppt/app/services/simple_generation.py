import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from app.domain.models import JobCreateBody
from app.domain.preset_templates import PRESET_LABELS, VALID_PRESET_IDS
from app.domain.slide_style import style_options_from_form
from app.domain.topic_extract import extract_topic_via_llm
from app.settings import get_settings

_IMAGE_MAX_BYTES = 8 * 1024 * 1024
_ALLOWED_IMAGE_CT = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})
_ALLOWED_IMAGE_SUFFIX = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})


@dataclass
class PreparedGeneration:
    body: JobCreateBody
    tmp_paths: list[Path]
    out_path: Path
    cover_image_path: Path | None = None
    logo_image_path: Path | None = None


def cleanup_temp_paths(paths: list[Path]) -> None:
    for p in paths:
        try:
            if p.is_file():
                p.unlink()
        except OSError:
            pass


async def _save_optional_image(
    upload: UploadFile | None,
    tmp_paths: list[Path],
    label: str,
) -> Path | None:
    if upload is None or not upload.filename:
        return None
    raw_ct = (upload.content_type or "").split(";")[0].strip().lower()
    suffix = Path(upload.filename).suffix.lower()
    ct_ok = raw_ct in _ALLOWED_IMAGE_CT
    suf_ok = suffix in _ALLOWED_IMAGE_SUFFIX
    if not ct_ok and not suf_ok:
        raise HTTPException(
            status_code=400,
            detail=f"{label}仅支持 JPG、PNG、GIF、WebP 格式。",
        )
    content = await upload.read()
    if len(content) > _IMAGE_MAX_BYTES:
        raise HTTPException(status_code=400, detail=f"{label}过大（单张上限 8MB）。")
    if suffix not in _ALLOWED_IMAGE_SUFFIX:
        suffix = ".jpg" if "jpeg" in raw_ct else ".png"
    fd, name = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    path = Path(name)
    tmp_paths.append(path)
    path.write_bytes(content)
    return path


async def prepare_generation_from_form(
    topic: str,
    audience: str,
    slide_count: int,
    template_preset: str,
    style_palette: str | None = None,
    style_title_size: str | None = None,
    style_body_size: str | None = None,
    style_title_color: str | None = None,
    style_body_color: str | None = None,
    cover_image: UploadFile | None = None,
    logo_image: UploadFile | None = None,
) -> PreparedGeneration:
    settings = get_settings()
    key = (settings.deepseek_api_key or "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="服务端未配置 DeepSeek API Key，请在环境变量 DEEPSEEK_API_KEY 或 .env 中设置。",
        )

    tmp_paths: list[Path] = []

    out_fd, out_name = tempfile.mkstemp(suffix=".pptx")
    os.close(out_fd)
    out_path = Path(out_name)
    tmp_paths.append(out_path)

    if template_preset not in VALID_PRESET_IDS:
        choices = "、".join(
            f"{pid}（{PRESET_LABELS[pid]}）" for pid in sorted(VALID_PRESET_IDS)
        )
        cleanup_temp_paths(tmp_paths)
        raise HTTPException(
            status_code=400,
            detail=f"幻灯片风格无效，可选：{choices}。",
        )
    topic_clean = await extract_topic_via_llm(
        topic,
        api_base_url=settings.deepseek_api_base,
        model=settings.deepseek_model,
        api_key=key,
        timeout_s=min(30.0, settings.httpx_timeout_s),
    )
    if not topic_clean:
        cleanup_temp_paths(tmp_paths)
        raise HTTPException(status_code=400, detail="请填写课程主题。")

    try:
        style = style_options_from_form(
            style_palette=style_palette,
            style_title_size=style_title_size,
            style_body_size=style_body_size,
            style_title_color=style_title_color,
            style_body_color=style_body_color,
        )
    except (ValueError, ValidationError) as e:
        cleanup_temp_paths(tmp_paths)
        msg = str(e)
        if isinstance(e, ValidationError) and e.errors():
            msg = str(e.errors()[0].get("msg", msg))
        raise HTTPException(status_code=400, detail=msg) from e

    try:
        cover_path = await _save_optional_image(cover_image, tmp_paths, "封面配图")
        logo_path = await _save_optional_image(logo_image, tmp_paths, "角标/Logo 图")
    except HTTPException:
        cleanup_temp_paths(tmp_paths)
        raise

    body = JobCreateBody(
        topic=topic_clean,
        audience=audience,
        slide_count=slide_count,
        template_preset=template_preset,  # type: ignore[arg-type]
        style=style,
        api_base_url=settings.deepseek_api_base,
        model=settings.deepseek_model,
        api_key=key,
    )
    return PreparedGeneration(
        body=body,
        tmp_paths=tmp_paths,
        out_path=out_path,
        cover_image_path=cover_path,
        logo_image_path=logo_path,
    )
