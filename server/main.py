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

# Serve local assets for interactive viewport (loop 08 parity gate)
_LOCAL_ASSET_DIR = Path(r"E:\asset\AK")
if _LOCAL_ASSET_DIR.exists():
    from fastapi.staticfiles import StaticFiles as _SF
    app.mount("/local-assets", _SF(directory=_LOCAL_ASSET_DIR), name="local_assets")
