########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\ops_service\ops_service.py total lines 48 
########################################################################

import os
import logging
from flowork_kernel.services.database_service.database_service import DatabaseService # (FIX) Import File 111
from flowork_kernel.services.logging_service.logging_service import setup_logging
log = setup_logging(__name__, "ops_service.log")
TARGET_LATENCY = float(os.getenv("SLO_TARGET_LATENCY", "0.5")) # seconds
SERVICE_RATE_PER_WORKER = float(os.getenv("SERVICE_RATE_PER_WORKER", "2.0")) # jobs/s/worker
SCALING_HEADROOM = float(os.getenv("SCALING_HEADROOM", "1.4"))
CURRENT_WORKERS = int(os.getenv("CORE_MAX_WORKERS", "8")) # (FIX) Read from existing env
def get_autoscaling_advice() -> dict:
    """
    (FIXED by Gemini)
    Returns a dictionary (for FastAPI), not a JSON response.
    This logic runs on the Core Engine, where it has
    direct access to the Jobs database.
    """
    try:
        db_service = DatabaseService()
        result = db_service.execute_query(
            "SELECT COUNT(id) FROM Jobs WHERE status = 'PENDING'",
            fetch_one=True
        )
        depth = result[0] if result else 0
        arrival_rate = depth / max(TARGET_LATENCY, 0.1)
        req_workers = max(1, int(
            (arrival_rate / max(SERVICE_RATE_PER_WORKER, 0.1)) * SCALING_HEADROOM
        ))
        return {
            "engine_id": os.getenv("FLOWORK_ENGINE_ID", "core-default"),
            "queue_depth": depth,
            "arrival_rate_est": arrival_rate,
            "suggested_workers": req_workers,
            "current_max_workers": CURRENT_WORKERS,
            "params": {
                "target_latency": TARGET_LATENCY,
                "service_rate_per_worker": SERVICE_RATE_PER_WORKER,
                "headroom": SCALING_HEADROOM
            }
        }
    except Exception as e:
        log.error(f"[OpsAdvice] Failed to generate autoscaling advice: {e}", exc_info=True)
        return {"error": "Failed to calculate advice", "message": str(e)}
