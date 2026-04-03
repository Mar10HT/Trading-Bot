"""FastAPI security dependencies for the dashboard."""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.utils.config import EnvSettings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _get_settings() -> EnvSettings:
    return EnvSettings()


def require_api_key(key: str | None = Security(_api_key_header)) -> None:
    """Dependency that enforces API key authentication.

    Authentication is skipped when DASHBOARD_API_KEY is not set (dev mode).
    """
    settings = _get_settings()
    configured_key = settings.dashboard_api_key

    if not configured_key:
        # No key configured — skip auth (development mode)
        return

    if key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Set X-API-Key header.",
        )
