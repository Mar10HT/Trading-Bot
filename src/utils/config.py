from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class PairConfig(BaseModel):
    pair: str
    lower_price: float
    upper_price: float
    num_grids: int
    investment: float

    @field_validator("num_grids")
    @classmethod
    def grids_must_be_positive(cls, v: int) -> int:
        if v < 2:
            raise ValueError("num_grids must be at least 2")
        return v

    @field_validator("upper_price")
    @classmethod
    def upper_must_exceed_lower(cls, v: float, info) -> float:
        if "lower_price" in info.data and v <= info.data["lower_price"]:
            raise ValueError("upper_price must be greater than lower_price")
        return v


class RiskConfig(BaseModel):
    max_total_investment: float = 50.0
    min_order_value: float = 11.0
    max_drawdown_pct: float = 20.0
    max_drawdown_absolute: float = 10.0
    reserve_pct: float = 10.0


class ExchangeConfig(BaseModel):
    fee_rate: float = 0.001
    poll_interval_seconds: int = 10


class DashboardConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "data/trade_bot.log"


class BotConfig(BaseModel):
    mode: str = "paper"
    pairs: list[PairConfig] = []
    risk: RiskConfig = RiskConfig()
    exchange: ExchangeConfig = ExchangeConfig()
    dashboard: DashboardConfig = DashboardConfig()
    logging: LoggingConfig = LoggingConfig()

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("paper", "testnet", "live"):
            raise ValueError("mode must be one of: paper, testnet, live")
        return v


class EnvSettings(BaseSettings):
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_testnet_api_key: str = ""
    binance_testnet_api_secret: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def load_config(config_path: str | Path = "config/default.yaml") -> BotConfig:
    """Load bot configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    return BotConfig(**raw)


def load_env() -> EnvSettings:
    """Load environment variables from .env file."""
    return EnvSettings()
