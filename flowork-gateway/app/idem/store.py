########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\idem\store.py total lines 80 
########################################################################

import sqlite3
import os
import time
import logging
log = logging.getLogger(__name__)
DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/gateway.db")
def _conn():
    """Creates a fresh connection with proper PRAGMAs."""
    con = sqlite3.connect(DB_PATH, timeout=5.0, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA busy_timeout=5000;")
    return con
def init_idem_schema():
    """Ensures the idempotency table exists."""
    try:
        con = _conn()
        con.executescript("""
        CREATE TABLE IF NOT EXISTS idempotency(
          key TEXT PRIMARY KEY,
          created_at INTEGER NOT NULL,
          expiry INTEGER -- Optional: for future TTL support
        );
        CREATE INDEX IF NOT EXISTS idx_idem_created ON idempotency(created_at);
        """)
        con.close()
        log.info("[IdemStore] Schema initialized.")
    except Exception as e:
        log.warning(f"[IdemStore] Schema init warning (may already exist): {e}")
class IdemStore:
    """
    Local SQLite-based idempotency store.
    Used to prevent duplicate job submissions within a short time window.
    """
    def __init__(self):
        pass
    def check_and_store(self, key: str, ttl_seconds: int = 3600) -> bool:
        """
        Atomically checks if a key exists and stores it if NOT.
        Returns:
          True  -> Key ALREADY EXISTS (Hit / Duplicate Request)
          False -> Key was NEW and just stored (Miss / Allowed Request)
        """
        if not key:
            return False
        now = int(time.time())
        expiry = now + ttl_seconds
        con = _conn()
        try:
            cur = con.execute(
                "INSERT OR IGNORE INTO idempotency(key, created_at, expiry) VALUES(?, ?, ?)",
                (key, now, expiry)
            )
            con.commit()
            is_duplicate = (cur.rowcount == 0)
            if is_duplicate:
                 log.debug(f"[IdemStore] HIT (Duplicate) for key: {key}")
            else:
                 log.debug(f"[IdemStore] MISS (Stored new) for key: {key}")
            return is_duplicate
        except Exception as e:
            log.error(f"[IdemStore] Error checking key {key}: {e}")
            return False
        finally:
            con.close()
    def remember(self, key: str, job_id_ignored: str = None):
        """Legacy wrapper for 'remember'."""
        self.check_and_store(key)
    def lookup(self, key: str) -> bool:
        """Legacy wrapper for 'lookup' (returns True if exists)."""
        con = _conn()
        row = con.execute("SELECT 1 FROM idempotency WHERE key=?", (key,)).fetchone()
        con.close()
        return bool(row)
