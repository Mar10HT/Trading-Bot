from abc import ABC, abstractmethod

from src.storage.models import Balance, Order, OrderSide


class AbstractExchange(ABC):
    """Abstract exchange interface.

    All exchange implementations (paper, testnet, live) implement this interface.
    The trading engine never knows which implementation is running.
    """

    @abstractmethod
    async def fetch_ticker(self, pair: str) -> dict:
        """Fetch current ticker for a pair.

        Returns dict with at least: {"last": float, "bid": float, "ask": float}
        """

    @abstractmethod
    async def create_limit_order(
        self, pair: str, side: OrderSide, amount: float, price: float
    ) -> Order:
        """Place a limit order on the exchange."""

    @abstractmethod
    async def cancel_order(self, order_id: str, pair: str) -> bool:
        """Cancel an open order. Returns True if successfully cancelled."""

    @abstractmethod
    async def fetch_open_orders(self, pair: str) -> list[Order]:
        """Fetch all open orders for a pair."""

    @abstractmethod
    async def fetch_balance(self) -> dict[str, Balance]:
        """Fetch account balances. Returns dict keyed by asset symbol."""

    @abstractmethod
    async def get_min_order_amount(self, pair: str) -> float:
        """Get minimum order amount for a pair."""

    @abstractmethod
    async def get_min_notional(self, pair: str) -> float:
        """Get minimum notional value (price * amount) for a pair."""
