import logging
import os
import sys
from pathlib import Path

import structlog


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """Configure structlog with console and optional file output.

    Output format is controlled by LOG_FORMAT env var:
      - LOG_FORMAT=json  → JSON (suitable for log aggregators and production)
      - anything else    → human-readable console output (default for dev)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Ensure log directory exists
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Configure standard logging
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=handlers,
        force=True,
    )

    # Use JSON renderer when explicitly requested via env var (e.g. in Docker/production).
    # Default to human-readable console output for local development.
    use_json = os.getenv("LOG_FORMAT", "").lower() == "json"
    renderer = structlog.processors.JSONRenderer() if use_json else structlog.dev.ConsoleRenderer()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
