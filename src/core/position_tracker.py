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
        self.quote_received = 0.0  # Total USDT received from sells (net of fees)
        self.total_fees = 0.0
        self.completed_cycles = 0

        # _cost_basis: cost of current remaining holdings (reduced proportionally on each sell).
        # _total_buy_cost: cumulative cost of all buys ever (never decreases).
        # realized_pnl = quote_received - (_total_buy_cost - _cost_basis)
        #               = quote_received - cost_of_what_was_sold
        self._cost_basis = 0.0
        self._total_buy_cost = 0.0

    def record_fill(self, side: OrderSide, price: float, amount: float, fee: float) -> None:
        """Record a filled order and update position tracking."""
        if side == OrderSide.BUY:
            cost = amount * price + fee
            self.base_holdings += amount
            self._cost_basis += cost
            self._total_buy_cost += cost
        elif side == OrderSide.SELL:
            if self.base_holdings > 0:
                # Reduce cost basis proportionally to the fraction sold
                fraction_sold = amount / self.base_holdings
                self._cost_basis -= self._cost_basis * fraction_sold
            self.base_holdings -= amount
            self.quote_received += amount * price - fee
            self.completed_cycles += 1

        self.total_fees += fee

    @property
    def realized_pnl(self) -> float:
        """P&L from completed buy+sell cycles only (fees included)."""
        cost_of_sold = self._total_buy_cost - self._cost_basis
        return self.quote_received - cost_of_sold

    def unrealized_pnl(self, current_price: float) -> float:
        """P&L from unsold holdings valued at current market price."""
        if self.base_holdings <= 0:
            return 0.0
        market_value = self.base_holdings * current_price
        return market_value - self._cost_basis

    def total_pnl(self, current_price: float) -> float:
        """Total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl(current_price)

    def get_summary(self, current_price: float) -> dict:
        """Return a summary of the position."""
        return {
            "pair": self.pair,
            "base_holdings": self.base_holdings,
            "cost_basis": round(self._cost_basis, 6),
            "quote_received": self.quote_received,
            "realized_pnl": round(self.realized_pnl, 6),
            "unrealized_pnl": round(self.unrealized_pnl(current_price), 6),
            "total_pnl": round(self.total_pnl(current_price), 6),
            "total_fees": round(self.total_fees, 6),
            "completed_cycles": self.completed_cycles,
        }
