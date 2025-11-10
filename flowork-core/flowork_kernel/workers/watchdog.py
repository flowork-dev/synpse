########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\workers\watchdog.py total lines 28 
########################################################################

import threading
import time
from typing import Callable
class JobWatchdog:
    def __init__(self, deadline_seconds: int = 60, on_timeout: Callable[[str], None] = None):
        self.deadline = deadline_seconds
        self.on_timeout = on_timeout or (lambda job_id: None)
    def run_with_deadline(self, job_id: str, fn: Callable, *args, **kwargs):
        result_container = {"value": None, "error": None}
        t = threading.Thread(target=self._runner, args=(result_container, fn, args, kwargs), daemon=True)
        start = time.time()
        t.start()
        t.join(timeout=self.deadline)
        if t.is_alive():
            self.on_timeout(job_id)
            result_container["error"] = TimeoutError(f"Job {job_id} exceeded {self.deadline}s")
        return result_container["value"], result_container["error"]
    def _runner(self, box, fn, args, kwargs):
        try:
            box["value"] = fn(*args, **kwargs)
        except Exception as e:
            box["error"] = e
