"""Shared state between the bot and the dashboard.

The bot writes to this state, and the dashboard reads from it.
This avoids tight coupling between the two.
"""
from src.storage.database import Database
from src.strategy.multi_pair_manager import MultiPairManager

# These are set by main.py when the bot starts
manager: MultiPairManager | None = None
db: Database | None = None
bot_mode: str = "paper"
