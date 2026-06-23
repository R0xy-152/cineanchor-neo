from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server.routes.assets import router as assets_router
from server.routes.render import router as render_router

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "apps" / "web"

app = FastAPI(title="CineAnchor V0.1 Local API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(assets_router)
app.include_router(render_router)

if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")
