import click

from src.backtest.backtester import BacktestResult
from src.storage.models import OrderSide


def print_report(result: BacktestResult):
    """Print a formatted backtest report to console."""
    pnl_color = "green" if result.realized_pnl >= 0 else "red"
    pnl_pct = (result.realized_pnl / result.initial_investment * 100) if result.initial_investment > 0 else 0

    click.echo()
    click.echo("=" * 60)
    click.secho("  BACKTEST REPORT", bold=True)
    click.echo("=" * 60)
    click.echo()

    # Period
    click.secho("Period:", bold=True)
    click.echo(f"  From:     {result.start_date}")
    click.echo(f"  To:       {result.end_date}")
    click.echo(f"  Candles:  {result.total_candles}")
    click.echo()

    # Grid config
    click.secho("Configuration:", bold=True)
    click.echo(f"  Pair:       {result.pair}")
    click.echo(f"  Investment: ${result.initial_investment:.2f}")
    click.echo()

    # Performance
    click.secho("Performance:", bold=True)
    pnl_sign = "+" if result.realized_pnl >= 0 else ""
    click.echo(f"  Total P&L:          ", nl=False)
    click.secho(f"{pnl_sign}${result.realized_pnl:.4f} ({pnl_sign}{pnl_pct:.2f}%)", fg=pnl_color)
    click.echo(f"  Final equity:       ${result.final_equity:.4f}")
    click.echo(f"  Max drawdown:       ${result.max_drawdown:.4f} ({result.max_drawdown_pct:.2f}%)")
    click.echo(f"  Total fees paid:    ${result.total_fees:.4f}")
    click.echo()

    # Trade stats
    click.secho("Trades:", bold=True)
    total_trades = len(result.trades)
    buy_trades = sum(1 for t in result.trades if t.side == OrderSide.BUY)
    sell_trades = sum(1 for t in result.trades if t.side == OrderSide.SELL)
    click.echo(f"  Total trades:       {total_trades}")
    click.echo(f"  Buy orders filled:  {buy_trades}")
    click.echo(f"  Sell orders filled: {sell_trades}")
    click.echo(f"  Completed cycles:   {result.completed_cycles}")
    click.echo()

    # Final holdings
    click.secho("Final Holdings:", bold=True)
    click.echo(f"  USDT balance:       ${result.final_quote_balance:.4f}")
    if result.final_base_holdings > 0:
        base_asset = result.pair.split("/")[0]
        click.echo(f"  {base_asset} holdings:     {result.final_base_holdings:.8f}")
    click.echo()

    # Duration and annualized
    if result.start_date and result.end_date:
        duration = result.end_date - result.start_date
        days = duration.total_seconds() / 86400
        if days > 0:
            daily_return = pnl_pct / days
            annual_return = daily_return * 365
            click.secho("Projections:", bold=True)
            click.echo(f"  Duration:           {days:.1f} days")
            click.echo(f"  Daily return:       {daily_return:.4f}%")
            click.echo(f"  Annual return:      ", nl=False)
            ann_color = "green" if annual_return >= 0 else "red"
            click.secho(f"{annual_return:.2f}% (projected)", fg=ann_color)
            click.echo()

    click.echo("=" * 60)
