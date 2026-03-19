"""Structured logging configuration using structlog.

Per CONTEXT.md decisions:
- JSON structured logging via structlog with JSON output
- Each log entry: correlation_id, timestamp, level, message, and context fields
- Sensitive data handling: Full payloads logged in dev only (ENV=development)
- Log validation error field paths but not values in non-dev environments
"""

import logging
import sys

import structlog
from structlog.contextvars import merge_contextvars

from src.config.settings import settings


def configure_logging() -> None:
    """Configure structlog for the application.

    Call once at application startup (in FastAPI lifespan).
    Uses contextvars for request-scoped correlation IDs.

    Configuration varies by environment:
    - development: Pretty console output with colors
    - staging/production: JSON output for log aggregation
    """
    # Set stdlib logging level
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # Shared processors
    shared_processors: list[structlog.types.Processor] = [
        merge_contextvars,  # MUST be first - merges request-scoped context
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.env == "development":
        # Development: colorful console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Staging/Production: JSON for log aggregation
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger.

    Args:
        name: Logger name (optional, defaults to calling module)

    Returns:
        Configured structlog BoundLogger
    """
    return structlog.get_logger(name)


def should_log_full_payload() -> bool:
    """Check if full payloads should be logged.

    Per CONTEXT.md: Full payloads logged in dev only.
    """
    return settings.env == "development"
