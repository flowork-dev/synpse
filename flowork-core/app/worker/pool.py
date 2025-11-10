########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\app\worker\pool.py total lines 42 
########################################################################

import os
import threading
import queue
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any
log = logging.getLogger(__name__)
MAX_WORKERS = int(os.getenv("CORE_MAX_WORKERS","8"))
MAX_QUEUE = int(os.getenv("CORE_MAX_QUEUE","256"))
class BoundedExecutor:
    def __init__(self, workers:int=MAX_WORKERS, max_q:int=MAX_QUEUE):
        self.q = queue.Queue(maxsize=max_q)
        self.exec = ThreadPoolExecutor(max_workers=workers)
        self._stop = False
        self._pump_th = threading.Thread(target=self._pump, daemon=True)
        self._pump_th.start()
    def submit(self, fn:Callable, *a, **kw):
        self.q.put((fn,a,kw), block=True)
    def _pump(self):
        while not self._stop:
            try:
                fn,a,kw = self.q.get(timeout=1)
            except queue.Empty:
                continue
            self.exec.submit(self._safe, fn, *a, **kw)
            self.q.task_done()
    def _safe(self, fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            log.exception("worker error: %s", e)
    def shutdown(self):
        self._stop = True
        self.exec.shutdown(wait=False)
executor = BoundedExecutor()
