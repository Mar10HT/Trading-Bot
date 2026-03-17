import asyncio

import structlog

from src.core.risk_manager import RiskManager
from src.exchange.base import AbstractExchange
from src.storage.database import Database
from src.strategy.grid_strategy import GridStrategy
from src.utils.config import BotConfig

logger = structlog.get_logger()


class MultiPairManager:
    """Manages multiple GridStrategy instances running concurrently."""

    def __init__(
        self,
        config: BotConfig,
        exchange: AbstractExchange,
        risk_manager: RiskManager,
        db: Database,
    ):
        self.config = config
        self.exchange = exchange
        self.risk_manager = risk_manager
        self.db = db

        self.strategies: dict[str, GridStrategy] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    async def start_all(self):
        """Start trading strategies for all configured pairs."""
        for pair_config in self.config.pairs:
            strategy = GridStrategy(
                pair_config=pair_config,
                exchange=self.exchange,
                risk_manager=self.risk_manager,
                db=self.db,
                fee_rate=self.config.exchange.fee_rate,
                poll_interval=self.config.exchange.poll_interval_seconds,
            )
            self.strategies[pair_config.pair] = strategy

            task = asyncio.create_task(
                self._run_strategy(strategy),
                name=f"grid_{pair_config.pair}",
            )
            self._tasks[pair_config.pair] = task

        logger.info("all_strategies_started", pairs=list(self.strategies.keys()))

        # Wait for all tasks
        try:
            await asyncio.gather(*self._tasks.values())
        except asyncio.CancelledError:
            logger.info("strategies_cancelled")

    async def stop_all(self):
        """Stop all running strategies."""
        for pair, strategy in self.strategies.items():
            await strategy.stop()
        for pair, task in self._tasks.items():
            task.cancel()
        logger.info("all_strategies_stopped")

    async def _run_strategy(self, strategy: GridStrategy):
        """Wrapper to run a strategy with error handling."""
        try:
            await strategy.start()
        except asyncio.CancelledError:
            await strategy.stop()
        except Exception as e:
            logger.error("strategy_crashed", pair=strategy.pair, error=str(e))
            await strategy.stop()

    def get_all_status(self) -> list[dict]:
        """Get status of all strategies."""
        return [s.get_status() for s in self.strategies.values()]
