########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\etl\exporter.py total lines 45 
########################################################################

import os
import threading
import time
import json
import requests
import logging
from .outbox import init_outbox_schema, pull_batch, mark_sent
log = logging.getLogger(__name__)
ETL_URL = os.getenv("ETL_URL", "").strip()
ETL_API_KEY = os.getenv("ETL_API_KEY", "")
ETL_INTERVAL = int(os.getenv("ETL_INTERVAL_SECONDS", "15"))
def _export_once():
    if not ETL_URL:
        return
    batch = pull_batch(limit=200)
    if not batch:
        return
    ids = [b["id"] for b in batch]
    try:
        r = requests.post(ETL_URL, json={"events": batch}, headers={
            "Authorization": f"Bearer {ETL_API_KEY}",
            "Content-Type": "application/json",
        }, timeout=10)
        r.raise_for_status()
        mark_sent(ids)
    except Exception as e:
        log.warning("ETL export failed: %s", e)
def start_exporter_thread(app=None):
    if app:
        log.info("Starting ETL exporter thread (attached to Flask app).")
    else:
        log.info("Starting ETL exporter thread (standalone mode).")
    init_outbox_schema()
    def _loop():
        while True:
            _export_once()
            time.sleep(ETL_INTERVAL)
    t = threading.Thread(target=_loop, daemon=True)
    t.start()
