import structlog

from src.storage.database import Database
from src.storage.models import OrderSide

logger = structlog.get_logger()


class PositionTracker:
    """Tracks holdings and calculates P&L for a trading pair."""

    def __init__(self, pair: str, initial_investment: float, db: Database):
        self.pair = pair
        self.initial_investment = initial_investment
        self.db = db

        self.base_asset = pair.split("/")[0]
        self.quote_asset = pair.split("/")[1]

        # Running totals
        self.base_holdings = 0.0
        self.quote_spent = 0.0  # Total USDT spent on buys
        self.quote_received = 0.0  # Total USDT received from sells
        self.total_fees = 0.0
        self.completed_cycles = 0

    def record_fill(self, side: OrderSide, price: float, amount: float, fee: float):
        """Record a filled order and update position tracking."""
        if side == OrderSide.BUY:
            self.base_holdings += amount
            self.quote_spent += amount * price + fee
        elif side == OrderSide.SELL:
            self.base_holdings -= amount
            self.quote_received += amount * price - fee
            self.completed_cycles += 1

        self.total_fees += fee

    @property
    def realized_pnl(self) -> float:
        """P&L from completed buy+sell cycles."""
        return self.quote_received - self.quote_spent

    def unrealized_pnl(self, current_price: float) -> float:
        """P&L from unsold holdings at current market price."""
        if self.base_holdings <= 0:
            return 0.0
        market_value = self.base_holdings * current_price
        # Cost basis of remaining holdings
        avg_cost = self.quote_spent / max(self.base_holdings, 1e-10) if self.quote_spent > 0 else 0
        cost_basis = self.base_holdings * avg_cost
        return market_value - cost_basis

    def total_pnl(self, current_price: float) -> float:
        """Total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl(current_price)

    def get_summary(self, current_price: float) -> dict:
        """Return a summary of the position."""
        return {
            "pair": self.pair,
            "base_holdings": self.base_holdings,
            "quote_spent": self.quote_spent,
            "quote_received": self.quote_received,
            "realized_pnl": round(self.realized_pnl, 6),
            "unrealized_pnl": round(self.unrealized_pnl(current_price), 6),
            "total_pnl": round(self.total_pnl(current_price), 6),
            "total_fees": round(self.total_fees, 6),
            "completed_cycles": self.completed_cycles,
        }
