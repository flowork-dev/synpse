########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\jobs.py total lines 72 
########################################################################

import time
import uuid
import threading
from typing import Dict, Any
from flask import Blueprint, request, jsonify
from app.ops.chaos import maybe_chaos           # Chaos injection (header-gated)
from app.ops.drain import is_draining           # Drain guard for rolling upgrades
from app.idem.global_client import atomic_get_or_create_global  # Global D1 idempotency
from app.metrics import RATE_LIMIT_HIT          # Metrics (rate-limit rejections)
jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/v1/jobs")
_rate_bucket: Dict[str, Dict[str, Any]] = {}
_rate_lock = threading.Lock()
_LIMIT_PER_WINDOW = 30  # requests
_WINDOW_SECONDS = 60    # seconds
def _rate_key(req) -> str:
    uid = req.headers.get("X-User-Id") or req.remote_addr or "anonymous"
    return f"user:{uid}"
def _rate_limited(req) -> bool:
    now = int(time.time())
    key = _rate_key(req)
    with _rate_lock:
        entry = _rate_bucket.get(key)
        if not entry or now - entry["ts"] >= _WINDOW_SECONDS:
            _rate_bucket[key] = {"ts": now, "count": 1}
            return False
        entry["count"] += 1
        return entry["count"] > _LIMIT_PER_WINDOW
@jobs_bp.post("/enqueue")
def enqueue_job():
    """
    Enqueue a job request with global idempotency (D1), chaos toggle, and drain guard.
    - If Idempotency-Key header repeats, return the winner job_id with 200.
    - Otherwise, create a new job_id and return 202 Accepted.
    """
    maybe_chaos()
    if is_draining():
        return jsonify({
            "status": "error",
            "message": "Gateway is draining for an upgrade. Please try again later.",
            "retry_after": 30
        }), 503
    if _rate_limited(request):
        RATE_LIMIT_HIT.labels(scope="user").inc()
        return jsonify({"error": "rate_limited", "retry_after": 10}), 429
    data = request.get_json(silent=True) or {}
    task_type = str(data.get("type", "generic")).strip()
    args = data.get("args", {})
    idem_key = request.headers.get("Idempotency-Key", "").strip()
    my_job_id = str(uuid.uuid4())
    if idem_key:
        winner = atomic_get_or_create_global(idem_key, job_id=my_job_id, ttl=3600)
        if winner and winner.get("job_id") != my_job_id:
            return jsonify({
                "ok": True,
                "cached": True,
                "job_id": winner.get("job_id"),
                "status": "already_enqueued",
            }), 200
    job_record = {
        "job_id": my_job_id,
        "type": task_type,
        "args": args,
        "queued_at": int(time.time()),
        "status": "queued"
    }
    return jsonify({"ok": True, "cached": False, "job": job_record}), 202
