########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\queue\dispatcher.py total lines 76 
########################################################################

import os
import time
import logging
from typing import Dict, Any, Optional
USE_SHARDED = os.getenv("ENGINE_QUEUE_SHARDED", "true").lower() == "true"
if USE_SHARDED:
    from .models_sharded import enqueue_job, queue_depth
else:
    from .models import enqueue_job, queue_depth
from app.metrics import QUEUE_DEPTH
from app.etl.outbox import enqueue_event
from app.rl.limiter import RateLimitExceeded # (Placeholder if needed later)
log = logging.getLogger(__name__)
class QueueFullError(Exception):
    """Raised when the target engine queue is full (backpressure)."""
    pass
class NoEngineAvailableError(Exception):
    """Raised when no suitable engine can be found for routing."""
    pass
class JobDispatcher:
    """
    Central Logic for dispatching jobs to appropriate engine queues.
    Handles:
    - Engine selection (routing) - *To be implemented fully in Roadmap 3.2*
    - Backpressure checks (QueueFullError)
    - Rate limiting hooks
    - Enqueuing to persistence layer (SQLite)
    - Emitting ETL events
    """
    def __init__(self):
        self.max_queue = int(os.getenv("ENGINE_MAX_QUEUE", "500"))
        self.default_priority = int(os.getenv("JOB_DEFAULT_PRIORITY", "100"))
    def check_rate_limit(self, remote_addr: str):
        """
        Hook for checking rate limits before dispatching.
        Currently a placeholder, can integrate with app.rl.limiter if needed.
        """
        pass
    def dispatch(self, data: Dict[str, Any], job_key: Optional[str] = None) -> str:
        """
        Dispatches a job payload to a target engine.
        """
        user_id = data.get("user_id")
        engine_id = data.get("engine_id")
        payload = data.get("payload", {})
        priority = int(data.get("priority", self.default_priority))
        job_id = data.get("job_id") # Expect job_id from caller for idempotency
        if not engine_id:
            raise ValueError("engine_id is currently required until smart routing is enabled.")
        if not user_id:
             raise ValueError("user_id is required.")
        current_depth = queue_depth(engine_id)
        QUEUE_DEPTH.set(current_depth)
        if current_depth >= self.max_queue:
            log.warning(f"[Dispatcher] Backpressure: Engine {engine_id} queue full ({current_depth}/{self.max_queue})")
            raise QueueFullError(f"Queue for engine {engine_id} is full.")
        final_jid = enqueue_job(engine_id, user_id, payload, priority=priority, job_id=job_id)
        enqueue_event("job_enqueued", {
            "job_id": final_jid,
            "engine_id": engine_id,
            "user_id": user_id,
            "priority": priority,
            "ts": int(time.time())
        })
        log.info(f"[Dispatcher] Job {final_jid} dispatched to engine {engine_id} (Priority: {priority})")
        return final_jid
_dispatcher = JobDispatcher()
def get_queue_dispatcher() -> JobDispatcher:
    """Returns the singleton JobDispatcher instance."""
    return _dispatcher
