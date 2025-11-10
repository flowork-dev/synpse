########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\net\breaker.py total lines 42 
########################################################################

import time
import threading
from app.metrics import CIRCUIT_OPEN
class CircuitBreaker:
    def __init__(self, failure_threshold:int=5, recovery_time:int=30):
        self.fail_th = failure_threshold
        self.recover = recovery_time
        self._state = "closed"  # closed|open|half
        self._fails = 0
        self._opened_at = 0
        self._lock = threading.Lock()
    def on_success(self):
        with self._lock:
            if self._state != "closed":
                CIRCUIT_OPEN.labels("core").set(0)
            self._fails = 0
            self._state = "closed"
    def on_failure(self):
        with self._lock:
            self._fails += 1
            if self._fails >= self.fail_th and self._state != "open":
                CIRCUIT_OPEN.labels("core").set(1)
                self._state = "open"
                self._opened_at = int(time.time())
    def allow(self) -> bool:
        with self._lock:
            if self._state == "closed":
                return True
            if self._state == "open":
                if int(time.time()) - self._opened_at >= self.recover:
                    self._state = "half"
                    return True  # allow a probe
                return False
            if self._state == "half":
                return True
            return False
