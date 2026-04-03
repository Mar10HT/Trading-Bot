# Documentation Index

<!-- AUTO-GENERATED -->

**Last Updated:** 2024-04-03

## Quick Navigation

| Document | Purpose | Audience |
|----------|---------|----------|
| [../README.md](../README.md) | Project overview, features, architecture | Everyone |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup, testing, code style | Contributors |
| [ENV.md](ENV.md) | Environment variables configuration | Operators, developers |

## Documentation Structure

### Getting Started

1. **[../README.md](../README.md)** — Start here
   - Project overview and features
   - Quick start (installation, running bot)
   - Architecture overview
   - Configuration basics
   - Trading mechanics explanation
   - Troubleshooting common issues

### Configuration

2. **[ENV.md](ENV.md)** — Environment variable reference
   - All environment variables explained
   - Security best practices
   - Setup by trading mode (paper/testnet/live)
   - Troubleshooting guide

3. **[../config/default.yaml](../config/default.yaml)** — YAML configuration template
   - Trading pairs configuration
   - Risk management settings
   - Exchange parameters
   - Dashboard settings
   - Logging configuration

### Development

4. **[CONTRIBUTING.md](CONTRIBUTING.md)** — Developer guide
   - Development setup
   - Running and writing tests
   - Code style and linting standards
   - Git workflow and conventions
   - Architecture guidelines
   - Feature development process

### Source Code

Key modules with inline documentation:

- **Core Trading Logic** (`src/core/`)
  - `grid_engine.py` — Grid level calculation and state
  - `order_manager.py` — Order lifecycle management
  - `position_tracker.py` — P&L tracking
  - `risk_manager.py` — Risk enforcement and kill switches

- **Strategy** (`src/strategy/`)
  - `grid_strategy.py` — Single-pair trading loop
  - `multi_pair_manager.py` — Multi-pair coordinator

- **Exchange Integration** (`src/exchange/`)
  - `base.py` — Abstract exchange interface
  - `paper.py` — Paper trading simulator

- **Web Dashboard** (`src/dashboard/`)
  - `app.py` — FastAPI application
  - `routes/` — API endpoints (status, trades, pnl, controls)

- **Data Persistence** (`src/storage/`)
  - `database.py` — SQLite operations
  - `models.py` — Pydantic data models

- **Utilities** (`src/utils/`)
  - `config.py` — Configuration loading and validation
  - `logger.py` — Structured logging setup
  - `helpers.py` — Utility functions

## Feature Guides

### Running the Bot

```bash
# Paper trading (simulated)
trade-bot run

# Custom configuration
trade-bot --config config/custom.yaml run

# View grid setup
trade-bot info

# Backtest strategy
trade-bot backtest --pair BTC/USDT --since 2024-01-01 --until 2024-03-01 \
  --lower 72000 --upper 76000 --grids 5 --investment 45
```

### Testing

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=src --cov-report=term-missing

# Specific test
pytest tests/test_grid_engine.py -v
```

### Code Quality

```bash
# Format code
ruff format src/

# Check for issues
ruff check src/

# Fix automatically
ruff check --fix src/
```

## Architecture Quick Reference

**Main Components:**
- **GridEngine** — Calculates price levels and trading actions
- **OrderManager** — Manages order lifecycle (place, fill, cancel)
- **PositionTracker** — Tracks cost basis and P&L
- **RiskManager** — Enforces limits and kill switches
- **GridStrategy** — Orchestrates single-pair trading loop
- **MultiPairManager** — Coordinates multiple pairs
- **PaperExchange** — Simulates trading without real capital
- **Database** — Persists orders and trades to SQLite
- **Dashboard** — FastAPI web UI with real-time updates

**Data Flow:**
```
Config (YAML) → BotConfig (Pydantic)
                    ↓
            MultiPairManager
                ├─ GridStrategy (BTC/USDT)
                │   ├─ GridEngine
                │   ├─ OrderManager
                │   ├─ PositionTracker
                │   └─ RiskManager
                └─ GridStrategy (ETH/USDT)
                    └─ ...

                    ↓
                PaperExchange (or Real Exchange)
                    ↓
                Database (SQLite)
                    ↓
                Dashboard (FastAPI)
```

## Troubleshooting Guide

| Issue | Solution | Details |
|-------|----------|---------|
| Bot won't start | Check config file path | `trade-bot --config config/default.yaml run` |
| Dashboard not accessible | Check host/port in config | Default: `http://127.0.0.1:8080` |
| Tests fail with asyncio error | Install pytest-asyncio | `pip install pytest-asyncio` |
| Paper trading P&L doesn't match | Check fee_rate, slippage | Paper mode is simplified simulation |
| Ruff checks fail | Run auto-fix | `ruff check --fix src/` |

See [CONTRIBUTING.md](CONTRIBUTING.md#troubleshooting) for more.

## External Resources

- **Python:** [python.org](https://www.python.org/)
- **Pytest:** [pytest.org](https://docs.pytest.org/)
- **FastAPI:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
- **Pydantic:** [docs.pydantic.dev](https://docs.pydantic.dev/)
- **CCXT:** [docs.ccxt.com](https://docs.ccxt.com/)
- **Binance API:** [binance-docs.github.io](https://binance-docs.github.io/)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:
- Setting up development environment
- Writing tests
- Code style standards
- Pull request process
- Security checks

## Support & Issues

For bugs, feature requests, or questions:
1. Check [CONTRIBUTING.md](CONTRIBUTING.md#troubleshooting) troubleshooting section
2. Review [ENV.md](ENV.md#troubleshooting) for configuration issues
3. Open an issue on GitHub with reproduction steps

<!-- END AUTO-GENERATED -->
