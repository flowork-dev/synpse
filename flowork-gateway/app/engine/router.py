########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\engine\router.py total lines 47 
########################################################################

import hashlib
from typing import List, Optional, Dict, Any
class EngineRouter:
    """
    (English Hardcode) Handles the logic for selecting the best available engine for a given job.
    (English Hardcode) Uses Rendezvous (Highest Random Weight) Hashing for stickiness.
    """
    def __init__(self):
        pass
    def _score(self, key: str, engine_id: str, weight: float = 1.0) -> float:
        """
        (English Hardcode) Computes a deterministic score for an (engine, key) pair.
        """
        hash_input = f"{key}@{engine_id}".encode("utf-8")
        h = hashlib.sha256(hash_input).hexdigest()
        v = (int(h[:8], 16) / 0xFFFFFFFF) or 1e-9
        safe_weight = float(weight) if isinstance(weight, (int, float)) and weight > 0 else 1.0
        return safe_weight * (1.0 / (1.0 - v))
    def select_engine(self, job_key: str, candidates: List[Dict[str, Any]]) -> Optional[str]:
        """
        (English Hardcode) Selects the best engine ID from the candidates list based on the job_key.
        (English Hardcode) Returns None if no candidates are available.
        """
        if not candidates:
            return None
        if not job_key:
             import uuid
             job_key = str(uuid.uuid4())
        best_engine_id = None
        best_score = -1.0
        for node in candidates:
            node_id = node.get("id")
            node_weight = node.get("weight", 1.0)
            if not node_id:
                continue
            score = self._score(job_key, node_id, node_weight)
            if score > best_score:
                best_score = score
                best_engine_id = node_id
        return best_engine_id
engine_router = EngineRouter()
