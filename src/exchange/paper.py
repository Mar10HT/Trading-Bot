import uuid
from datetime import datetime

import ccxt.async_support as ccxt
import structlog

from src.exchange.base import AbstractExchange
from src.storage.models import Balance, Order, OrderSide, OrderStatus

logger = structlog.get_logger()


class PaperExchange(AbstractExchange):
    """Simulated exchange for paper trading.

    Uses real Binance public API for price data, but simulates order fills locally.
    No API keys required.
    """

    def __init__(self, initial_balance: float = 50.0, fee_rate: float = 0.001):
        self.fee_rate = fee_rate
        self._exchange = ccxt.binance({"enableRateLimit": True})

        # Simulated balances: {asset: Balance}
        self._balances: dict[str, Balance] = {
            "USDT": Balance(asset="USDT", free=initial_balance, total=initial_balance),
        }

        # Open orders: {order_id: Order}
        self._open_orders: dict[str, Order] = {}

        # Last known prices per pair
        self._last_prices: dict[str, float] = {}

    async def close(self):
        """Close the ccxt exchange connection."""
        await self._exchange.close()

    async def fetch_ticker(self, pair: str) -> dict:
        """Fetch real ticker from Binance public API."""
        ticker = await self._exchange.fetch_ticker(pair)
        self._last_prices[pair] = ticker["last"]

        # Check if any open orders should be filled
        await self._check_fills(pair, ticker["last"])

        return {
            "last": ticker["last"],
            "bid": ticker["bid"],
            "ask": ticker["ask"],
            "timestamp": ticker["timestamp"],
        }

    async def create_limit_order(
        self, pair: str, side: OrderSide, amount: float, price: float
    ) -> Order:
        """Simulate placing a limit order."""
        order_id = f"paper_{uuid.uuid4().hex[:12]}"

        # Validate balance
        if side == OrderSide.BUY:
            required = amount * price * (1 + self.fee_rate)
            usdt_balance = self._balances.get("USDT", Balance(asset="USDT"))
            if usdt_balance.free < required:
                raise ValueError(
                    f"Insufficient USDT balance: {usdt_balance.free:.2f} < {required:.2f}"
                )
            # Lock the USDT
            usdt_balance.free -= required
            usdt_balance.locked += required
        else:
            base_asset = pair.split("/")[0]
            base_balance = self._balances.get(base_asset, Balance(asset=base_asset))
            if base_balance.free < amount:
                raise ValueError(
                    f"Insufficient {base_asset} balance: {base_balance.free:.8f} < {amount:.8f}"
                )
            base_balance.free -= amount
            base_balance.locked += amount

        order = Order(
            id=order_id,
            pair=pair,
            side=side,
            price=price,
            amount=amount,
            status=OrderStatus.OPEN,
            created_at=datetime.utcnow(),
        )
        self._open_orders[order_id] = order

        logger.debug(
            "paper_order_placed",
            order_id=order_id,
            pair=pair,
            side=side.value,
            price=price,
            amount=amount,
        )
        return order

    async def cancel_order(self, order_id: str, pair: str) -> bool:
        """Cancel a simulated order and unlock funds."""
        order = self._open_orders.pop(order_id, None)
        if not order:
            return False

        # Unlock the funds
        if order.side == OrderSide.BUY:
            required = order.amount * order.price * (1 + self.fee_rate)
            usdt = self._balances.get("USDT", Balance(asset="USDT"))
            usdt.locked -= required
            usdt.free += required
        else:
            base_asset = pair.split("/")[0]
            base = self._balances.get(base_asset, Balance(asset=base_asset))
            base.locked -= order.amount
            base.free += order.amount

        order.status = OrderStatus.CANCELLED
        return True

    async def fetch_open_orders(self, pair: str) -> list[Order]:
        """Return simulated open orders for a pair."""
        return [o for o in self._open_orders.values() if o.pair == pair]

    async def fetch_balance(self) -> dict[str, Balance]:
        """Return simulated balances."""
        # Update totals
        for b in self._balances.values():
            b.total = b.free + b.locked
        return dict(self._balances)

    async def get_min_order_amount(self, pair: str) -> float:
        """Simulate Binance minimum order amounts."""
        minimums = {
            "BTC/USDT": 0.00001,
            "ETH/USDT": 0.0001,
        }
        return minimums.get(pair, 0.001)

    async def get_min_notional(self, pair: str) -> float:
        """Simulate Binance minimum notional value."""
        return 10.0  # Binance typical MIN_NOTIONAL

    async def _check_fills(self, pair: str, current_price: float):
        """Check if any open orders should be filled at the current price."""
        filled_ids = []

        for order_id, order in self._open_orders.items():
            if order.pair != pair:
                continue

            should_fill = False
            if order.side == OrderSide.BUY and current_price <= order.price:
                should_fill = True
            elif order.side == OrderSide.SELL and current_price >= order.price:
                should_fill = True

            if should_fill:
                await self._fill_order(order)
                filled_ids.append(order_id)

        for oid in filled_ids:
            del self._open_orders[oid]

    async def _fill_order(self, order: Order):
        """Simulate filling an order."""
        fee_amount = order.amount * order.price * self.fee_rate
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.utcnow()
        order.fee = fee_amount

        base_asset = order.pair.split("/")[0]

        if order.side == OrderSide.BUY:
            # Unlock USDT, add base asset
            cost = order.amount * order.price * (1 + self.fee_rate)
            usdt = self._balances.get("USDT", Balance(asset="USDT"))
            usdt.locked -= cost

            if base_asset not in self._balances:
                self._balances[base_asset] = Balance(asset=base_asset)
            self._balances[base_asset].free += order.amount

        elif order.side == OrderSide.SELL:
            # Unlock base asset, add USDT
            base = self._balances.get(base_asset, Balance(asset=base_asset))
            base.locked -= order.amount

            revenue = order.amount * order.price * (1 - self.fee_rate)
            if "USDT" not in self._balances:
                self._balances["USDT"] = Balance(asset="USDT")
            self._balances["USDT"].free += revenue

        logger.info(
            "paper_order_filled",
            order_id=order.id,
            pair=order.pair,
            side=order.side.value,
            price=order.price,
            amount=order.amount,
            fee=fee_amount,
        )

    # Callbacks for filled orders (set by strategy)
    _on_fill_callbacks: list = []

    def on_fill(self, callback):
        """Register a callback for when an order is filled."""
        self._on_fill_callbacks.append(callback)

    def get_filled_orders_since(self, pair: str) -> list[Order]:
        """Get orders that were recently filled. Used by strategy polling."""
        # This is tracked by the strategy layer checking order status changes
        return []
