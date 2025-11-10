########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\dispatch.py total lines 133 
########################################################################

"""
(Roadmap 2.1, 2.4, 3.2, 4.2)
Handles the internal dispatching of jobs from the GUI/Cluster
to the local queue (and eventually to the Core Engine).
- Implements local bounded queue (Backpressure).
- Implements local idempotency.
- Implements global idempotency check (via D1).
- Implements rate limiting hook (via dispatcher).
- Implements engine selection (Roadmap 3.2).
"""
import time
from flask import Blueprint, request, jsonify, current_app
from app.queue.dispatcher import get_queue_dispatcher, QueueFullError, NoEngineAvailableError
from app.idem.global_client import GlobalIdempotencyClient
from app.rl.limiter import RateLimitExceeded
from app.idem.store import IdemStore
from app.security.guards import gateway_token_required, admin_token_required # (MODIFIED: Added admin_token_required)
from app.engine.registry import engine_registry # (ADDED FOR ROADMAP 3.2)
from app.engine.router import engine_router # (ADDED FOR ROADMAP 3.2)
from app.metrics import (
    JOBS_ENQUEUED_TOTAL,
    JOBS_REJECTED_TOTAL,
    JOBS_DROPPED_TOTAL,
    JOB_ENQUEUE_LATENCY,
    RATE_LIMIT_HIT,
    IDEMPOTENCY_HIT_LOCAL,
    IDEMPOTENCY_HIT_GLOBAL
)
dispatch_bp = Blueprint('dispatch_bp', __name__)
@dispatch_bp.route('/internal/jobs/enqueue', methods=['POST'])
@gateway_token_required
def enqueue_job():
    """
    The primary endpoint for enqueuing a new job into the system.
    This is called by the GUI (Cloudflare) via the tunnel.
    """
    start_time = time.monotonic()
    dispatcher = get_queue_dispatcher()
    idem_store = IdemStore()
    data = request.get_json()
    if not data:
        JOBS_REJECTED_TOTAL.labels(reason='no_data').inc()
        return jsonify({"error": "No data provided"}), 400
    job_id = data.get('job_id')
    job_key = data.get('job_key') # (Roadmap 3.2) Used for routing/sharding
    idempotency_key = request.headers.get('Idempotency-Key')
    try:
        dispatcher.check_rate_limit(request.remote_addr)
    except RateLimitExceeded:
        RATE_LIMIT_HIT.inc()
        JOBS_REJECTED_TOTAL.labels(reason='rate_limit').inc()
        return jsonify({"error": "Rate limit exceeded"}), 429
    if idempotency_key:
        if idem_store.check_and_store(idempotency_key):
            IDEMPOTENCY_HIT_LOCAL.inc()
            JOBS_REJECTED_TOTAL.labels(reason='idempotency_local').inc()
            current_app.logger.warn(f"[Dispatch] Local Idempotency hit: {idempotency_key}")
            return jsonify({"status": "accepted", "idempotency": "local_hit"}), 200
    if current_app.config.get("GLOBAL_IDEMPOTENCY_ENABLED", False):
        global_idem_client = GlobalIdempotencyClient(
            current_app.config["ETL_D1_URL"],
            current_app.config["ETL_D1_TOKEN"],
            current_app.config["ETL_API_KEY"]
        )
        try:
            is_duplicate = global_idem_client.check_global_idem(idempotency_key, job_id)
            if is_duplicate:
                IDEMPOTENCY_HIT_GLOBAL.inc()
                JOBS_REJECTED_TOTAL.labels(reason='idempotency_global').inc()
                current_app.logger.warn(f"[Dispatch] Global Idempotency hit: {idempotency_key}")
                return jsonify({"status": "accepted", "idempotency": "global_hit"}), 200
        except Exception as e:
            current_app.logger.error(f"[Dispatch] Global Idempotency check failed: {e}")
            JOBS_REJECTED_TOTAL.labels(reason='idem_global_fail').inc()
    try:
        dispatcher.dispatch(data, job_key)
        JOBS_ENQUEUED_TOTAL.inc()
        JOB_ENQUEUE_LATENCY.observe(time.monotonic() - start_time)
        return jsonify({"status": "queued", "job_id": job_id}), 202
    except QueueFullError:
        JOBS_DROPPED_TOTAL.labels(reason='queue_full').inc()
        current_app.logger.warn("[Dispatch] Queue full (Backpressure). Job dropped.")
        return jsonify({"error": "Queue is full, try again later"}), 503
    except NoEngineAvailableError:
        JOBS_DROPPED_TOTAL.labels(reason='no_engine').inc()
        current_app.logger.error("[Dispatch] No healthy engine available. Job dropped.")
        return jsonify({"error": "No healthy engine available"}), 503
    except Exception as e:
        JOBS_DROPPED_TOTAL.labels(reason='internal_error').inc()
        current_app.logger.error(f"[Dispatch] Failed to enqueue job: {e}")
        return jsonify({"error": "Internal server error"}), 500
@dispatch_bp.route('/dispatch/select-engine', methods=['POST'])
@admin_token_required
def select_engine_endpoint():
    """
    (ADDED FOR ROADMAP 3.2)
    Admin endpoint to test the engine selection and routing logic.
    Provides the current list of active engines and shows which
    engine *would* be selected for a given job_key.
    """
    data = request.get_json()
    if not data or 'job_key' not in data:
        return jsonify({"error": "Missing 'job_key' in request body"}), 400
    job_key = data['job_key']
    try:
        active_engines = engine_registry.get_active_engines()
        if not active_engines:
            return jsonify({
                "error": "No active engines available in the registry.",
                "active_engines": [],
                "job_key": job_key,
                "selected_engine_id": None
            }), 503 # Service Unavailable
        selected_engine_id = engine_router.select_engine(job_key, active_engines)
        active_engine_list = [
            {"id": engine.id, "url": engine.url, "last_heartbeat": engine.last_heartbeat_utc.isoformat()}
            for engine in active_engines
        ]
        return jsonify({
            "message": "Engine selection test successful.",
            "job_key": job_key,
            "active_engines": active_engine_list,
            "selected_engine_id": selected_engine_id
        }), 200
    except Exception as e:
        current_app.logger.error(f"[DispatchSelect] Error during engine selection test: {e}")
        return jsonify({"error": "Internal server error during selection test."}), 500
