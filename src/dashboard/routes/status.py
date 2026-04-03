from fastapi import APIRouter, Depends

from src.dashboard import state
from src.dashboard.deps import require_api_key

router = APIRouter(tags=["status"], dependencies=[Depends(require_api_key)])


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
