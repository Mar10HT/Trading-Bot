import asyncio
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.dashboard import state
from src.utils.config import EnvSettings

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str | None = Query(default=None)):
    """WebSocket endpoint for live status updates.

    Pass ?token=<DASHBOARD_API_KEY> when authentication is enabled.
    """
    settings = EnvSettings()
    if settings.dashboard_api_key and token != settings.dashboard_api_key:
        await ws.close(code=1008)  # Policy violation
        return

    await ws.accept()

    try:
        while True:
            data = _get_live_data()
            await ws.send_json(data)
            await asyncio.sleep(5)
    except (WebSocketDisconnect, Exception):
        pass


def _get_live_data() -> dict:
    """Build live data payload for WebSocket clients."""
    if not state.manager:
        return {"running": False, "strategies": []}

    strategies = []
    for s in state.manager.strategies.values():
        strategies.append({
            "pair": s.pair,
            "running": s.is_running,
            "price": s.current_price,
            "active_orders": s.order_manager.active_order_count,
            "pnl": s.position_tracker.get_summary(s.current_price),
            "grid": s.engine.get_grid_summary(),
        })

    return {"running": True, "strategies": strategies}
