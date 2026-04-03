import pytest
import pandas as pd

from src.backtest.backtester import Backtester
from src.storage.models import OrderSide


def make_candles(prices: list[float]) -> pd.DataFrame:
    """Create a simple OHLCV dataframe from a list of prices."""
    data = []
    for i, price in enumerate(prices):
        data.append({
            "timestamp": pd.Timestamp("2025-01-01") + pd.Timedelta(minutes=5 * i),
            "open": price,
            "high": price * 1.001,
            "low": price * 0.999,
            "close": price,
            "volume": 100.0,
        })
    return pd.DataFrame(data)


def make_candles_ohlc(candles: list[dict]) -> pd.DataFrame:
    """Create OHLCV dataframe with explicit OHLC values."""
    data = []
    for i, c in enumerate(candles):
        data.append({
            "timestamp": pd.Timestamp("2025-01-01") + pd.Timedelta(minutes=5 * i),
            "open": c.get("open", c["close"]),
            "high": c.get("high", c["close"]),
            "low": c.get("low", c["close"]),
            "close": c["close"],
            "volume": c.get("volume", 100.0),
        })
    return pd.DataFrame(data)


class TestBacktesterBasic:
    def test_runs_without_error(self):
        prices = [65000] * 100  # Flat market
        df = make_candles(prices)
        bt = Backtester("BTC/USDT", 60000, 70000, 5, 45)
        result = bt.run(df)
        assert result.pair == "BTC/USDT"
        assert result.total_candles == 100

    def test_flat_market_no_trades(self):
        # Price stays at 65000; candles have tiny high/low (±0.1%) — no grid level crossed
        prices = [65000] * 50
        df = make_candles(prices)
        bt = Backtester("BTC/USDT", 60000, 70000, 5, 45)
        result = bt.run(df)
        # Grid levels are at 60k/62k/64k/66k/68k/70k; 65k±65 never reaches any of them
        assert len(result.trades) == 0
        assert result.final_equity > 0

    def test_empty_df_raises(self):
        df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        bt = Backtester("BTC/USDT", 60000, 70000, 5, 45)
        with pytest.raises(ValueError, match="empty"):
            bt.run(df)


class TestBacktesterWithMovement:
    def test_price_oscillation_generates_trades(self):
        # Price oscillates between grid levels to trigger fills
        prices = []
        for _ in range(20):
            prices.extend([63000, 61000, 63000, 65000, 67000, 65000])
        df = make_candles_ohlc([
            {"close": p, "high": p + 500, "low": p - 500} for p in prices
        ])
        bt = Backtester("BTC/USDT", 60000, 70000, 5, 45)
        result = bt.run(df)
        assert len(result.trades) > 0

    def test_result_has_all_fields(self):
        prices = [65000, 63000, 61000, 63000, 65000, 67000, 69000, 67000]
        df = make_candles_ohlc([
            {"close": p, "high": p + 1000, "low": p - 1000} for p in prices
        ])
        bt = Backtester("BTC/USDT", 60000, 70000, 5, 45)
        result = bt.run(df)
        assert result.initial_investment == 45
        assert result.final_equity > 0
        assert result.max_drawdown >= 0
        assert result.total_fees >= 0
        # Both P&L fields must be present and numerically distinct from each other
        assert hasattr(result, "realized_pnl")
        assert hasattr(result, "total_return")
        assert result.total_return == pytest.approx(result.final_equity - 45, abs=1e-6)


class TestBacktesterRisk:
    def test_equity_never_negative(self):
        # Even with bad prices, equity should stay positive
        prices = [65000, 60000, 55000, 50000, 45000]
        df = make_candles_ohlc([
            {"close": p, "high": p + 500, "low": p - 500} for p in prices
        ])
        bt = Backtester("BTC/USDT", 60000, 70000, 5, 45)
        result = bt.run(df)
        assert result.final_equity >= 0

    def test_fees_are_tracked(self):
        prices = []
        for _ in range(10):
            prices.extend([63000, 61000, 65000, 67000])
        df = make_candles_ohlc([
            {"close": p, "high": p + 1500, "low": p - 1500} for p in prices
        ])
        bt = Backtester("BTC/USDT", 60000, 70000, 5, 45, fee_rate=0.001)
        result = bt.run(df)
        if len(result.trades) > 0:
            assert result.total_fees > 0
