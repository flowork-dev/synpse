########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\ops\chaos.py total lines 40 
########################################################################

import os
import time
import random
from flask import Blueprint, request
chaos_bp = Blueprint('chaos_bp', __name__)
def _is_chaos_enabled() -> bool:
    """
    Checks if chaos mode is enabled for this request.
    Requires 'X-Chaos' header to be present and set to 'on', 'true', or '1'.
    """
    header_val = request.headers.get("X-Chaos", "").lower()
    return header_val in ("on", "true", "1")
def maybe_chaos():
    """
    Potentially injects latency or raises an error for testing resilience.
    This should be called at the start of routes you want to stress-test.
    """
    if not _is_chaos_enabled():
        return
    try:
        latency_ms = int(os.getenv("CHAOS_LATENCY_MS", "0"))
        if latency_ms > 0:
            time.sleep(latency_ms / 1000.0)
    except ValueError:
        pass # Ignore invalid env var
    try:
        error_rate = float(os.getenv("CHAOS_ERROR_RATE", "0.0"))
        if error_rate > 0.0 and random.random() < error_rate:
            raise Exception("🔥 Chaos Monkey struck this request! (Testing resilience)")
    except ValueError:
        pass # Ignore invalid env var
@chaos_bp.route("/api/v1/ops/chaos/ping", methods=["GET"])
def chaos_ping():
    return {"message": "Chaos module loaded"}, 200
