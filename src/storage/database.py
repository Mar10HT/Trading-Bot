import json
from datetime import datetime
from pathlib import Path

import aiosqlite

from src.storage.models import Order, OrderSide, OrderStatus, Trade

DB_PATH = Path("data/trade_bot.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    pair TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    grid_level INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    filled_at TEXT,
    fee REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    fee REAL NOT NULL DEFAULT 0.0,
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    grid_level INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS grid_states (
    pair TEXT PRIMARY KEY,
    config_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS balances (
    asset TEXT PRIMARY KEY,
    free REAL NOT NULL DEFAULT 0.0,
    locked REAL NOT NULL DEFAULT 0.0
);
"""


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    async def save_order(self, order: Order):
        await self._db.execute(
            """INSERT OR REPLACE INTO orders
               (id, pair, side, price, amount, status, grid_level, created_at, filled_at, fee)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                order.id, order.pair, order.side.value, order.price,
                order.amount, order.status.value, order.grid_level,
                order.created_at.isoformat(),
                order.filled_at.isoformat() if order.filled_at else None,
                order.fee,
            ),
        )
        await self._db.commit()

    async def get_open_orders(self, pair: str | None = None) -> list[Order]:
        if pair:
            cursor = await self._db.execute(
                "SELECT * FROM orders WHERE status = 'open' AND pair = ?", (pair,)
            )
        else:
            cursor = await self._db.execute("SELECT * FROM orders WHERE status = 'open'")
        rows = await cursor.fetchall()
        return [self._row_to_order(row) for row in rows]

    async def save_trade(self, trade: Trade):
        await self._db.execute(
            """INSERT INTO trades
               (pair, side, price, amount, fee, realized_pnl, grid_level, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade.pair, trade.side.value, trade.price, trade.amount,
                trade.fee, trade.realized_pnl, trade.grid_level,
                trade.timestamp.isoformat(),
            ),
        )
        await self._db.commit()

    async def get_trades(self, pair: str | None = None, limit: int = 100) -> list[Trade]:
        if pair:
            cursor = await self._db.execute(
                "SELECT * FROM trades WHERE pair = ? ORDER BY timestamp DESC LIMIT ?",
                (pair, limit),
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
        rows = await cursor.fetchall()
        return [self._row_to_trade(row) for row in rows]

    async def save_grid_state(self, pair: str, state_dict: dict):
        await self._db.execute(
            """INSERT OR REPLACE INTO grid_states (pair, config_json, updated_at)
               VALUES (?, ?, ?)""",
            (pair, json.dumps(state_dict), datetime.utcnow().isoformat()),
        )
        await self._db.commit()

    async def get_grid_state(self, pair: str) -> dict | None:
        cursor = await self._db.execute(
            "SELECT config_json FROM grid_states WHERE pair = ?", (pair,)
        )
        row = await cursor.fetchone()
        if row:
            return json.loads(row["config_json"])
        return None

    async def update_balance(self, asset: str, free: float, locked: float):
        await self._db.execute(
            """INSERT OR REPLACE INTO balances (asset, free, locked)
               VALUES (?, ?, ?)""",
            (asset, free, locked),
        )
        await self._db.commit()

    async def get_total_pnl(self) -> float:
        cursor = await self._db.execute("SELECT COALESCE(SUM(realized_pnl), 0) FROM trades")
        row = await cursor.fetchone()
        return row[0]

    @staticmethod
    def _row_to_order(row) -> Order:
        return Order(
            id=row["id"],
            pair=row["pair"],
            side=OrderSide(row["side"]),
            price=row["price"],
            amount=row["amount"],
            status=OrderStatus(row["status"]),
            grid_level=row["grid_level"],
            created_at=datetime.fromisoformat(row["created_at"]),
            filled_at=datetime.fromisoformat(row["filled_at"]) if row["filled_at"] else None,
            fee=row["fee"],
        )

    @staticmethod
    def _row_to_trade(row) -> Trade:
        return Trade(
            id=row["id"],
            pair=row["pair"],
            side=OrderSide(row["side"]),
            price=row["price"],
            amount=row["amount"],
            fee=row["fee"],
            realized_pnl=row["realized_pnl"],
            grid_level=row["grid_level"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )
