from typing import Literal

from pydantic import BaseModel, Field

from app.domain.slide_style import SlideStyleOptions

TemplatePreset = Literal[
    "simple",
    "cartoon",
    "academic",
    "forest",
    "ocean",
    "sunset",
    "tech",
    "elegant",
    "chalk_dark",
]


class SlideModel(BaseModel):
    title: str = Field(..., min_length=1)
    bullets: list[str] = Field(default_factory=list)
    notes: str = ""


class SlideDeckModel(BaseModel):
    slides: list[SlideModel] = Field(default_factory=list)


class JobCreateBody(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    audience: str = "大学生"
    slide_count: int = Field(8, ge=3, le=30)
    template_preset: TemplatePreset = Field(
        "simple",
        description="内置幻灯片配色主题：simple / cartoon / academic / forest / ocean / sunset / tech / elegant / chalk_dark",
    )
    style: SlideStyleOptions = Field(default_factory=SlideStyleOptions)
    api_base_url: str = "https://api.openai.com/v1"
    api_key: str = Field(..., min_length=1)
    model: str = "gpt-4o-mini"
