import click
import structlog

from src.utils.config import load_config
from src.utils.logger import setup_logging

logger = structlog.get_logger()


@click.group()
@click.option("--config", "-c", default="config/default.yaml", help="Path to config file")
@click.pass_context
def cli(ctx, config):
    """Trade Bot - Grid Trading for Binance"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)
    cfg = ctx.obj["config"]
    setup_logging(level=cfg.logging.level, log_file=cfg.logging.file)


@cli.command()
@click.pass_context
def run(ctx):
    """Start the trading bot."""
    import asyncio

    cfg = ctx.obj["config"]
    logger.info("bot_starting", mode=cfg.mode, pairs=[p.pair for p in cfg.pairs])

    asyncio.run(_run_bot(cfg))


async def _run_bot(cfg):
    """Main async bot loop."""
    from src.core.grid_engine import GridEngine
    from src.core.risk_manager import RiskManager
    from src.exchange.paper import PaperExchange
    from src.storage.database import Database

    # Initialize components
    db = Database()
    await db.connect()

    risk_manager = RiskManager(cfg.risk)

    # Create exchange based on mode
    if cfg.mode == "paper":
        exchange = PaperExchange(
            initial_balance=cfg.risk.max_total_investment,
            fee_rate=cfg.exchange.fee_rate,
        )
    else:
        logger.error("mode_not_implemented", mode=cfg.mode)
        return

    # Initialize grid engines for each pair
    engines: list[GridEngine] = []
    for pair_cfg in cfg.pairs:
        engine = GridEngine(
            pair=pair_cfg.pair,
            lower_price=pair_cfg.lower_price,
            upper_price=pair_cfg.upper_price,
            num_grids=pair_cfg.num_grids,
            investment=pair_cfg.investment,
            fee_rate=cfg.exchange.fee_rate,
        )
        engines.append(engine)

    # Start trading loop for each pair
    import asyncio

    tasks = []
    for engine in engines:
        task = asyncio.create_task(
            _trading_loop(engine, exchange, risk_manager, db, cfg.exchange.poll_interval_seconds)
        )
        tasks.append(task)

    logger.info("bot_running", num_pairs=len(engines))

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("bot_stopping", reason="keyboard_interrupt")
    finally:
        await exchange.close()
        await db.close()


async def _trading_loop(engine, exchange, risk_manager, db, poll_interval):
    """Main trading loop for a single pair."""
    import asyncio

    from src.storage.models import OrderSide, OrderStatus

    # Get initial price and initialize grid
    ticker = await exchange.fetch_ticker(engine.pair)
    current_price = ticker["last"]
    logger.info("initial_price", pair=engine.pair, price=current_price)

    actions = engine.initialize(current_price)
    summary = engine.get_grid_summary()
    logger.info("grid_summary", **summary)

    # Place initial orders
    placed_orders = {}
    for action in actions:
        valid, reason = risk_manager.check_order_valid(action.amount, action.price)
        if not valid:
            logger.warning("order_skipped", reason=reason, level=action.grid_level)
            continue
        try:
            order = await exchange.create_limit_order(
                engine.pair, action.side, action.amount, action.price
            )
            placed_orders[order.id] = action.grid_level
            await db.save_order(order)
        except ValueError as e:
            logger.warning("order_failed", error=str(e), level=action.grid_level)

    # Main polling loop
    while not risk_manager.is_killed:
        await asyncio.sleep(poll_interval)

        try:
            ticker = await exchange.fetch_ticker(engine.pair)
            current_price = ticker["last"]

            # Check drawdown
            balances = await exchange.fetch_balance()
            usdt = balances.get("USDT")
            equity = usdt.total if usdt else 0
            # Add value of held assets
            for asset, bal in balances.items():
                if asset != "USDT" and bal.total > 0:
                    try:
                        pair_ticker = await exchange.fetch_ticker(f"{asset}/USDT")
                        equity += bal.total * pair_ticker["last"]
                    except Exception:
                        pass

            safe, reason = risk_manager.check_drawdown(equity)
            if not safe:
                logger.critical("stopping_pair", pair=engine.pair, reason=reason)
                # Cancel all open orders
                open_orders = await exchange.fetch_open_orders(engine.pair)
                for order in open_orders:
                    await exchange.cancel_order(order.id, engine.pair)
                break

            # Check for filled orders and place new ones
            open_orders = await exchange.fetch_open_orders(engine.pair)
            open_ids = {o.id for o in open_orders}

            # Find orders that were in our tracked list but are no longer open (= filled)
            filled_levels = []
            for order_id, level in list(placed_orders.items()):
                if order_id not in open_ids:
                    filled_levels.append((order_id, level))
                    del placed_orders[order_id]

            # Process filled orders
            for order_id, level in filled_levels:
                # Determine the side from the engine state
                level_state = engine.level_states.get(level)
                if level_state == "buy":
                    side = OrderSide.BUY
                elif level_state == "sell":
                    side = OrderSide.SELL
                else:
                    continue

                next_action = engine.on_order_filled(level, side)
                if next_action:
                    valid, reason = risk_manager.check_order_valid(
                        next_action.amount, next_action.price
                    )
                    if valid:
                        try:
                            new_order = await exchange.create_limit_order(
                                engine.pair, next_action.side,
                                next_action.amount, next_action.price,
                            )
                            placed_orders[new_order.id] = next_action.grid_level
                            await db.save_order(new_order)
                        except ValueError as e:
                            logger.warning("order_failed", error=str(e))

            # Save grid state periodically
            await db.save_grid_state(engine.pair, engine.get_state())

        except Exception as e:
            logger.error("loop_error", pair=engine.pair, error=str(e))
            await asyncio.sleep(poll_interval)


@cli.command()
@click.option("--pair", "-p", default="BTC/USDT", help="Trading pair")
@click.option("--since", "-s", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--until", "-u", required=True, help="End date (YYYY-MM-DD)")
@click.option("--lower", "-l", type=float, required=True, help="Grid lower price")
@click.option("--upper", type=float, required=True, help="Grid upper price")
@click.option("--grids", "-g", type=int, default=5, help="Number of grid levels")
@click.option("--investment", "-i", type=float, default=45.0, help="Investment in USDT")
@click.option("--timeframe", "-t", default="5m", help="Candle timeframe (1m, 5m, 15m, 1h)")
@click.pass_context
def backtest(ctx, pair, since, until, lower, upper, grids, investment, timeframe):
    """Run backtest against historical data."""
    from src.backtest.backtester import Backtester
    from src.backtest.data_fetcher import fetch_ohlcv
    from src.backtest.report import print_report

    cfg = ctx.obj["config"]

    click.echo(f"Fetching {pair} data from {since} to {until} ({timeframe} candles)...")
    df = fetch_ohlcv(pair=pair, timeframe=timeframe, since=since, until=until)

    if df.empty:
        click.secho("No data fetched. Check pair and date range.", fg="red")
        return

    click.echo(f"Running backtest on {len(df)} candles...")

    bt = Backtester(
        pair=pair,
        lower_price=lower,
        upper_price=upper,
        num_grids=grids,
        investment=investment,
        fee_rate=cfg.exchange.fee_rate,
    )
    result = bt.run(df)
    print_report(result)


@cli.command()
@click.pass_context
def info(ctx):
    """Show grid configuration summary."""
    cfg = ctx.obj["config"]
    click.echo(f"\nMode: {cfg.mode}")
    click.echo(f"Max investment: ${cfg.risk.max_total_investment}")
    click.echo(f"Reserve: {cfg.risk.reserve_pct}%")
    click.echo(f"Kill switch at: {cfg.risk.max_drawdown_pct}% / ${cfg.risk.max_drawdown_absolute}")
    click.echo()

    for pair_cfg in cfg.pairs:
        from src.core.grid_engine import GridEngine

        engine = GridEngine(
            pair=pair_cfg.pair,
            lower_price=pair_cfg.lower_price,
            upper_price=pair_cfg.upper_price,
            num_grids=pair_cfg.num_grids,
            investment=pair_cfg.investment,
            fee_rate=cfg.exchange.fee_rate,
        )
        summary = engine.get_grid_summary()
        click.echo(f"--- {summary['pair']} ---")
        click.echo(f"  Range: {summary['range']}")
        click.echo(f"  Levels: {summary['num_levels']}")
        click.echo(f"  Grid spacing: ${summary['grid_spacing']}")
        click.echo(f"  Amount/level: {summary['amount_per_level']:.8f}")
        click.echo(f"  Profit/cycle: ${summary['profit_per_cycle']:.6f}")
        click.echo(f"  Investment: ${summary['investment']}")
        click.echo()


if __name__ == "__main__":
    cli()
