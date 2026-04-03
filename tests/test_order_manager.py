"""Tests for OrderManager — focuses on fill detection and cancelled order handling."""
import pytest

from src.core.order_manager import OrderManager
from src.storage.models import GridAction, Order, OrderSide, OrderStatus


class FakeExchange:
    """Minimal exchange stub for testing OrderManager in isolation."""

    def __init__(self):
        self._open_orders: dict[str, Order] = {}
        self._counter = 0

    async def create_limit_order(
        self, pair: str, side: OrderSide, amount: float, price: float
    ) -> Order:
        self._counter += 1
        order = Order(
            id=f"fake_{self._counter}",
            pair=pair,
            side=side,
            price=price,
            amount=amount,
            status=OrderStatus.OPEN,
        )
        self._open_orders[order.id] = order
        return order

    async def fetch_open_orders(self, pair: str) -> list[Order]:
        return [o for o in self._open_orders.values() if o.pair == pair]

    async def cancel_order(self, order_id: str, pair: str) -> bool:
        order = self._open_orders.pop(order_id, None)
        if order:
            order.status = OrderStatus.CANCELLED
            return True
        return False

    def simulate_fill(self, order_id: str) -> None:
        """Remove from open orders to simulate exchange fill."""
        self._open_orders.pop(order_id, None)


class FakeDatabase:
    """No-op database stub."""

    def __init__(self):
        self.saved_orders: list[Order] = []
        self.saved_trades = []

    async def save_order(self, order: Order) -> None:
        self.saved_orders.append(order)

    async def save_trade(self, trade) -> None:
        self.saved_trades.append(trade)


def make_manager(pair: str = "BTC/USDT") -> tuple[OrderManager, FakeExchange, FakeDatabase]:
    exchange = FakeExchange()
    db = FakeDatabase()
    manager = OrderManager(exchange=exchange, db=db, pair=pair, fee_rate=0.001)
    return manager, exchange, db


def make_action(side: OrderSide, price: float = 65000, level: int = 2) -> GridAction:
    return GridAction(side=side, price=price, amount=0.001, grid_level=level)


class TestPlaceOrder:
    @pytest.mark.asyncio
    async def test_place_order_tracks_it(self):
        manager, exchange, _ = make_manager()
        action = make_action(OrderSide.BUY)
        order = await manager.place_order(action)
        assert order is not None
        assert manager.active_order_count == 1

    @pytest.mark.asyncio
    async def test_place_multiple_orders(self):
        manager, _, _ = make_manager()
        await manager.place_order(make_action(OrderSide.BUY, price=64000, level=2))
        await manager.place_order(make_action(OrderSide.SELL, price=66000, level=3))
        assert manager.active_order_count == 2


class TestCheckFills:
    @pytest.mark.asyncio
    async def test_filled_order_is_detected(self):
        manager, exchange, db = make_manager()
        action = make_action(OrderSide.BUY, level=2)
        order = await manager.place_order(action)

        # Simulate exchange fill (remove from open orders)
        exchange.simulate_fill(order.id)

        fills = await manager.check_fills()
        assert len(fills) == 1
        level, side, filled = fills[0]
        assert level == 2
        assert side == OrderSide.BUY

    @pytest.mark.asyncio
    async def test_open_order_not_reported_as_filled(self):
        manager, exchange, _ = make_manager()
        await manager.place_order(make_action(OrderSide.BUY, level=2))
        # Order is still open — check_fills should return nothing
        fills = await manager.check_fills()
        assert len(fills) == 0

    @pytest.mark.asyncio
    async def test_cancelled_order_not_treated_as_filled(self):
        """Regression: previously a cancelled order was counted as a fill."""
        manager, exchange, db = make_manager()
        action = make_action(OrderSide.BUY, level=2)
        order = await manager.place_order(action)

        # Cancel the order through the exchange (sets status=CANCELLED on the shared object)
        await exchange.cancel_order(order.id, "BTC/USDT")

        fills = await manager.check_fills()
        assert len(fills) == 0, (
            "Cancelled order should not be reported as filled"
        )
        assert len(db.saved_trades) == 0

    @pytest.mark.asyncio
    async def test_fill_saves_trade_to_db(self):
        manager, exchange, db = make_manager()
        order = await manager.place_order(make_action(OrderSide.BUY, level=2))
        exchange.simulate_fill(order.id)
        await manager.check_fills()
        assert len(db.saved_trades) == 1


class TestCancelAll:
    @pytest.mark.asyncio
    async def test_cancel_all_clears_tracked_orders(self):
        manager, exchange, _ = make_manager()
        await manager.place_order(make_action(OrderSide.BUY, price=64000, level=2))
        await manager.place_order(make_action(OrderSide.SELL, price=66000, level=3))
        assert manager.active_order_count == 2

        await manager.cancel_all()
        assert manager.active_order_count == 0

    @pytest.mark.asyncio
    async def test_cancel_all_continues_if_one_fails(self):
        """cancel_all must not stop on the first failed cancellation."""
        manager, exchange, _ = make_manager()
        o1 = await manager.place_order(make_action(OrderSide.BUY, price=64000, level=2))
        o2 = await manager.place_order(make_action(OrderSide.SELL, price=66000, level=3))

        # Manually remove first order from exchange to simulate it already being gone
        exchange._open_orders.pop(o1.id, None)

        # Should not raise and should clear both from tracking
        await manager.cancel_all()
        assert manager.active_order_count == 0
