from dataclasses import dataclass, field

import pandas as pd
import structlog

from src.core.grid_engine import GridEngine
from src.storage.models import OrderSide

logger = structlog.get_logger()


@dataclass
class BacktestTrade:
    timestamp: pd.Timestamp
    side: OrderSide
    price: float
    amount: float
    fee: float
    grid_level: int


@dataclass
class BacktestResult:
    pair: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    initial_investment: float
    total_candles: int

    # Trade stats
    trades: list[BacktestTrade] = field(default_factory=list)
    completed_cycles: int = 0
    total_fees: float = 0.0

    # P&L
    realized_pnl: float = 0.0
    final_equity: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0

    # Holdings at end
    final_base_holdings: float = 0.0
    final_quote_balance: float = 0.0


class Backtester:
    """Replays historical price data through the GridEngine to simulate performance."""

    def __init__(
        self,
        pair: str,
        lower_price: float,
        upper_price: float,
        num_grids: int,
        investment: float,
        fee_rate: float = 0.001,
    ):
        self.engine = GridEngine(
            pair=pair,
            lower_price=lower_price,
            upper_price=upper_price,
            num_grids=num_grids,
            investment=investment,
            fee_rate=fee_rate,
        )
        self.fee_rate = fee_rate
        self.investment = investment

    def run(self, df: pd.DataFrame) -> BacktestResult:
        """Run backtest against historical OHLCV data.

        Uses the 'close' price of each candle to check for order fills.
        Also checks 'low' and 'high' to detect intra-candle crosses.
        """
        if df.empty:
            raise ValueError("Cannot backtest with empty data")

        result = BacktestResult(
            pair=self.engine.pair,
            start_date=df["timestamp"].iloc[0],
            end_date=df["timestamp"].iloc[-1],
            initial_investment=self.investment,
            total_candles=len(df),
        )

        # State tracking
        quote_balance = self.investment  # USDT
        base_balance = 0.0  # BTC/ETH/etc
        peak_equity = self.investment

        # Open orders: {grid_level: {"side": OrderSide, "price": float}}
        open_orders: dict[int, dict] = {}

        # Initialize grid with first candle's close price
        first_price = df["close"].iloc[0]
        actions = self.engine.initialize(first_price)

        for action in actions:
            notional = action.amount * action.price
            if action.side == OrderSide.BUY and notional <= quote_balance:
                open_orders[action.grid_level] = {
                    "side": action.side,
                    "price": action.price,
                    "amount": action.amount,
                }

            elif action.side == OrderSide.SELL:
                # For initial sells, we need to "buy" the base asset first at current price
                # In real grid trading, you'd place limit orders. Here we simulate:
                # Only place sell orders if we can afford to buy the base at market
                cost = action.amount * first_price * (1 + self.fee_rate)
                if cost <= quote_balance:
                    quote_balance -= cost
                    base_balance += action.amount
                    fee = action.amount * first_price * self.fee_rate
                    result.total_fees += fee
                    open_orders[action.grid_level] = {
                        "side": action.side,
                        "price": action.price,
                        "amount": action.amount,
                    }

        # Replay candles
        for _, candle in df.iterrows():
            low = candle["low"]
            high = candle["high"]
            timestamp = candle["timestamp"]

            filled_levels = []

            for level, order in open_orders.items():
                filled = False

                if order["side"] == OrderSide.BUY and low <= order["price"]:
                    # Buy order filled
                    cost = order["amount"] * order["price"]
                    fee = cost * self.fee_rate
                    if quote_balance >= cost + fee:
                        quote_balance -= (cost + fee)
                        base_balance += order["amount"]
                        result.total_fees += fee
                        result.trades.append(BacktestTrade(
                            timestamp=timestamp,
                            side=OrderSide.BUY,
                            price=order["price"],
                            amount=order["amount"],
                            fee=fee,
                            grid_level=level,
                        ))
                        filled = True

                elif order["side"] == OrderSide.SELL and high >= order["price"]:
                    # Sell order filled
                    if base_balance >= order["amount"]:
                        revenue = order["amount"] * order["price"]
                        fee = revenue * self.fee_rate
                        quote_balance += (revenue - fee)
                        base_balance -= order["amount"]
                        result.total_fees += fee
                        result.trades.append(BacktestTrade(
                            timestamp=timestamp,
                            side=OrderSide.SELL,
                            price=order["price"],
                            amount=order["amount"],
                            fee=fee,
                            grid_level=level,
                        ))
                        filled = True

                if filled:
                    filled_levels.append(level)

            # Process filled orders → place new ones
            for level in filled_levels:
                filled_order = open_orders.pop(level)
                next_action = self.engine.on_order_filled(level, filled_order["side"])

                if next_action:
                    open_orders[next_action.grid_level] = {
                        "side": next_action.side,
                        "price": next_action.price,
                        "amount": next_action.amount,
                    }

                    # Count completed cycles (a buy followed by sell = 1 cycle)
                    if filled_order["side"] == OrderSide.SELL:
                        result.completed_cycles += 1

            # Calculate current equity for drawdown tracking
            close_price = candle["close"]
            current_equity = quote_balance + (base_balance * close_price)

            if current_equity > peak_equity:
                peak_equity = current_equity

            drawdown = peak_equity - current_equity
            drawdown_pct = (drawdown / peak_equity * 100) if peak_equity > 0 else 0

            if drawdown > result.max_drawdown:
                result.max_drawdown = drawdown
                result.max_drawdown_pct = drawdown_pct

        # Final calculations
        final_price = df["close"].iloc[-1]
        result.final_base_holdings = base_balance
        result.final_quote_balance = quote_balance
        result.final_equity = quote_balance + (base_balance * final_price)
        result.realized_pnl = result.final_equity - self.investment

        return result
