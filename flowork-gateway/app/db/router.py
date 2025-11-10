########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\db\router.py total lines 76 
########################################################################

import os
import sqlite3
import logging
from functools import lru_cache
from typing import Optional
from flask import Flask
log = logging.getLogger(__name__)
DATA_DIR = os.getenv("SQLITE_DATA_DIR", "/app/data/engines")
os.makedirs(DATA_DIR, exist_ok=True)
PRAGMAS = [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA busy_timeout=5000;",
    "PRAGMA temp_store=MEMORY;",
    "PRAGMA cache_size=-8000;",  # ~8MB
]
def _apply_pragmas(con: sqlite3.Connection):
    """ (English Hardcode) Helper to apply pragmas to a raw connection """
    cur = con.cursor()
    for p in PRAGMAS:
        cur.execute(p)
    con.commit()
def _db_path(engine_id: str) -> str:
    """ (English Hardcode) Helper to get a sanitized DB path for an engine """
    safe = "".join(ch for ch in engine_id if ch.isalnum() or ch in ("-", "_"))
    return os.path.join(DATA_DIR, f"{safe}.db")
class ShardManager: # (FIXED) Name matches manage.py
    """
    Manages sharded SQLite connections for engine job queues.
    This is the class expected by app/manage.py.
    """
    def __init__(self):
        self.app: Optional[Flask] = None
        log.info("[DB Router] ShardManager instance created.")
    def init_app(self, app: Flask):
        self.app = app
        log.info("[DB Router] Initialized sharded engine DB router (init_app).")
    @lru_cache(maxsize=1024)
    def get_connection(self, engine_id: str) -> sqlite3.Connection:
        """
        Gets a cached, PRAGMA-optimized connection for a specific engine.
        """
        path = _db_path(engine_id)
        con = sqlite3.connect(path, timeout=5.0, isolation_level=None)
        _apply_pragmas(con)
        return con
    def ensure_engine_schema(self, engine_id: str):
        """
        Ensures the job queue tables exist in the specific engine's DB.
        """
        con = self.get_connection(engine_id)
        con.executescript("""
        CREATE TABLE IF NOT EXISTS jobs(
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          payload TEXT NOT NULL,
          priority INTEGER NOT NULL DEFAULT 100,
          status TEXT NOT NULL DEFAULT 'queued',  -- queued|claimed|done|error|expired
          retries INTEGER NOT NULL DEFAULT 0,
          max_retries INTEGER NOT NULL DEFAULT 3,
          created_at INTEGER NOT NULL,
          available_at INTEGER NOT NULL,
          claimed_at INTEGER,
          worker_id TEXT,
          version INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_status_prio ON jobs(status, priority, available_at, created_at);
        """)
        log.debug(f"[DB Router] Schema ensured for engine {engine_id}")
db_router = ShardManager()
