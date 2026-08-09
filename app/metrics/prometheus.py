from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUEST_DURATION_BUCKETS: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of incoming HTTP requests.",
    labelnames=("method", "endpoint", "status"),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Duration of incoming HTTP requests in seconds.",
    labelnames=("method", "endpoint"),
    buckets=HTTP_REQUEST_DURATION_BUCKETS,
)

EVENTS_PROVIDER_REQUESTS_TOTAL = Counter(
    "events_provider_requests_total",
    "Total number of requests to Events Provider API.",
    labelnames=("endpoint", "status"),
)

EVENTS_PROVIDER_REQUEST_DURATION_SECONDS = Histogram(
    "events_provider_request_duration_seconds",
    "Duration of requests to Events Provider API in seconds.",
    labelnames=("endpoint",),
    buckets=HTTP_REQUEST_DURATION_BUCKETS,
)

TICKETS_CREATED_TOTAL = Gauge(
    "tickets_created_total",
    "Total number of tickets stored in the database.",
)

TICKETS_CANCELLED_TOTAL = Gauge(
    "tickets_cancelled_total",
    "Total number of cancelled tickets stored in the database.",
)

EVENTS_TOTAL = Gauge(
    "events_total",
    "Total number of events stored in the database.",
)

CACHE_HITS_TOTAL = Counter(
    "cache_hits_total",
    "Total number of cache hits for available seats.",
)

CACHE_MISSES_TOTAL = Counter(
    "cache_misses_total",
    "Total number of cache misses for available seats.",
)
