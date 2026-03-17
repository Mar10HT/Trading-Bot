import structlog

from src.storage.models import GridAction, OrderSide

logger = structlog.get_logger()


class GridEngine:
    """Core grid trading logic.

    Calculates evenly spaced price levels and determines buy/sell actions
    when price crosses grid levels.

    Grid mechanic:
    - Levels below current price → buy orders
    - Levels above current price → sell orders
    - When a buy fills at level N → place sell at level N+1
    - When a sell fills at level N → place buy at level N-1
    """

    def __init__(
        self,
        pair: str,
        lower_price: float,
        upper_price: float,
        num_grids: int,
        investment: float,
        fee_rate: float = 0.001,
    ):
        self.pair = pair
        self.lower_price = lower_price
        self.upper_price = upper_price
        self.num_grids = num_grids
        self.investment = investment
        self.fee_rate = fee_rate

        self.levels = self._calculate_levels()
        self.order_amount_per_level = self._calculate_amount_per_level()

        # Track which levels have active orders: {level_index: "buy" | "sell" | None}
        self.level_states: dict[int, str | None] = {}
        self._initialized = False

    def _calculate_levels(self) -> list[float]:
        """Calculate evenly spaced grid levels between lower and upper price."""
        step = (self.upper_price - self.lower_price) / self.num_grids
        return [round(self.lower_price + i * step, 8) for i in range(self.num_grids + 1)]

    def _calculate_amount_per_level(self) -> float:
        """Calculate the base asset amount for each grid level order.

        Uses the midpoint price to estimate a uniform order size.
        Reserves a portion for fees.
        """
        usable_investment = self.investment * (1 - self.fee_rate * 2 * self.num_grids)
        mid_price = (self.lower_price + self.upper_price) / 2
        amount = usable_investment / self.num_grids / mid_price
        return max(amount, 0)

    def initialize(self, current_price: float) -> list[GridAction]:
        """Initialize grid based on current price.

        Places buy orders below current price and sell orders above.
        Returns list of initial actions to execute.
        """
        actions: list[GridAction] = []
        self._initialized = True

        for i, level in enumerate(self.levels):
            if level < current_price:
                # Place buy order at this level
                self.level_states[i] = "buy"
                actions.append(GridAction(
                    side=OrderSide.BUY,
                    price=level,
                    amount=self.order_amount_per_level,
                    grid_level=i,
                ))
            elif level > current_price:
                # Place sell order at this level
                self.level_states[i] = "sell"
                actions.append(GridAction(
                    side=OrderSide.SELL,
                    price=level,
                    amount=self.order_amount_per_level,
                    grid_level=i,
                ))
            else:
                # Price is exactly on a level, skip it
                self.level_states[i] = None

        logger.info(
            "grid_initialized",
            pair=self.pair,
            levels=len(self.levels),
            buys=sum(1 for s in self.level_states.values() if s == "buy"),
            sells=sum(1 for s in self.level_states.values() if s == "sell"),
            amount_per_level=self.order_amount_per_level,
        )
        return actions

    def on_order_filled(self, grid_level: int, side: OrderSide) -> GridAction | None:
        """Handle a filled order and return the next grid action.

        When a buy fills at level N → place sell at level N+1
        When a sell fills at level N → place buy at level N-1
        """
        if side == OrderSide.BUY:
            # Buy filled at level N → place sell at level N+1
            next_level = grid_level + 1
            if next_level < len(self.levels):
                self.level_states[grid_level] = None
                self.level_states[next_level] = "sell"
                logger.info(
                    "grid_cycle",
                    pair=self.pair,
                    filled_side="buy",
                    filled_level=grid_level,
                    next_side="sell",
                    next_level=next_level,
                    next_price=self.levels[next_level],
                )
                return GridAction(
                    side=OrderSide.SELL,
                    price=self.levels[next_level],
                    amount=self.order_amount_per_level,
                    grid_level=next_level,
                )
        elif side == OrderSide.SELL:
            # Sell filled at level N → place buy at level N-1
            next_level = grid_level - 1
            if next_level >= 0:
                self.level_states[grid_level] = None
                self.level_states[next_level] = "buy"
                logger.info(
                    "grid_cycle",
                    pair=self.pair,
                    filled_side="sell",
                    filled_level=grid_level,
                    next_side="buy",
                    next_level=next_level,
                    next_price=self.levels[next_level],
                )
                return GridAction(
                    side=OrderSide.BUY,
                    price=self.levels[next_level],
                    amount=self.order_amount_per_level,
                    grid_level=next_level,
                )

        return None

    def get_profit_per_grid(self) -> float:
        """Calculate expected profit per completed grid cycle (buy+sell) after fees."""
        if len(self.levels) < 2:
            return 0.0
        grid_spacing = self.levels[1] - self.levels[0]
        mid_price = (self.lower_price + self.upper_price) / 2
        gross_profit = (grid_spacing / mid_price) * self.order_amount_per_level * mid_price
        fees = 2 * self.fee_rate * self.order_amount_per_level * mid_price
        return gross_profit - fees

    def get_state(self) -> dict:
        """Return serializable grid state for persistence."""
        return {
            "pair": self.pair,
            "lower_price": self.lower_price,
            "upper_price": self.upper_price,
            "num_grids": self.num_grids,
            "investment": self.investment,
            "levels": self.levels,
            "level_states": {str(k): v for k, v in self.level_states.items()},
            "order_amount_per_level": self.order_amount_per_level,
            "initialized": self._initialized,
        }

    def get_grid_summary(self) -> dict:
        """Return a human-readable summary of the grid configuration."""
        return {
            "pair": self.pair,
            "range": f"{self.lower_price} - {self.upper_price}",
            "num_levels": len(self.levels),
            "grid_spacing": round(self.levels[1] - self.levels[0], 2) if len(self.levels) > 1 else 0,
            "amount_per_level": self.order_amount_per_level,
            "profit_per_cycle": round(self.get_profit_per_grid(), 6),
            "investment": self.investment,
            "active_buys": sum(1 for s in self.level_states.values() if s == "buy"),
            "active_sells": sum(1 for s in self.level_states.values() if s == "sell"),
        }
