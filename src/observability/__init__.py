"""Observability module for logging and metrics."""

from .logging import configure_logging, get_logger
from .metrics import (
    processing_latency,
    records_added,
    validation_failures,
    webhooks_received,
)

__all__ = [
    "configure_logging",
    "get_logger",
    "webhooks_received",
    "validation_failures",
    "records_added",
    "processing_latency",
]
