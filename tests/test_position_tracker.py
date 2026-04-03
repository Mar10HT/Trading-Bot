import pytest

from src.core.position_tracker import PositionTracker
from src.storage.models import OrderSide


def make_tracker(pair: str = "BTC/USDT") -> PositionTracker:
    return PositionTracker(pair=pair, initial_investment=50.0, db=None)


class TestRecordFill:
    def test_buy_increases_holdings(self):
        t = make_tracker()
        t.record_fill(OrderSide.BUY, price=65000, amount=0.001, fee=0.065)
        assert t.base_holdings == pytest.approx(0.001)

    def test_sell_decreases_holdings(self):
        t = make_tracker()
        t.record_fill(OrderSide.BUY, price=65000, amount=0.001, fee=0.065)
        t.record_fill(OrderSide.SELL, price=66000, amount=0.001, fee=0.066)
        assert t.base_holdings == pytest.approx(0.0, abs=1e-10)

    def test_fees_accumulate(self):
        t = make_tracker()
        t.record_fill(OrderSide.BUY, price=65000, amount=0.001, fee=0.065)
        t.record_fill(OrderSide.SELL, price=66000, amount=0.001, fee=0.066)
        assert t.total_fees == pytest.approx(0.131, rel=1e-6)

    def test_completed_cycles_increment_on_sell_only(self):
        t = make_tracker()
        t.record_fill(OrderSide.BUY, price=65000, amount=0.001, fee=0.065)
        assert t.completed_cycles == 0
        t.record_fill(OrderSide.SELL, price=66000, amount=0.001, fee=0.066)
        assert t.completed_cycles == 1


class TestCostBasis:
    def test_cost_basis_correct_after_partial_sell(self):
        """Selling half the holdings should halve the cost basis, not leave it unchanged."""
        t = make_tracker()
        # Buy 1.0 BTC at $65k
        t.record_fill(OrderSide.BUY, price=65000, amount=1.0, fee=65.0)
        full_cost = t._cost_basis
        assert full_cost == pytest.approx(65065.0)  # 65000 + fee

        # Sell 0.5 BTC — cost basis should halve
        t.record_fill(OrderSide.SELL, price=66000, amount=0.5, fee=33.0)
        assert t._cost_basis == pytest.approx(full_cost * 0.5, rel=1e-6)

    def test_unrealized_pnl_after_partial_sell(self):
        """After selling half at a profit, unrealized P&L on remaining half should be correct."""
        t = make_tracker()
        t.record_fill(OrderSide.BUY, price=65000, amount=1.0, fee=65.0)
        t.record_fill(OrderSide.SELL, price=66000, amount=0.5, fee=33.0)

        # Remaining: 0.5 BTC. Cost basis ~32532.5 (half of 65065).
        # At price $67000: market value = 0.5 * 67000 = 33500
        unrealized = t.unrealized_pnl(current_price=67000)
        expected = 0.5 * 67000 - t._cost_basis
        assert unrealized == pytest.approx(expected, rel=1e-6)

    def test_unrealized_pnl_zero_when_no_holdings(self):
        t = make_tracker()
        assert t.unrealized_pnl(current_price=65000) == 0.0

    def test_avg_cost_was_wrong_before_fix(self):
        """Regression: old code returned avg_cost = total_spent / remaining_holdings
        which gives $130k/BTC after selling half, instead of the correct ~$65k/BTC."""
        t = make_tracker()
        t.record_fill(OrderSide.BUY, price=65000, amount=1.0, fee=65.0)
        t.record_fill(OrderSide.SELL, price=66000, amount=0.5, fee=33.0)

        # With fixed code, cost basis of 0.5 BTC should be ~$32.5k, NOT ~$65k
        assert t._cost_basis < 40000.0, (
            f"cost_basis {t._cost_basis} is too high — old avg_cost bug may have returned"
        )


class TestRealizedPnl:
    def test_positive_after_profitable_cycle(self):
        t = make_tracker()
        t.record_fill(OrderSide.BUY, price=65000, amount=0.001, fee=0.065)
        t.record_fill(OrderSide.SELL, price=66000, amount=0.001, fee=0.066)
        # Profit = (66 - 65) USDT - 0.131 fees = 0.869 USDT
        assert t.realized_pnl > 0

    def test_negative_after_loss_cycle(self):
        t = make_tracker()
        t.record_fill(OrderSide.BUY, price=66000, amount=0.001, fee=0.066)
        t.record_fill(OrderSide.SELL, price=65000, amount=0.001, fee=0.065)
        assert t.realized_pnl < 0


class TestSummary:
    def test_summary_contains_expected_keys(self):
        t = make_tracker()
        summary = t.get_summary(current_price=65000)
        for key in ("pair", "base_holdings", "cost_basis", "realized_pnl",
                    "unrealized_pnl", "total_pnl", "total_fees", "completed_cycles"):
            assert key in summary

    def test_total_pnl_is_sum(self):
        t = make_tracker()
        t.record_fill(OrderSide.BUY, price=65000, amount=0.001, fee=0.065)
        summary = t.get_summary(current_price=66000)
        assert summary["total_pnl"] == pytest.approx(
            summary["realized_pnl"] + summary["unrealized_pnl"], abs=1e-6
        )
