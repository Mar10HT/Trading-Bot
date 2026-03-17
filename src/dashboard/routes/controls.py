from fastapi import APIRouter

from src.dashboard import state

router = APIRouter(tags=["controls"])


@router.post("/controls/stop")
async def stop_bot():
    """Gracefully stop all strategies."""
    if state.manager:
        await state.manager.stop_all()
        return {"status": "stopped"}
    return {"status": "not_running"}


@router.post("/controls/kill")
async def kill_bot():
    """Emergency kill switch - cancel all orders and stop."""
    if state.manager:
        for strategy in state.manager.strategies.values():
            strategy.risk_manager.activate_kill_switch("Dashboard kill switch")
        await state.manager.stop_all()
        return {"status": "killed"}
    return {"status": "not_running"}
