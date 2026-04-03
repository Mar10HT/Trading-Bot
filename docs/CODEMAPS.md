# Trade Bot Codemaps

<!-- AUTO-GENERATED -->

Complete architectural overview of the Trade Bot codebase.

**Last Updated:** 2024-04-03

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       CLI Entry Point                           │
│                    (src/main.py — Click)                        │
│  run │ backtest │ info │ help                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
┌──────────────────┐          ┌──────────────────┐
│  Bot Core        │          │  Backtester      │
│  (Main loop)     │          │  (Historical)    │
└────────┬─────────┘          └──────────────────┘
         │
    ┌────┴────┐
    │          │
    ▼          ▼
┌─────────────────────────────────────┐
│   MultiPairManager                  │
│   (Coordinates multiple pairs)      │
└────────┬─────────────────────────────┘
         │
    ┌────┴────┬────────┬───────────┐
    │         │        │           │
    ▼         ▼        ▼           ▼
GridStrategy GridStrategy GridStrategy ...
(BTC/USDT)   (ETH/USDT)   (ALT/USDT)

    ▼
┌──────────────────────────────────────┐
│     GridStrategy (Single Pair)       │
│                                      │
│  ├─ GridEngine                       │
│  ├─ OrderManager                     │
│  ├─ PositionTracker                  │
│  └─ RiskManager                      │
└─────────────┬────────────────────────┘
              │
    ┌─────────┴──────────┐
    │                    │
    ▼                    ▼
┌───────────────┐   ┌────────────────┐
│ PaperExchange │   │ Database       │
│ (Simulator)   │   │ (SQLite)       │
└───────────────┘   └────────────────┘
                           │
                    ┌──────┴───────┐
                    │              │
                    ▼              ▼
              Orders/Trades    GridState

                    │
                    ▼
            ┌──────────────────┐
            │ FastAPI Dashboard│
            │ (http://8080)    │
            └──────────────────┘
                    │
            ┌───────┴────────┐
            │                │
            ▼                ▼
        REST API         WebSocket
      (status, trades)  (live updates)
```

## Module Dependency Map

```
src/
├── main.py [ENTRY]
│   └─→ src.utils.config
│   └─→ src.utils.logger
│   └─→ src.strategy.multi_pair_manager
│
├── core/ [CORE LOGIC]
│   ├── grid_engine.py [NO DEPS]
│   │   └─→ src.storage.models
│   │
│   ├── order_manager.py
│   │   └─→ src.storage.models
│   │
│   ├── position_tracker.py
│   │   └─→ src.storage.models
│   │
│   └── risk_manager.py [NO DEPS]
│
├── strategy/ [ORCHESTRATION]
│   ├── grid_strategy.py
│   │   └─→ src.core.*
│   │   └─→ src.storage.database
│   │
│   └── multi_pair_manager.py
│       └─→ src.strategy.grid_strategy
│       └─→ src.dashboard.state
│
├── exchange/ [EXCHANGE ABSTRACTION]
│   ├── base.py [ABSTRACT]
│   └── paper.py [IMPLEMENTATION]
│
├── storage/ [PERSISTENCE]
│   ├── models.py [PYDANTIC MODELS]
│   └── database.py
│       └─→ src.storage.models
│
├── dashboard/ [WEB UI]
│   ├── app.py
│   │   └─→ src.dashboard.routes.*
│   │
│   ├── state.py [SHARED STATE]
│   │
│   ├── routes/
│   │   ├── status.py
│   │   ├── trades.py
│   │   ├── pnl.py
│   │   └── controls.py
│   │   └─→ src.dashboard.state
│   │
│   ├── ws.py [WEBSOCKET]
│   │   └─→ src.dashboard.state
│   │
│   └── deps.py [DEPENDENCIES]
│
├── backtest/ [TESTING]
│   ├── backtester.py
│   │   └─→ src.core.grid_engine
│   │
│   ├── data_fetcher.py
│   │   └─→ ccxt
│   │
│   └── report.py
│
├── notifications/
│   └── (placeholder for Telegram)
│
└── utils/ [INFRASTRUCTURE]
    ├── config.py
    │   └─→ pydantic, pyyaml
    │
    ├── logger.py
    │   └─→ structlog
    │
    └── helpers.py [UTILITIES]
```

## Data Model Hierarchy

```
Order (Pydantic)
├── id: str
├── pair: str
├── side: OrderSide (ENUM: BUY | SELL)
├── price: float
├── amount: float
├── status: OrderStatus (ENUM: PENDING | OPEN | FILLED | CANCELLED)
├── grid_level: int
├── created_at: datetime
├── filled_at: datetime | None
└── fee: float

Trade (Pydantic) — Executed order
├── id: int
├── pair: str
├── side: OrderSide
├── price: float
├── amount: float
├── fee: float
├── realized_pnl: float
├── grid_level: int
└── timestamp: datetime

GridState (Pydantic) — Current grid status
├── pair: str
├── lower_price: float
├── upper_price: float
├── num_grids: int
├── levels: list[float]
├── active_buy_levels: list[int]
├── active_sell_levels: list[int]
├── investment: float
├── is_running: bool
└── created_at: datetime

Balance (Pydantic)
├── asset: str
├── free: float
└── locked: float
```

## Configuration Hierarchy

```
Environment Variables (.env)
├── BINANCE_API_KEY / BINANCE_API_SECRET
├── BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET
├── TELEGRAM_BOT_TOKEN
├── TELEGRAM_CHAT_ID
├── DASHBOARD_API_KEY
└── LOG_FORMAT

        ↓ (loaded by load_env())

YAML Configuration (config/default.yaml)
└─→ BotConfig (Pydantic)
    ├── mode: str (paper | testnet | live)
    │
    ├── pairs: list[PairConfig]
    │   ├── pair: str
    │   ├── lower_price: float
    │   ├── upper_price: float
    │   ├── num_grids: int
    │   └── investment: float
    │
    ├── risk: RiskConfig
    │   ├── max_total_investment: float
    │   ├── min_order_value: float
    │   ├── max_drawdown_pct: float
    │   ├── max_drawdown_absolute: float
    │   └── reserve_pct: float
    │
    ├── exchange: ExchangeConfig
    │   ├── fee_rate: float
    │   └── poll_interval_seconds: int
    │
    ├── dashboard: DashboardConfig
    │   ├── host: str
    │   └── port: int
    │
    └── logging: LoggingConfig
        ├── level: str
        └── file: str
```

## API Routes

```
FastAPI Dashboard Server (http://127.0.0.1:8080)

GET  /api/status          → Current balance, grid state, P&L
GET  /api/trades          → Trade history
GET  /api/trades?limit=50 → Paginated trade history
GET  /api/pnl             → P&L metrics and statistics

POST /api/controls/start  → Start trading
POST /api/controls/stop   → Stop trading
POST /api/controls/pause  → Pause (resume from last state)

WS   /ws                  → WebSocket for real-time updates
```

## Database Schema (SQLite)

```
trades
├── id (INTEGER PRIMARY KEY)
├── pair (TEXT)
├── side (TEXT) — 'buy' or 'sell'
├── price (REAL)
├── amount (REAL)
├── fee (REAL)
├── realized_pnl (REAL)
├── grid_level (INTEGER)
└── timestamp (TEXT, ISO datetime)

orders
├── id (TEXT PRIMARY KEY)
├── pair (TEXT)
├── side (TEXT)
├── price (REAL)
├── amount (REAL)
├── status (TEXT) — pending|open|filled|cancelled
├── grid_level (INTEGER)
├── created_at (TEXT, ISO datetime)
├── filled_at (TEXT, nullable)
└── fee (REAL)
```

## Class Hierarchy

```
AbstractExchange (abstract)
├── paper.py → PaperExchange
└── (future) ccxt_exchange.py → CcxtExchange

Database
└── SQLite operations (async, aiosqlite)

RiskManager
└── Stateless, pure functions

GridEngine
└── Stateful, tracks grid levels and order states

OrderManager
└── Manages order lifecycle

PositionTracker
└── Tracks cost basis and P&L

GridStrategy
└── Orchestrates single-pair trading loop

MultiPairManager
└── Coordinates multiple GridStrategy instances

FastAPI + Starlette
└── Dashboard web server
```

## Test Coverage Map

```
tests/
├── conftest.py
│   ├── db fixture (in-memory SQLite)
│   ├── paper_exchange fixture
│   └── config fixtures
│
├── test_grid_engine.py [UNIT]
│   ├── test_grid_levels
│   ├── test_order_amount_calculation
│   ├── test_grid_state_initialization
│   ├── test_investment_validation
│   └── test_config_validation
│
├── test_order_manager.py [UNIT]
│   ├── test_place_order
│   ├── test_fill_order
│   ├── test_cancel_order
│   └── test_order_state_transitions
│
├── test_position_tracker.py [UNIT]
│   ├── test_track_entry
│   ├── test_calculate_pnl
│   ├── test_multiple_entries
│   └── test_position_closure
│
├── test_risk_manager.py [UNIT]
│   ├── test_position_limit_enforcement
│   ├── test_drawdown_kill_switch
│   └── test_min_order_value
│
└── test_backtester.py [INTEGRATION]
    ├── test_backtest_on_sample_data
    ├── test_profitability_calculation
    ├── test_fee_deduction
    └── test_multiple_cycle_trading
```

## Key Algorithms

### Grid Level Calculation
```
levels = [lower + i * step for i in range(num_grids + 1)]
where step = (upper - lower) / num_grids

Example: lower=100, upper=200, num_grids=5
levels = [100, 120, 140, 160, 180, 200]
```

### Order Amount Per Level
```
amount_per_level = investment / (num_grids * current_price)

Example: $45 investment, 5 grids, $73,500 BTC price
amount_per_level = 45 / (5 * 73500) = 0.000122... BTC
```

### Realized P&L Calculation
```
For each matched pair (buy + sell):
  profit = (sell_price - buy_price) * amount
  fee_cost = amount * (buy_fee + sell_fee)
  realized_pnl = profit - fee_cost

Accumulate across all closed positions.
```

### Kill Switch Triggers
```
1. Drawdown % → max_drawdown_pct = 20%
   if (initial_balance - current_balance) / initial_balance > 0.20:
       KILL

2. Drawdown Absolute → max_drawdown_absolute = $10
   if (initial_balance - current_balance) > 10:
       KILL
```

## Async Concurrency Model

```
asyncio.gather(
    manager.start_all(),      # Main trading loop
    server.serve(),           # FastAPI dashboard
)

Each pair runs in its own asyncio Task:
  while _running:
      1. Fetch price (async)
      2. Calculate grid actions
      3. Place/cancel orders (async)
      4. Update database (async)
      5. await asyncio.sleep(poll_interval)

Dashboard runs separately in uvicorn:
  - Reads shared state (no locking — immutable updates)
  - Handles WebSocket connections
  - Non-blocking JSON responses
```

## Error Handling Strategy

```
Level 1: User Input Validation (Pydantic)
├── YAML config validation
├── Command-line argument validation
└── API request validation

Level 2: System-Level Error Handling
├── Exchange connection errors → log and retry
├── Database errors → transaction rollback
├── WebSocket disconnection → auto-reconnect
└── Invalid order states → log and skip

Level 3: Risk Management
├── Kill switch triggers → stop bot
├── Position limit exceeded → reject order
├── Insufficient balance → skip order
└── Order fill failures → log and retry
```

## Logging Events

```
bot_starting          → Bot initialization
bot_stopping          → Graceful shutdown

grid_initialized      → Grid created
order_placed          → Order submitted
order_filled          → Order executed
order_cancelled       → Order cancelled
position_closed       → Trade pair executed

price_update          → Price tick (debug level)
pnl_update            → P&L changed
balance_changed       → Account balance update

drawdown_alert        → Risk threshold approaching
kill_switch_triggered → Max loss exceeded

dashboard_starting    → Web server started
ws_client_connected   → WebSocket client joined
ws_client_disconnected → WebSocket client left
```

## Performance Characteristics

```
Time Complexity:
- Grid level calculation: O(n) where n = num_grids
- Order matching: O(m) where m = active_orders
- Position tracking: O(1) amortized
- P&L calculation: O(k) where k = num_trades

Space Complexity:
- Active orders per pair: O(n)
- Trade history: O(k) unbounded growth (database)
- Dashboard state: O(1) fixed size
- Grid state: O(n)

Async Concurrency:
- N trading pairs = N concurrent asyncio.Tasks
- Dashboard WebSocket = separate event loop
- No thread locks (Python GIL friendly)
```

## Related Documentation

- [../README.md](../README.md) — Project overview and getting started
- [CONTRIBUTING.md](CONTRIBUTING.md) — Development guide
- [ENV.md](ENV.md) — Environment variables reference
- [../config/default.yaml](../config/default.yaml) — Configuration template

<!-- END AUTO-GENERATED -->
