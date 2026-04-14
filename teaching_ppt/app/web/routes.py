from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter(tags=["web"])

_BASE_DIR = Path(__file__).resolve().parent.parent.parent


@router.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/minimal", status_code=307)


@router.get("/minimal")
async def minimal_ui() -> FileResponse:
    path = _BASE_DIR / "static" / "minimal.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="minimal.html not found")
    return FileResponse(path, media_type="text/html; charset=utf-8")
