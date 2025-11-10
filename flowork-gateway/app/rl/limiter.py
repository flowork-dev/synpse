########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\rl\limiter.py total lines 93 
########################################################################

import time, sqlite3, os
from typing import Tuple, Any
from flask import g, jsonify, request, current_app, Response
from functools import wraps
DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/gateway.db")
def _conn():
    """ (English Hardcode) Creates a WAL-enabled connection. """
    con = sqlite3.connect(DB_PATH, timeout=5.0, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA busy_timeout=5000;")
    return con
def init_rl_schema():
    """ (English Hardcode) Creates the rl_bucket table if it doesn't exist. """
    con = _conn()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS rl_bucket(
        key TEXT PRIMARY KEY,
        tokens REAL NOT NULL,
        last_refill INTEGER NOT NULL,
        rate REAL NOT NULL,   -- tokens per second
        burst REAL NOT NULL   -- bucket size
    );
    """)
    con.close()
def _now():
    return int(time.time())
def allow(key:str, rate:float, burst:float, cost:float=1.0) -> Tuple[bool,int]:
    """
    (English Hardcode)
    Token Bucket Algorithm (from Roadmap 2.2).
    Returns (allowed, retry_after_seconds).
    """
    con = _conn(); cur = con.cursor()
    now = _now()
    row = cur.execute("SELECT tokens,last_refill,rate,burst FROM rl_bucket WHERE key=?", (key,)).fetchone()
    if row:
        tokens, last_refill, rate_db, burst_db = row
        if rate_db != rate or burst_db != burst:
            tokens = burst
            last_refill = now
        else:
            tokens = min(tokens + (now - last_refill) * rate_db, burst_db)
        allowed = tokens >= cost
        if allowed:
            tokens -= cost
            cur.execute("UPDATE rl_bucket SET tokens=?, last_refill=? WHERE key=?", (tokens, now, key))
            con.commit(); con.close()
            return True, 0
        else:
            deficit = cost - tokens
            retry = int(deficit / rate_db) if rate_db > 0 else 1
            cur.execute("UPDATE rl_bucket SET tokens=?, last_refill=? WHERE key=?", (tokens, now, key))
            con.commit(); con.close()
            return False, max(retry, 1)
    else:
        tokens = max(burst - cost, 0.0)
        cur.execute("INSERT OR REPLACE INTO rl_bucket(key,tokens,last_refill,rate,burst) VALUES(?,?,?,?,?)",
                    (key, tokens, now, rate, burst))
        con.commit(); con.close()
        return True, 0
class RateLimitExceeded(Exception):
    """Raised when a rate limit is exceeded."""
    pass
class RateLimiter:
    """(English Hardcode) Placeholder class for compatibility."""
    def __init__(self, app: Any = None):
        self.app = app
        if app:
            self.init_app(app)
    def init_app(self, app: Any):
        """(English Hardcode) Initialize the limiter with app config."""
        pass
    def allow_request(self, key: str) -> bool:
        """(English Hardcode) Placeholder, always returns True for now."""
        return True
def rl_allow(limiter: RateLimiter) -> bool:
    if request.endpoint in ['health_bp.health_check', 'prometheus_bp.metrics']:
        return True
    return True
def rate_limit(limit: int, per: int, scope: str):
    def decorator(f: Any):
        @wraps(f)
        def _wrapped(*args: Any, **kwargs: Any):
            return f(*args, **kwargs)
        return _wrapped
    return decorator
