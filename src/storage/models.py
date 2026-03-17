from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"


class Order(BaseModel):
    id: str = ""
    pair: str
    side: OrderSide
    price: float
    amount: float
    status: OrderStatus = OrderStatus.PENDING
    grid_level: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    filled_at: datetime | None = None
    fee: float = 0.0


class Trade(BaseModel):
    id: int = 0
    pair: str
    side: OrderSide
    price: float
    amount: float
    fee: float = 0.0
    realized_pnl: float = 0.0
    grid_level: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GridState(BaseModel):
    pair: str
    lower_price: float
    upper_price: float
    num_grids: int
    levels: list[float] = []
    active_buy_levels: list[int] = []
    active_sell_levels: list[int] = []
    investment: float = 0.0
    is_running: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Balance(BaseModel):
    asset: str
    free: float = 0.0
    locked: float = 0.0
    total: float = 0.0


class GridAction(BaseModel):
    """Action emitted by GridEngine when a level is crossed."""
    side: OrderSide
    price: float
    amount: float
    grid_level: int
