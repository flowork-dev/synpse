########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\cluster\sticky.py total lines 32 
########################################################################

import hashlib
import os
from typing import List, Optional
SELF_ID = os.getenv("GATEWAY_ID", "gw-0")
def _score(key: str, node_id: str, weight: float = 1.0) -> float:
    """
    Rendezvous score (HRW hashing). Deterministic and stable across nodes.
    """
    h = hashlib.sha256((key + "@" + node_id).encode("utf-8")).hexdigest()
    v = (int(h[:8], 16) / 0xFFFFFFFF) or 1e-9
    return weight * (1.0 / (1.0 - v))
def pick_home_gateway(key: str, candidates: List[str]) -> Optional[str]:
    """
    Return the highest-scoring node for the given key.
    """
    if not candidates:
        return None
    best, best_s = None, -1.0
    for nid in candidates:
        s = _score(key, nid, 1.0)
        if s > best_s:
            best_s, best = s, nid
    return best
def is_home_gateway(key: str, candidates: List[str]) -> bool:
    """Check if SELF_ID is the home for this key."""
    return pick_home_gateway(key, candidates) == SELF_ID
