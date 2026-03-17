import math


def round_price(price: float, tick_size: float = 0.01) -> float:
    """Round price to the nearest tick size."""
    if tick_size <= 0:
        return price
    precision = max(0, -int(math.log10(tick_size)))
    return round(round(price / tick_size) * tick_size, precision)


def round_amount(amount: float, step_size: float = 0.00001) -> float:
    """Round amount down to the nearest step size (always floor to avoid exceeding balance)."""
    if step_size <= 0:
        return amount
    precision = max(0, -int(math.log10(step_size)))
    return round(math.floor(amount / step_size) * step_size, precision)


def calculate_fee(amount: float, price: float, fee_rate: float = 0.001) -> float:
    """Calculate trading fee for an order."""
    return amount * price * fee_rate


def format_pnl(pnl: float) -> str:
    """Format P&L value with sign and color hint."""
    sign = "+" if pnl >= 0 else ""
    return f"{sign}{pnl:.4f} USDT"


def validate_min_notional(amount: float, price: float, min_notional: float = 10.0) -> bool:
    """Check if order meets minimum notional value requirement."""
    return amount * price >= min_notional
