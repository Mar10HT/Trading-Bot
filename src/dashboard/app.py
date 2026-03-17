from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.dashboard.routes.controls import router as controls_router
from src.dashboard.routes.pnl import router as pnl_router
from src.dashboard.routes.status import router as status_router
from src.dashboard.routes.trades import router as trades_router
from src.dashboard.ws import router as ws_router

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="Trade Bot Dashboard", version="0.1.0")

    # API routes
    app.include_router(status_router, prefix="/api")
    app.include_router(trades_router, prefix="/api")
    app.include_router(pnl_router, prefix="/api")
    app.include_router(controls_router, prefix="/api")
    app.include_router(ws_router)

    # Static files (served at root, after API routes)
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
