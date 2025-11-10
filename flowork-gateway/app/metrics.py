########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\metrics.py total lines 125 
########################################################################

from typing import Optional
from flask import Blueprint, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
REQUEST_LATENCY = Histogram(
    "gateway_request_latency_seconds",
    "Latency of HTTP requests in seconds.",
    ["method", "endpoint"],
)
REQUEST_COUNT = Counter(
    "gateway_requests_total",
    "Total number of HTTP requests handled.",
    ["method", "endpoint", "status"],
)
IN_PROGRESS = Gauge(
    "gateway_inprogress_requests",
    "Number of in-progress HTTP requests.",
)
GATEWAY_ENGINE_HEARTBEAT = Counter(
    "gateway_engine_heartbeat_total",
    "Total heartbeats received from engines.",
    ["engine_id"],
)
GATEWAY_ENGINE_STATUS = Gauge(
    "gateway_engine_status",
    "Status of registered engines (1=online, 0=offline).",
    ["engine_id"],
)
QUEUE_DEPTH = Gauge(
    "gateway_queue_depth_total",
    "Current number of jobs in the queue.",
)
JOBS_ENQUEUED_TOTAL = Counter(
    "gateway_jobs_enqueued_total",
    "Total jobs successfully enqueued into internal queue."
)
JOBS_REJECTED_TOTAL = Counter(
    "gateway_jobs_rejected_total",
    "Total jobs rejected by Gateway (e.g. bad request, auth fail).",
    ["reason"]
)
JOBS_DROPPED_TOTAL = Counter(
    "gateway_jobs_dropped_total",
    "Total jobs dropped due to backpressure or no engine.",
    ["reason"]
)
JOB_ENQUEUE_LATENCY = Histogram(
    "gateway_job_enqueue_latency_seconds",
    "Time taken to process an enqueue request."
)
CIRCUIT_OPEN = Gauge(
    "gateway_circuit_open",
    "Whether the circuit breaker to Core is open (1) or closed (0).",
    ["service"],
)
RATE_LIMIT_HIT = Counter(
    "gateway_rate_limit_hit_total",
    "Total number of requests rejected by rate limiter.",
    ["scope"] # e.g., "user", "engine", "global"
)
IDEMPOTENCY_HIT_LOCAL = Counter(
    "gateway_idem_hit_local_total",
    "Total idempotent requests served from local cache."
)
IDEMPOTENCY_HIT_GLOBAL = Counter(
    "gateway_idem_hit_global_total",
    "Total idempotent requests served from global (D1) cache."
)
ENQ_TOTAL = Counter(
    "gateway_enq_v1_total",
    "Total enqueue requests to V1 API.",
    ["outcome"]
)
ENQ_IDEM_HIT = Counter(
    "gateway_enq_v1_idem_hit_total",
    "Idempotency hits in V1 API."
)
ENQ_RATE_LIMIT_USER = Counter(
    "gateway_enq_v1_rl_user_total",
    "User rate limit hits in V1 API."
)
ENQ_RATE_LIMIT_ENGINE = Counter(
    "gateway_enq_v1_rl_engine_total",
    "Engine rate limit hits in V1 API."
)
ENQ_USER_WINDOW_SIZE = Gauge(
    "gateway_enq_v1_window_user",
    "Current user rate limit window size.",
    ["user_id"]
)
ENQ_ENGINE_WINDOW_SIZE = Gauge(
    "gateway_enq_v1_window_engine",
    "Current engine rate limit window size.",
    ["engine_id"]
)
gateway_enqueue_engine_window_size = ENQ_ENGINE_WINDOW_SIZE
_metrics_bp: Optional[Blueprint] = None
def register_metrics(app):
    """
    Attach /metrics exporter endpoint to the given Flask app.
    This function is intentionally idempotent.
    """
    global _metrics_bp
    if getattr(app, "_prom_metrics_registered", False):
        return
    _metrics_bp = Blueprint("metrics_exporter", __name__)
    @_metrics_bp.route("/metrics")
    def _export():
        data = generate_latest()
        return Response(data, mimetype=CONTENT_TYPE_LATEST)
    app.register_blueprint(_metrics_bp)
    app._prom_metrics_registered = True
def init_app_metrics(app):
    register_metrics(app)
