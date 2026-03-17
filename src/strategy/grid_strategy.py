import asyncio

import structlog

from src.core.grid_engine import GridEngine
from src.core.order_manager import OrderManager
from src.core.position_tracker import PositionTracker
from src.core.risk_manager import RiskManager
from src.exchange.base import AbstractExchange
from src.storage.database import Database
from src.utils.config import PairConfig

logger = structlog.get_logger()


class GridStrategy:
    """Orchestrates the grid trading loop for a single pair.

    Ties together GridEngine, OrderManager, PositionTracker,
    and RiskManager into the main trading cycle.
    """

    def __init__(
        self,
        pair_config: PairConfig,
        exchange: AbstractExchange,
        risk_manager: RiskManager,
        db: Database,
        fee_rate: float = 0.001,
        poll_interval: int = 10,
    ):
        self.pair = pair_config.pair
        self.exchange = exchange
        self.risk_manager = risk_manager
        self.db = db
        self.poll_interval = poll_interval
        self._running = False

        self.engine = GridEngine(
            pair=pair_config.pair,
            lower_price=pair_config.lower_price,
            upper_price=pair_config.upper_price,
            num_grids=pair_config.num_grids,
            investment=pair_config.investment,
            fee_rate=fee_rate,
        )

        self.order_manager = OrderManager(exchange, db, pair_config.pair)

        self.position_tracker = PositionTracker(
            pair=pair_config.pair,
            initial_investment=pair_config.investment,
            db=db,
        )

        self.current_price = 0.0
        self._tick_count = 0

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self):
        """Initialize the grid and start the trading loop."""
        self._running = True

        # Get current price
        ticker = await self.exchange.fetch_ticker(self.pair)
        self.current_price = ticker["last"]

        logger.info("strategy_starting", pair=self.pair, price=self.current_price)

        # Initialize grid
        actions = self.engine.initialize(self.current_price)
        summary = self.engine.get_grid_summary()
        logger.info("grid_configured", **summary)

        # Place initial orders
        placed = 0
        for action in actions:
            valid, reason = self.risk_manager.check_order_valid(action.amount, action.price)
            if not valid:
                logger.warning("initial_order_skipped", reason=reason, level=action.grid_level)
                continue

            order = await self.order_manager.place_order(action)
            if order:
                placed += 1

        logger.info("initial_orders_placed", pair=self.pair, count=placed, total=len(actions))

        # Main loop
        while self._running and not self.risk_manager.is_killed:
            await asyncio.sleep(self.poll_interval)
            await self._tick()

    async def stop(self):
        """Gracefully stop the strategy."""
        self._running = False
        await self.order_manager.cancel_all()
        logger.info("strategy_stopped", pair=self.pair)

    async def _tick(self):
        """Single iteration of the trading loop."""
        self._tick_count += 1

        try:
            # Update price
            ticker = await self.exchange.fetch_ticker(self.pair)
            self.current_price = ticker["last"]

            # Check for filled orders
            fills = await self.order_manager.check_fills()

            for level, side, order in fills:
                # Update position tracker
                fee = order.amount * order.price * 0.001
                self.position_tracker.record_fill(side, order.price, order.amount, fee)

                # Get next grid action
                next_action = self.engine.on_order_filled(level, side)
                if next_action:
                    valid, reason = self.risk_manager.check_order_valid(
                        next_action.amount, next_action.price
                    )
                    if valid:
                        await self.order_manager.place_order(next_action)
                    else:
                        logger.warning("next_order_skipped", reason=reason)

            # Check drawdown periodically (every 6 ticks = ~1 min at 10s interval)
            if self._tick_count % 6 == 0:
                await self._check_risk()

            # Save state periodically (every 30 ticks = ~5 min)
            if self._tick_count % 30 == 0:
                await self.db.save_grid_state(self.pair, self.engine.get_state())
                pnl = self.position_tracker.get_summary(self.current_price)
                logger.info("periodic_status", price=self.current_price, **pnl)

        except Exception as e:
            logger.error("tick_error", pair=self.pair, error=str(e))

    async def _check_risk(self):
        """Check drawdown and trigger kill switch if needed."""
        balances = await self.exchange.fetch_balance()
        equity = 0.0

        # Sum up USDT balance
        usdt = balances.get("USDT")
        if usdt:
            equity += usdt.total

        # Add market value of base holdings
        base_asset = self.pair.split("/")[0]
        base = balances.get(base_asset)
        if base and base.total > 0:
            equity += base.total * self.current_price

        safe, reason = self.risk_manager.check_drawdown(equity)
        if not safe:
            logger.critical("risk_limit_hit", pair=self.pair, reason=reason)
            await self.stop()

    def get_status(self) -> dict:
        """Return current strategy status."""
        return {
            "pair": self.pair,
            "running": self._running,
            "current_price": self.current_price,
            "active_orders": self.order_manager.active_order_count,
            "grid": self.engine.get_grid_summary(),
            "position": self.position_tracker.get_summary(self.current_price),
        }
