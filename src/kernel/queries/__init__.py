"""Queries - read-only operations.

Queries represent user intentions to retrieve data.
Unlike commands, queries do not modify state or emit events.
"""
from .query_data import DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT, QueryData

__all__ = ["QueryData", "DEFAULT_QUERY_LIMIT", "MAX_QUERY_LIMIT"]
