import structlog

from src.utils.config import RiskConfig
from src.utils.helpers import validate_min_notional

logger = structlog.get_logger()


class RiskManager:
    """Monitors risk and enforces safety limits.

    Tracks drawdown, validates orders against minimums, and triggers
    kill switch when thresholds are breached.
    """

    def __init__(self, config: RiskConfig):
        self.config = config
        self.initial_capital = config.max_total_investment
        self._kill_switch_active = False

    @property
    def is_killed(self) -> bool:
        return self._kill_switch_active

    def check_order_valid(self, amount: float, price: float) -> tuple[bool, str]:
        """Validate an order against risk rules."""
        if self._kill_switch_active:
            return False, "Kill switch is active"

        notional = amount * price
        if notional < self.config.min_order_value:
            return False, f"Order value {notional:.2f} below minimum {self.config.min_order_value}"

        if not validate_min_notional(amount, price, self.config.min_order_value):
            return False, "Order does not meet minimum notional"

        return True, "OK"

    def check_drawdown(self, current_equity: float) -> tuple[bool, str]:
        """Check if drawdown exceeds limits. Returns (is_safe, reason)."""
        if self._kill_switch_active:
            return False, "Kill switch already active"

        loss = self.initial_capital - current_equity
        loss_pct = (loss / self.initial_capital) * 100 if self.initial_capital > 0 else 0

        if loss >= self.config.max_drawdown_absolute:
            self._kill_switch_active = True
            reason = (
                f"Absolute drawdown limit hit: ${loss:.2f} >= ${self.config.max_drawdown_absolute}"
            )
            logger.critical("kill_switch_triggered", reason=reason)
            return False, reason

        if loss_pct >= self.config.max_drawdown_pct:
            self._kill_switch_active = True
            reason = (
                f"Percentage drawdown limit hit: {loss_pct:.1f}% >= {self.config.max_drawdown_pct}%"
            )
            logger.critical("kill_switch_triggered", reason=reason)
            return False, reason

        return True, f"Drawdown OK: ${loss:.2f} ({loss_pct:.1f}%)"

    def get_usable_capital(self) -> float:
        """Calculate usable capital after reserving a percentage."""
        reserve = self.initial_capital * (self.config.reserve_pct / 100)
        return self.initial_capital - reserve

    def activate_kill_switch(self, reason: str = "Manual"):
        """Manually activate the kill switch."""
        self._kill_switch_active = True
        logger.critical("kill_switch_activated", reason=reason)

    def reset_kill_switch(self):
        """Reset the kill switch (use with caution)."""
        self._kill_switch_active = False
        logger.warning("kill_switch_reset")
