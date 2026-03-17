from datetime import datetime
from pathlib import Path

import ccxt
import pandas as pd
import structlog

logger = structlog.get_logger()

DATA_DIR = Path("data/historical")


def fetch_ohlcv(
    pair: str,
    timeframe: str = "5m",
    since: str | None = None,
    until: str | None = None,
    limit: int = 1000,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch OHLCV candle data from Binance.

    Args:
        pair: Trading pair (e.g. "BTC/USDT")
        timeframe: Candle interval ("1m", "5m", "15m", "1h", "1d")
        since: Start date as ISO string (e.g. "2025-01-01")
        until: End date as ISO string (e.g. "2025-03-01")
        limit: Max candles per API request
        use_cache: Whether to cache/load from CSV files

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
    """
    cache_file = _get_cache_path(pair, timeframe, since, until)

    if use_cache and cache_file.exists():
        logger.info("loading_cached_data", file=str(cache_file))
        return pd.read_csv(cache_file, parse_dates=["timestamp"])

    exchange = ccxt.binance({"enableRateLimit": True})

    since_ts = None
    if since:
        since_ts = int(datetime.fromisoformat(since).timestamp() * 1000)

    until_ts = None
    if until:
        until_ts = int(datetime.fromisoformat(until).timestamp() * 1000)

    all_candles = []
    current_since = since_ts

    logger.info("fetching_ohlcv", pair=pair, timeframe=timeframe, since=since, until=until)

    while True:
        candles = exchange.fetch_ohlcv(
            pair, timeframe=timeframe, since=current_since, limit=limit
        )

        if not candles:
            break

        all_candles.extend(candles)

        # Move to next batch
        last_timestamp = candles[-1][0]
        current_since = last_timestamp + 1

        if until_ts and last_timestamp >= until_ts:
            break

        if len(candles) < limit:
            break

        logger.debug("fetched_batch", count=len(candles), total=len(all_candles))

    if not all_candles:
        logger.warning("no_data_fetched", pair=pair)
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    # Filter by until date
    if until_ts:
        df = df[df["timestamp"] <= pd.Timestamp(until)]

    # Remove duplicates
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    # Cache to CSV
    if use_cache:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_file, index=False)
        logger.info("data_cached", file=str(cache_file), rows=len(df))

    return df


def _get_cache_path(pair: str, timeframe: str, since: str | None, until: str | None) -> Path:
    """Generate a cache file path for the given parameters."""
    pair_slug = pair.replace("/", "_")
    since_slug = since.replace("-", "") if since else "start"
    until_slug = until.replace("-", "") if until else "end"
    filename = f"{pair_slug}_{timeframe}_{since_slug}_{until_slug}.csv"
    return DATA_DIR / filename
