"""Shared pytest configuration and fixtures."""
import logging

import pytest
import structlog


@pytest.fixture(autouse=True)
def silence_logging():
    """Suppress log output during tests to keep output clean and fast."""
    structlog.configure(
        processors=[structlog.processors.KeyValueRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)
