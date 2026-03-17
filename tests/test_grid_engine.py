from src.core.grid_engine import GridEngine
from src.storage.models import OrderSide


def make_engine(lower=60000, upper=70000, grids=5, investment=45, fee=0.001):
    return GridEngine(
        pair="BTC/USDT",
        lower_price=lower,
        upper_price=upper,
        num_grids=grids,
        investment=investment,
        fee_rate=fee,
    )


class TestGridLevelCalculation:
    def test_levels_count(self):
        engine = make_engine(grids=5)
        assert len(engine.levels) == 6  # num_grids + 1

    def test_levels_evenly_spaced(self):
        engine = make_engine(lower=60000, upper=70000, grids=5)
        expected_step = 2000.0
        for i in range(1, len(engine.levels)):
            step = engine.levels[i] - engine.levels[i - 1]
            assert abs(step - expected_step) < 0.01

    def test_levels_boundaries(self):
        engine = make_engine(lower=60000, upper=70000)
        assert engine.levels[0] == 60000
        assert engine.levels[-1] == 70000

    def test_two_grids(self):
        engine = make_engine(lower=100, upper=200, grids=2)
        assert engine.levels == [100, 150, 200]

    def test_amount_per_level_is_positive(self):
        engine = make_engine()
        assert engine.order_amount_per_level > 0


class TestGridInitialization:
    def test_initialize_creates_actions(self):
        engine = make_engine(lower=60000, upper=70000, grids=5)
        actions = engine.initialize(current_price=65000)
        assert len(actions) > 0

    def test_buys_below_sells_above(self):
        engine = make_engine(lower=60000, upper=70000, grids=5)
        actions = engine.initialize(current_price=65000)
        for action in actions:
            if action.side == OrderSide.BUY:
                assert action.price < 65000
            elif action.side == OrderSide.SELL:
                assert action.price > 65000

    def test_all_levels_assigned(self):
        engine = make_engine(lower=60000, upper=70000, grids=5)
        actions = engine.initialize(current_price=65000)
        buy_count = sum(1 for a in actions if a.side == OrderSide.BUY)
        sell_count = sum(1 for a in actions if a.side == OrderSide.SELL)
        # With price at 65000 (midpoint): levels 60k, 62k, 64k are buys; 66k, 68k, 70k are sells
        assert buy_count == 3
        assert sell_count == 3

    def test_price_at_level_skips_it(self):
        engine = make_engine(lower=60000, upper=70000, grids=5)
        # Price exactly at 64000 (level 2)
        actions = engine.initialize(current_price=64000)
        prices = [a.price for a in actions]
        assert 64000 not in prices


class TestOrderFilled:
    def test_buy_filled_creates_sell(self):
        engine = make_engine(lower=60000, upper=70000, grids=5)
        engine.initialize(current_price=65000)
        # Buy filled at level 2 (64000) → should create sell at level 3 (66000)
        action = engine.on_order_filled(grid_level=2, side=OrderSide.BUY)
        assert action is not None
        assert action.side == OrderSide.SELL
        assert action.grid_level == 3
        assert action.price == 66000

    def test_sell_filled_creates_buy(self):
        engine = make_engine(lower=60000, upper=70000, grids=5)
        engine.initialize(current_price=65000)
        # Sell filled at level 3 (66000) → should create buy at level 2 (64000)
        action = engine.on_order_filled(grid_level=3, side=OrderSide.SELL)
        assert action is not None
        assert action.side == OrderSide.BUY
        assert action.grid_level == 2
        assert action.price == 64000

    def test_buy_at_top_returns_none(self):
        engine = make_engine(lower=60000, upper=70000, grids=5)
        engine.initialize(current_price=65000)
        # Buy at last level can't create sell above
        action = engine.on_order_filled(grid_level=5, side=OrderSide.BUY)
        assert action is None

    def test_sell_at_bottom_returns_none(self):
        engine = make_engine(lower=60000, upper=70000, grids=5)
        engine.initialize(current_price=65000)
        # Sell at first level can't create buy below
        action = engine.on_order_filled(grid_level=0, side=OrderSide.SELL)
        assert action is None


class TestProfitCalculation:
    def test_profit_per_grid_positive(self):
        engine = make_engine(lower=60000, upper=70000, grids=5, investment=45)
        profit = engine.get_profit_per_grid()
        # With $2000 spacing on $65k avg price, profit should be positive after fees
        assert profit > 0

    def test_tight_grid_low_profit(self):
        # Very tight grid = small profit, possibly negative after fees
        engine = make_engine(lower=64900, upper=65100, grids=5, investment=45)
        profit = engine.get_profit_per_grid()
        # Spacing is only $40, very tight. Profit may be low
        assert isinstance(profit, float)


class TestGridState:
    def test_get_state_serializable(self):
        engine = make_engine()
        engine.initialize(current_price=65000)
        state = engine.get_state()
        assert state["pair"] == "BTC/USDT"
        assert len(state["levels"]) == 6
        assert state["initialized"] is True

    def test_get_summary(self):
        engine = make_engine()
        engine.initialize(current_price=65000)
        summary = engine.get_grid_summary()
        assert summary["pair"] == "BTC/USDT"
        assert summary["num_levels"] == 6
        assert summary["grid_spacing"] == 2000.0
        assert summary["active_buys"] == 3
        assert summary["active_sells"] == 3
