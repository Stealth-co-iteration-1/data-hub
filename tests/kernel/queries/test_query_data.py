"""Tests for QueryData query."""
import dataclasses

from src.kernel.queries import DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT, QueryData
from src.kernel.domain import CorrelationContext


def test_query_data_has_required_model_field():
    """QueryData requires model field."""
    query = QueryData(model="contacts")
    assert query.model == "contacts"


def test_query_data_has_default_limit():
    """QueryData limit defaults to DEFAULT_QUERY_LIMIT."""
    query = QueryData(model="contacts")
    assert query.limit == DEFAULT_QUERY_LIMIT
    assert query.limit == 100


def test_query_data_has_default_filters_none():
    """QueryData filters defaults to None."""
    query = QueryData(model="contacts")
    assert query.filters is None


def test_query_data_accepts_filters():
    """QueryData accepts filter dict."""
    # V1: Only connection_id filtering is supported (no JSON field filtering)
    filters = {"connection_id": "abc"}
    query = QueryData(model="contacts", filters=filters)
    assert query.filters == filters


def test_query_data_has_correlation_context():
    """QueryData has optional correlation_context with default."""
    query = QueryData(model="contacts")
    assert isinstance(query.correlation, CorrelationContext)
    assert query.correlation.correlation_id is not None


def test_query_data_is_dataclass():
    """QueryData is a dataclass."""
    assert dataclasses.is_dataclass(QueryData)


def test_query_data_has_no_offset_field():
    """QueryData does NOT have offset field (deferred to future phase)."""
    # Offset pagination deferred - verify field doesn't exist
    assert not hasattr(QueryData(model="test"), "offset") or \
           "offset" not in [f.name for f in dataclasses.fields(QueryData)]


def test_max_query_limit_is_1000():
    """MAX_QUERY_LIMIT is 1000."""
    assert MAX_QUERY_LIMIT == 1000


def test_default_query_limit_is_100():
    """DEFAULT_QUERY_LIMIT is 100."""
    assert DEFAULT_QUERY_LIMIT == 100
