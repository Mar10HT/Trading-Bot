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
    """Main async bot loop using the strategy layer."""
    from src.core.risk_manager import RiskManager
    from src.exchange.paper import PaperExchange
    from src.storage.database import Database
    from src.strategy.multi_pair_manager import MultiPairManager

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

    # Create multi-pair manager
    manager = MultiPairManager(cfg, exchange, risk_manager, db)

    # Set shared state for dashboard
    from src.dashboard import state as dash_state
    dash_state.manager = manager
    dash_state.db = db
    dash_state.bot_mode = cfg.mode

    # Start dashboard server alongside bot
    import uvicorn
    from src.dashboard.app import create_app

    app = create_app()
    server_config = uvicorn.Config(
        app,
        host=cfg.dashboard.host,
        port=cfg.dashboard.port,
        log_level="warning",
    )
    server = uvicorn.Server(server_config)

    logger.info(
        "dashboard_starting",
        url=f"http://{cfg.dashboard.host}:{cfg.dashboard.port}",
    )

    try:
        # Run bot and dashboard concurrently
        import asyncio
        await asyncio.gather(
            manager.start_all(),
            server.serve(),
        )
    except KeyboardInterrupt:
        logger.info("bot_stopping", reason="keyboard_interrupt")
        await manager.stop_all()
    finally:
        await exchange.close()
        await db.close()


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
