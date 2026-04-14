from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes_simple import router as simple_router
from app.settings import get_settings
from app.web.routes import router as web_router

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(simple_router, prefix="/api/simple")
app.include_router(web_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
