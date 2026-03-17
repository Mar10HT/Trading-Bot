from fastapi import APIRouter

from src.dashboard import state

router = APIRouter(tags=["status"])


@router.get("/status")
async def get_status():
    """Get bot status and all active grid strategies."""
    if not state.manager:
        return {"running": False, "mode": state.bot_mode, "strategies": []}

    strategies = state.manager.get_all_status()
    return {
        "running": True,
        "mode": state.bot_mode,
        "strategies": strategies,
    }
