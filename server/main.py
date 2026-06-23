from __future__ import annotations

from fastapi import FastAPI

from server.routes.render import router as render_router


app = FastAPI(title="CineAnchor V0.1 Local API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(render_router)
