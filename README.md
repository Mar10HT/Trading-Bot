# Trade Bot - Grid Trading Bot for Binance

A sophisticated grid trading bot for cryptocurrency markets built with Python, featuring backtesting capabilities, a real-time dashboard, and multiple trading modes (paper, testnet, live).

## Overview

**Trade Bot** is a professional-grade grid trading implementation for Binance that automatically buys and sells cryptocurrencies across evenly-spaced price levels. The bot generates profit from price oscillations within a defined range and includes comprehensive risk management, backtesting tools, and a live dashboard.

### Key Features

- **Grid Trading Engine** — Executes buy/sell orders at evenly-spaced price levels
- **Multiple Modes** — Paper (simulated), testnet (Binance Testnet), and live trading
- **Real-Time Dashboard** — Monitor positions, P&L, and active orders via FastAPI web UI
- **Backtesting** — Test strategies against historical OHLCV data before trading live
- **Risk Management** — Kill switches, position limits, and drawdown protection
- **Async Architecture** — High-performance async/await with asyncio and aiohttp
- **Persistent Storage** — Trade history and order state tracked in SQLite
- **Structured Logging** — JSON and human-readable logging with structlog
- **WebSocket Support** — Real-time updates to dashboard via WebSocket

## Quick Start

### Prerequisites

- Python 3.11+
- pip (or uv/poetry)
- A Binance API key (for testnet/live) or use paper mode for simulation

### Installation

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd Trade-Bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (optional for paper mode)
   ```

### Running the Bot

#### Paper Trading Mode (Simulated)
```bash
trade-bot run
```
Starts the bot in paper mode with default config (`config/default.yaml`).

#### Custom Configuration
```bash
trade-bot --config config/custom.yaml run
```

#### View Grid Configuration
```bash
trade-bot info
```
Displays grid levels, profit-per-cycle, and per-level amounts.

#### Run Backtests
```bash
trade-bot backtest \
  --pair BTC/USDT \
  --since 2024-01-01 \
  --until 2024-03-01 \
  --lower 72000 \
  --upper 76000 \
  --grids 5 \
  --investment 45.0 \
  --timeframe 5m
```

### Accessing the Dashboard

Once the bot is running, open your browser:
```
http://127.0.0.1:8080
```

The dashboard displays:
- Real-time balance and unrealized P&L
- Active buy/sell orders at each grid level
- Trade history with entry/exit prices
- Risk metrics and kill-switch status

## Architecture

### Directory Structure

```
Trade-Bot/
├── src/
│   ├── core/                 # Core trading logic
│   │   ├── grid_engine.py    # Grid level calculation and state
│   │   ├── order_manager.py  # Order lifecycle management
│   │   ├── position_tracker.py # Position and P&L tracking
│   │   └── risk_manager.py   # Risk limits and kill switches
│   ├── strategy/             # Trading strategy orchestration
│   │   ├── grid_strategy.py  # Single-pair grid trading loop
│   │   └── multi_pair_manager.py # Multi-pair coordinator
│   ├── exchange/             # Exchange abstraction
│   │   ├── base.py           # Abstract exchange interface
│   │   └── paper.py          # Paper trading implementation
│   ├── storage/              # Data persistence
│   │   ├── database.py       # SQLite connection and queries
│   │   └── models.py         # Pydantic data models
│   ├── dashboard/            # Web dashboard (FastAPI)
│   │   ├── app.py            # FastAPI app factory
│   │   ├── state.py          # Shared state (manager, db, etc.)
│   │   └── routes/           # API endpoints (status, trades, pnl, controls)
│   ├── backtest/             # Backtesting suite
│   │   ├── backtester.py     # Backtest engine
│   │   ├── data_fetcher.py   # Historical data from ccxt
│   │   └── report.py         # Backtest result formatting
│   ├── notifications/        # Telegram alerts (placeholder)
│   ├── utils/                # Configuration and logging
│   │   ├── config.py         # YAML config + Pydantic validation
│   │   ├── logger.py         # Structlog setup
│   │   └── helpers.py        # Utility functions
│   └── main.py               # CLI entry point
├── tests/                    # pytest test suite
│   ├── test_grid_engine.py
│   ├── test_order_manager.py
│   ├── test_position_tracker.py
│   ├── test_risk_manager.py
│   ├── test_backtester.py
│   └── conftest.py
├── config/
│   └── default.yaml          # Default bot configuration
├── data/                     # Runtime data (logs, database, etc.)
├── pyproject.toml            # Dependencies and project metadata
├── .env.example              # Environment variables template
└── .gitignore
```

### Key Components

#### Grid Engine (`src/core/grid_engine.py`)
Calculates evenly-spaced price levels and determines when to buy/sell:
- Levels below current price → buy orders
- Levels above current price → sell orders
- When a buy fills at level N → place sell at level N+1
- When a sell fills at level N → place buy at level N-1

#### Order Manager (`src/core/order_manager.py`)
Manages order lifecycle (pending → open → filled/cancelled) and tracks fills.

#### Position Tracker (`src/core/position_tracker.py`)
Tracks cost basis, average entry price, and calculates realized/unrealized P&L.

#### Risk Manager (`src/core/risk_manager.py`)
Enforces position limits and kill switches:
- Max total investment cap
- Max drawdown (% or absolute)
- Min order value (exchange minimum)
- Reserve percentage (untradeable buffer)

#### Grid Strategy (`src/strategy/grid_strategy.py`)
Orchestrates the main trading loop for a single pair:
1. Fetch current price
2. Calculate grid actions (buys/sells to place/cancel)
3. Execute orders
4. Update position and P&L
5. Sleep and repeat

#### Multi-Pair Manager (`src/strategy/multi_pair_manager.py`)
Coordinates multiple grid strategies trading different pairs concurrently.

#### Paper Exchange (`src/exchange/paper.py`)
Simulates exchange behavior without real capital:
- Matches orders immediately against current price
- Deducts fees from fills
- Maintains order book state

#### Dashboard (`src/dashboard/`)
FastAPI web UI with:
- Real-time status endpoint (`/api/status`)
- Trade history endpoint (`/api/trades`)
- P&L metrics endpoint (`/api/pnl`)
- Controls endpoint (`/api/controls` — start/stop/pause)
- WebSocket for live updates (`/ws`)

## Configuration

### YAML Configuration (`config/default.yaml`)

```yaml
mode: "paper"              # paper | testnet | live

pairs:
  - pair: "BTC/USDT"
    lower_price: 72000.0   # Grid lower boundary
    upper_price: 76000.0   # Grid upper boundary
    num_grids: 5           # Number of grid levels
    investment: 45.0       # USDT to allocate to this pair

risk:
  max_total_investment: 50.0    # Total capital cap
  min_order_value: 11.0         # Minimum per-order (Binance notional)
  max_drawdown_pct: 20.0        # Kill switch at 20% loss
  max_drawdown_absolute: 10.0   # Kill switch at $10 loss
  reserve_pct: 10.0             # Keep 10% untradeable

exchange:
  fee_rate: 0.001               # 0.1% Binance fee
  poll_interval_seconds: 10     # Price check interval

dashboard:
  host: "127.0.0.1"
  port: 8080

logging:
  level: "INFO"                 # DEBUG | INFO | WARNING | ERROR
  file: "data/trade_bot.log"
```

### Environment Variables (`.env`)

Required for testnet/live trading:
- `BINANCE_API_KEY` — Live Binance API key
- `BINANCE_API_SECRET` — Live Binance API secret
- `BINANCE_TESTNET_API_KEY` — Testnet API key
- `BINANCE_TESTNET_API_SECRET` — Testnet API secret

Optional:
- `TELEGRAM_BOT_TOKEN` — Telegram notification bot token
- `TELEGRAM_CHAT_ID` — Telegram chat ID for alerts
- `DASHBOARD_API_KEY` — API key for dashboard authentication (leave empty to disable)

## Development

### Running Tests

```bash
# All tests
pytest

# With coverage report
pytest --cov=src --cov-report=term-missing

# Specific test file
pytest tests/test_grid_engine.py

# By marker
pytest -m unit
pytest -m integration
```

### Code Style & Linting

```bash
# Format with black (if available) or ruff
ruff format src/ tests/

# Lint
ruff check src/ tests/

# Fix issues automatically
ruff check --fix src/ tests/

# Type checking
mypy src/  # if mypy is installed
```

### Pre-commit Checks

Before committing, ensure:
1. Tests pass: `pytest`
2. Linting passes: `ruff check`
3. No hardcoded secrets in `.env` or config files

## Data Models

All core data structures use Pydantic for validation:

- **Order** — Buy/sell orders with price, amount, status, grid level
- **Trade** — Executed orders with fill price, fee, realized P&L
- **GridState** — Current state of a grid (levels, active orders, running status)
- **Balance** — Asset balance (free + locked)

See `src/storage/models.py` for full definitions.

## Logging

Logging is configured via `src/utils/logger.py` with structlog:

**Console Output (Development):**
```
2024-04-03 10:15:42.123 [INFO] bot_starting mode=paper pairs=['BTC/USDT']
2024-04-03 10:15:43.456 [INFO] order_placed side=buy price=73500.0 amount=0.00061 grid_level=2
```

**JSON Output (Production):**
```json
{"timestamp": "2024-04-03T10:15:42Z", "level": "info", "event": "bot_starting", "mode": "paper"}
```

Set `LOG_FORMAT=json` environment variable to enable JSON output.

## Trading Mechanics

### Example: BTC/USDT Grid with $50 USDT

**Configuration:**
- Range: $72,000 - $76,000
- Grids: 5 levels
- Investment: $45 USDT
- Fee: 0.1%

**Grid Levels:**
```
$76,000 ← Sell 4
$75,000 ← Sell 3
$74,000 ← Sell 2 (middle)
$73,000 ← Sell 1
$72,000 ← Buy 1

Amount per level ≈ $9 USDT
```

**Profit Mechanics:**
1. Price drops to $72,500 → Buy at $72,000 (level 1)
2. Price rises to $74,000 → Sell at $74,000 (level 2) → Profit ~$18
3. Price drops back → Buy at $73,000 → Sell at $75,000 → Profit ~$18
4. Repeat cycle multiple times per day in volatile markets

**Backtest Results:**
```
$ trade-bot backtest -p BTC/USDT -s 2024-01-01 -u 2024-03-01 ...
Fetching BTC/USDT data from 2024-01-01 to 2024-03-01 (5m candles)...
Running backtest on 17280 candles...

Backtest Results for BTC/USDT
================================
Total Cycles: 342
Profitable Cycles: 287 (84%)
Win Rate: 83.9%
Total P&L: $127.45
Return: 283% over $45 investment
Max Drawdown: -$8.32 (-18.5%)
```

## Troubleshooting

### Bot fails to start: "Config file not found"
```bash
trade-bot --config config/default.yaml run
# Or create config/default.yaml from the template in config/
```

### Dashboard not accessible
```bash
# Check if running on correct port
curl http://127.0.0.1:8080/api/status
# Verify host/port in config/default.yaml
```

### Tests fail: "RuntimeError: no running event loop"
- Ensure pytest-asyncio is installed: `pip install pytest-asyncio`
- Tests use `pytest.mark.asyncio` to handle async functions

### Paper trading not matching live prices
- Paper mode matches at current market price with realistic fill simulation
- Use testnet for more realistic fills if available
- Check fee_rate in config (default 0.1%)

## Deployment

### Docker (Example Dockerfile)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .
COPY src/ src/
COPY config/ config/
ENV LOG_FORMAT=json
CMD ["trade-bot", "run"]
```

### Environment Variables (Production)
- Set `LOG_FORMAT=json` for structured logging
- Use secret manager for API keys (not .env)
- Set `DASHBOARD_API_KEY` to enable authentication

## Project Status

- Grid Engine: Fully functional
- Paper Trading: Fully functional
- Backtesting: Fully functional
- Dashboard: Functional (basic UI)
- Testnet Support: Planned
- Live Trading: Planned
- Telegram Notifications: Placeholder
- Mobile App: Not planned

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for:
- Development setup
- Running tests
- Code style requirements
- Pull request process

## License

[Add your license here]

## Support

For issues, questions, or feature requests, open an issue on GitHub.

---

**Last Updated:** 2024-04-03
**Version:** 0.1.0
