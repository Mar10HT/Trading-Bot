from fastapi import APIRouter

from src.dashboard import state

router = APIRouter(tags=["pnl"])


@router.get("/pnl")
async def get_pnl():
    """Get P&L summary across all pairs."""
    if not state.manager:
        return {"total_pnl": 0, "pairs": []}

    pairs_pnl = []
    total_realized = 0.0
    total_unrealized = 0.0
    total_fees = 0.0

    for strategy in state.manager.strategies.values():
        summary = strategy.position_tracker.get_summary(strategy.current_price)
        pairs_pnl.append(summary)
        total_realized += summary["realized_pnl"]
        total_unrealized += summary["unrealized_pnl"]
        total_fees += summary["total_fees"]

    return {
        "total_realized_pnl": round(total_realized, 6),
        "total_unrealized_pnl": round(total_unrealized, 6),
        "total_pnl": round(total_realized + total_unrealized, 6),
        "total_fees": round(total_fees, 6),
        "pairs": pairs_pnl,
    }
