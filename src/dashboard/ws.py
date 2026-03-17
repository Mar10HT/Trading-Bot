import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.dashboard import state

router = APIRouter()

# Connected WebSocket clients
_clients: set[WebSocket] = set()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for live status updates."""
    await ws.accept()
    _clients.add(ws)

    try:
        while True:
            # Send status update every 5 seconds
            data = _get_live_data()
            await ws.send_json(data)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        _clients.discard(ws)
    except Exception:
        _clients.discard(ws)


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
