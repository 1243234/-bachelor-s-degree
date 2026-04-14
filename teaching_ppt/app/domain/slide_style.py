"""用户个性化：整体配色 + 适量可选标题/正文字号与颜色（均为预设项，非自由 RGB）。"""

from __future__ import annotations

from dataclasses import replace

from pydantic import BaseModel, Field

# ----- 整体背景配色（与幻灯片风格 theme 二选一叠加逻辑由 merge 处理）-----
STYLE_PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
    "crisp": {
        "cover_bg": (255, 255, 255),
        "content_bg": (248, 250, 252),
        "cover_title": (15, 23, 42),
        "cover_sub": (100, 116, 139),
        "content_title": (30, 41, 59),
        "body": (71, 85, 105),
    },
    "business_blue": {
        "cover_bg": (239, 246, 255),
        "content_bg": (241, 248, 255),
        "cover_title": (30, 64, 175),
        "cover_sub": (59, 130, 246),
        "content_title": (29, 78, 216),
        "body": (51, 65, 85),
    },
    "nature_green": {
        "cover_bg": (240, 253, 244),
        "content_bg": (236, 253, 245),
        "cover_title": (22, 101, 52),
        "cover_sub": (5, 150, 105),
        "content_title": (21, 128, 61),
        "body": (55, 65, 81),
    },
    "warm_coral": {
        "cover_bg": (255, 247, 237),
        "content_bg": (255, 251, 245),
        "cover_title": (185, 28, 28),
        "cover_sub": (217, 119, 6),
        "content_title": (154, 52, 18),
        "body": (67, 20, 7),
    },
    "slate": {
        "cover_bg": (248, 250, 252),
        "content_bg": (241, 245, 249),
        "cover_title": (51, 65, 85),
        "cover_sub": (100, 116, 139),
        "content_title": (51, 65, 85),
        "body": (71, 85, 105),
    },
    "ink_dark": {
        "cover_bg": (15, 23, 42),
        "content_bg": (30, 41, 59),
        "cover_title": (248, 250, 252),
        "cover_sub": (148, 163, 184),
        "content_title": (226, 232, 240),
        "body": (203, 213, 225),
    },
}

PALETTE_LABELS: dict[str, str] = {
    "theme": "跟随所选幻灯片主题",
    "crisp": "极简白灰",
    "business_blue": "商务蓝",
    "nature_green": "自然绿",
    "warm_coral": "暖色活力",
    "slate": "雅灰",
    "ink_dark": "深色沉浸",
}

VALID_PALETTE_IDS: frozenset[str] = frozenset({"theme", *STYLE_PALETTES.keys()})

# ----- 标题字号：相对当前视觉基准的增量（磅）-----
TITLE_SIZE_DELTA: dict[str, int] = {
    "theme": 0,
    "compact": -6,
    "enlarged": 4,
    "prominent": 8,
}
TITLE_SIZE_LABELS: dict[str, str] = {
    "theme": "跟随主题默认",
    "compact": "稍小",
    "enlarged": "稍大",
    "prominent": "更大",
}
VALID_TITLE_SIZES: frozenset[str] = frozenset(TITLE_SIZE_DELTA.keys())

# ----- 正文/副标题字号增量 -----
BODY_SIZE_DELTA: dict[str, int] = {
    "theme": 0,
    "compact": -3,
    "enlarged": 3,
    "prominent": 6,
}
BODY_SIZE_LABELS: dict[str, str] = {
    "theme": "跟随主题默认",
    "compact": "稍小",
    "enlarged": "稍大",
    "prominent": "更大",
}
VALID_BODY_SIZES: frozenset[str] = frozenset(BODY_SIZE_DELTA.keys())

# ----- 标题字色（封面主标题 + 内容页标题同色）-----
TITLE_COLOR_CHOICES: dict[str, tuple[int, int, int]] = {
    "charcoal": (31, 41, 55),
    "navy": (30, 58, 95),
    "forest": (22, 101, 52),
    "wine": (127, 29, 29),
    "terracotta": (180, 83, 9),
    "violet": (91, 33, 182),
    "snow": (248, 250, 252),
}
TITLE_COLOR_LABELS: dict[str, str] = {
    "charcoal": "炭灰",
    "navy": "藏青",
    "forest": "森绿",
    "wine": "酒红",
    "terracotta": "陶土橙",
    "violet": "紫罗兰",
    "snow": "雪白字（深色底用）",
}
VALID_TITLE_COLORS: frozenset[str] = frozenset(TITLE_COLOR_CHOICES.keys())

# ----- 正文/要点色（含封面副标题）-----
BODY_COLOR_CHOICES: dict[str, tuple[int, int, int]] = {
    "slate": (71, 85, 105),
    "charcoal": (55, 65, 81),
    "navy_soft": (51, 65, 85),
    "brown": (120, 53, 15),
    "green_soft": (22, 101, 52),
    "mist": (203, 213, 225),
}
BODY_COLOR_LABELS: dict[str, str] = {
    "slate": "石板灰",
    "charcoal": "深灰",
    "navy_soft": "柔蓝灰",
    "brown": "深棕",
    "green_soft": "柔绿",
    "mist": "浅灰字（深色底用）",
}
VALID_BODY_COLORS: frozenset[str] = frozenset(BODY_COLOR_CHOICES.keys())


class SlideStyleOptions(BaseModel):
    palette: str = Field("theme", min_length=2, max_length=32)
    title_size: str = Field("theme", max_length=16)
    body_size: str = Field("theme", max_length=16)
    title_color: str = Field("theme", max_length=16)
    body_color: str = Field("theme", max_length=16)


def _hx(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def get_palette_preview_tokens() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for pid, p in STYLE_PALETTES.items():
        out[pid] = {
            "coverBg": _hx(p["cover_bg"]),
            "contentBg": _hx(p["content_bg"]),
            "coverTitle": _hx(p["cover_title"]),
            "coverSub": _hx(p["cover_sub"]),
            "contentTitle": _hx(p["content_title"]),
            "bodyText": _hx(p["body"]),
        }
    return out


def get_title_color_preview_tokens() -> dict[str, str]:
    return {k: _hx(v) for k, v in TITLE_COLOR_CHOICES.items()}


def get_body_color_preview_tokens() -> dict[str, str]:
    return {k: _hx(v) for k, v in BODY_COLOR_CHOICES.items()}


def merge_preset_with_style(base, opt: SlideStyleOptions):
    from app.domain.preset_templates import PresetVisual as PV

    if opt.palette != "theme" and opt.palette in STYLE_PALETTES:
        p = STYLE_PALETTES[opt.palette]
        vis = PV(
            cover_bg=p["cover_bg"],
            content_bg=p["content_bg"],
            cover_title_rgb=p["cover_title"],
            cover_sub_rgb=p["cover_sub"],
            content_title_rgb=p["content_title"],
            body_rgb=p["body"],
            cover_title_pt=base.cover_title_pt,
            cover_sub_pt=base.cover_sub_pt,
            content_title_pt=base.content_title_pt,
            body_pt=base.body_pt,
        )
    else:
        vis = base

    if opt.title_color != "theme" and opt.title_color in TITLE_COLOR_CHOICES:
        c = TITLE_COLOR_CHOICES[opt.title_color]
        vis = replace(vis, cover_title_rgb=c, content_title_rgb=c)

    if opt.body_color != "theme" and opt.body_color in BODY_COLOR_CHOICES:
        c = BODY_COLOR_CHOICES[opt.body_color]
        vis = replace(vis, body_rgb=c, cover_sub_rgb=c)

    td = TITLE_SIZE_DELTA.get(opt.title_size, 0)
    if td != 0:
        vis = replace(
            vis,
            cover_title_pt=max(10, min(72, vis.cover_title_pt + td)),
            content_title_pt=max(10, min(72, vis.content_title_pt + td)),
        )

    bd = BODY_SIZE_DELTA.get(opt.body_size, 0)
    if bd != 0:
        vis = replace(
            vis,
            body_pt=max(8, min(36, vis.body_pt + bd)),
            cover_sub_pt=max(8, min(48, vis.cover_sub_pt + bd)),
        )

    return vis


def style_options_from_form(
    style_palette: str | None = None,
    style_title_size: str | None = None,
    style_body_size: str | None = None,
    style_title_color: str | None = None,
    style_body_color: str | None = None,
) -> SlideStyleOptions:
    pal = (style_palette or "theme").strip().lower()
    if pal not in VALID_PALETTE_IDS:
        hint = "、".join(f"{k}（{PALETTE_LABELS[k]}）" for k in sorted(VALID_PALETTE_IDS))
        raise ValueError(f"整体配色无效，可选：{hint}")

    ts = (style_title_size or "theme").strip().lower()
    if ts not in VALID_TITLE_SIZES:
        hint = "、".join(f"{k}（{TITLE_SIZE_LABELS[k]}）" for k in sorted(VALID_TITLE_SIZES))
        raise ValueError(f"标题字号无效，可选：{hint}")

    bs = (style_body_size or "theme").strip().lower()
    if bs not in VALID_BODY_SIZES:
        hint = "、".join(f"{k}（{BODY_SIZE_LABELS[k]}）" for k in sorted(VALID_BODY_SIZES))
        raise ValueError(f"正文字号无效，可选：{hint}")

    tc = (style_title_color or "theme").strip().lower()
    if tc != "theme" and tc not in VALID_TITLE_COLORS:
        hint = "、".join(f"{k}（{TITLE_COLOR_LABELS[k]}）" for k in sorted(VALID_TITLE_COLORS))
        raise ValueError(f"标题颜色无效，可选：{hint}")

    bc = (style_body_color or "theme").strip().lower()
    if bc != "theme" and bc not in VALID_BODY_COLORS:
        hint = "、".join(f"{k}（{BODY_COLOR_LABELS[k]}）" for k in sorted(VALID_BODY_COLORS))
        raise ValueError(f"正文颜色无效，可选：{hint}")

    return SlideStyleOptions(
        palette=pal,
        title_size=ts,
        body_size=bs,
        title_color=tc,
        body_color=bc,
    )
