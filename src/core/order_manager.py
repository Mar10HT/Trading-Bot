import structlog

from src.exchange.base import AbstractExchange
from src.storage.database import Database
from src.storage.models import GridAction, Order, OrderSide, OrderStatus, Trade

logger = structlog.get_logger()


class OrderManager:
    """Bridges GridEngine actions to Exchange calls.

    Tracks placed orders and detects fills by comparing
    open orders with previously tracked ones.
    """

    def __init__(self, exchange: AbstractExchange, db: Database, pair: str):
        self.exchange = exchange
        self.db = db
        self.pair = pair

        # {order_id: grid_level}
        self._tracked_orders: dict[str, int] = {}
        # {order_id: Order} - snapshot of placed orders
        self._order_snapshots: dict[str, Order] = {}

    async def place_order(self, action: GridAction) -> Order | None:
        """Place an order from a GridAction and track it."""
        try:
            order = await self.exchange.create_limit_order(
                self.pair, action.side, action.amount, action.price
            )
            order.grid_level = action.grid_level
            self._tracked_orders[order.id] = action.grid_level
            self._order_snapshots[order.id] = order
            await self.db.save_order(order)

            logger.info(
                "order_placed",
                pair=self.pair,
                side=action.side.value,
                price=action.price,
                amount=action.amount,
                level=action.grid_level,
                order_id=order.id,
            )
            return order
        except ValueError as e:
            logger.warning(
                "order_place_failed",
                pair=self.pair,
                error=str(e),
                level=action.grid_level,
            )
            return None

    async def check_fills(self) -> list[tuple[int, OrderSide, Order]]:
        """Check for filled orders.

        Returns list of (grid_level, side, filled_order) tuples.
        """
        open_orders = await self.exchange.fetch_open_orders(self.pair)
        open_ids = {o.id for o in open_orders}

        filled: list[tuple[int, OrderSide, Order]] = []

        for order_id, level in list(self._tracked_orders.items()):
            if order_id not in open_ids:
                # Order is no longer open → it was filled
                snapshot = self._order_snapshots.pop(order_id, None)
                del self._tracked_orders[order_id]

                if snapshot:
                    snapshot.status = OrderStatus.FILLED
                    await self.db.save_order(snapshot)

                    # Record trade
                    fee = snapshot.amount * snapshot.price * 0.001
                    trade = Trade(
                        pair=self.pair,
                        side=snapshot.side,
                        price=snapshot.price,
                        amount=snapshot.amount,
                        fee=fee,
                        grid_level=level,
                    )
                    await self.db.save_trade(trade)

                    filled.append((level, snapshot.side, snapshot))
                    logger.info(
                        "order_filled",
                        pair=self.pair,
                        side=snapshot.side.value,
                        price=snapshot.price,
                        amount=snapshot.amount,
                        level=level,
                    )

        return filled

    async def cancel_all(self):
        """Cancel all tracked orders."""
        for order_id in list(self._tracked_orders.keys()):
            await self.exchange.cancel_order(order_id, self.pair)
            self._tracked_orders.pop(order_id, None)
            self._order_snapshots.pop(order_id, None)
        logger.info("all_orders_cancelled", pair=self.pair)

    @property
    def active_order_count(self) -> int:
        return len(self._tracked_orders)
