########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\net\client_core.py total lines 22 
########################################################################

import os
import requests
from .breaker import CircuitBreaker
CORE_URL = os.getenv("CORE_URL","http://core:9000")
_breaker = CircuitBreaker(failure_threshold=5, recovery_time=30)
def post_core(path:str, json):
    if not _breaker.allow():
        raise RuntimeError("circuit_open")
    try:
        r = requests.post(f"{CORE_URL}{path}", json=json, timeout=5)
        r.raise_for_status()
        _breaker.on_success()
        return r.json()
    except Exception:
        _breaker.on_failure()
        raise
