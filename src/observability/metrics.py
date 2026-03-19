"""Prometheus-style metrics for observability.

Per CONTEXT.md decisions:
- Counters: webhooks_received_total, validation_failures_total, records_added_total
- Latency histogram: processing_latency_seconds with p50/p95/p99 buckets

Uses prometheus-client library which provides:
- Thread-safe counter/histogram increments
- /metrics endpoint support (optional, can use generate_latest)
- Automatic percentile calculation from histogram buckets
"""

from prometheus_client import Counter, Histogram

# Webhook counters
webhooks_received = Counter(
    "webhooks_received_total",
    "Total number of webhooks received",
    ["type"],  # Labels: sync, auth, forward, unknown
)

validation_failures = Counter(
    "validation_failures_total",
    "Total number of validation failures",
    ["schema_name"],  # Label: which schema failed
)

records_added = Counter(
    "records_added_total",
    "Total number of records successfully added",
)

# Processing latency histogram
# Buckets chosen for p50/p95/p99 visibility with typical webhook processing
# Expected range: 10ms to 5s
processing_latency = Histogram(
    "processing_latency_seconds",
    "Webhook background processing latency in seconds",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)
