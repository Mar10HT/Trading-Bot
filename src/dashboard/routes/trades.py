from fastapi import APIRouter, Query

from src.dashboard import state

router = APIRouter(tags=["trades"])


@router.get("/trades")
async def get_trades(pair: str | None = None, limit: int = Query(default=50, le=500)):
    """Get trade history."""
    if not state.db:
        return {"trades": []}

    trades = await state.db.get_trades(pair=pair, limit=limit)
    return {
        "trades": [
            {
                "id": t.id,
                "pair": t.pair,
                "side": t.side.value,
                "price": t.price,
                "amount": t.amount,
                "fee": t.fee,
                "realized_pnl": t.realized_pnl,
                "grid_level": t.grid_level,
                "timestamp": t.timestamp.isoformat(),
            }
            for t in trades
        ]
    }
