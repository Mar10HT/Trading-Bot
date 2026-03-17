from src.core.risk_manager import RiskManager
from src.utils.config import RiskConfig


def make_risk_manager(**kwargs):
    defaults = {
        "max_total_investment": 50.0,
        "min_order_value": 11.0,
        "max_drawdown_pct": 20.0,
        "max_drawdown_absolute": 10.0,
        "reserve_pct": 10.0,
    }
    defaults.update(kwargs)
    return RiskManager(RiskConfig(**defaults))


class TestOrderValidation:
    def test_valid_order(self):
        rm = make_risk_manager()
        valid, reason = rm.check_order_valid(amount=0.0002, price=65000)
        # 0.0002 * 65000 = 13 USDT > 11 minimum
        assert valid
        assert reason == "OK"

    def test_order_below_minimum(self):
        rm = make_risk_manager()
        valid, reason = rm.check_order_valid(amount=0.0001, price=65000)
        # 0.0001 * 65000 = 6.5 USDT < 11 minimum
        assert not valid

    def test_order_rejected_when_killed(self):
        rm = make_risk_manager()
        rm.activate_kill_switch("test")
        valid, reason = rm.check_order_valid(amount=0.0002, price=65000)
        assert not valid
        assert "Kill switch" in reason


class TestDrawdown:
    def test_within_limits(self):
        rm = make_risk_manager()
        safe, reason = rm.check_drawdown(current_equity=48)
        assert safe

    def test_absolute_limit_hit(self):
        rm = make_risk_manager(max_drawdown_absolute=10)
        safe, reason = rm.check_drawdown(current_equity=40)
        # Lost $10 = exactly at limit
        assert not safe
        assert rm.is_killed

    def test_percentage_limit_hit(self):
        rm = make_risk_manager(max_drawdown_pct=20)
        safe, reason = rm.check_drawdown(current_equity=39)
        # Lost $11 = 22% > 20%
        assert not safe
        assert rm.is_killed

    def test_kill_switch_persists(self):
        rm = make_risk_manager()
        rm.activate_kill_switch("test")
        safe, reason = rm.check_drawdown(current_equity=50)
        assert not safe


class TestCapital:
    def test_usable_capital(self):
        rm = make_risk_manager(max_total_investment=50, reserve_pct=10)
        assert rm.get_usable_capital() == 45.0

    def test_kill_switch_reset(self):
        rm = make_risk_manager()
        rm.activate_kill_switch("test")
        assert rm.is_killed
        rm.reset_kill_switch()
        assert not rm.is_killed
