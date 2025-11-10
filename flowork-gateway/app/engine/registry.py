########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\engine\registry.py total lines 74 
########################################################################

import os
import sqlite3
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
log = logging.getLogger(__name__)
DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/gateway.db")
def _conn():
    """Creates a fresh connection with proper PRAGMAs."""
    con = sqlite3.connect(DB_PATH, timeout=5.0, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA busy_timeout=5000;")
    return con
class EngineNode:
    """
    Represents a single Engine node in the cluster.
    """
    def __init__(self, engine_id: str, weight: float, capacity: int, last_seen_ts: float, url: str = None):
        self.id = engine_id
        self.weight = weight
        self.capacity = capacity
        self.last_seen_ts = last_seen_ts
        self.url = url # Internal URL for HTTP routing
    @property
    def last_heartbeat_utc(self) -> datetime:
        return datetime.fromtimestamp(self.last_seen_ts, tz=timezone.utc)
class EngineRegistry:
    """
    Manages the registry of all known Engines and their health status.
    Backed by SQLite 'registered_engines' table (synced via heartbeats).
    """
    def __init__(self):
        self.hb_ttl = int(os.getenv("ENGINE_HB_TTL", "60"))
    def get_active_engines(self) -> List[EngineNode]:
        """
        Returns a list of EngineNode objects that are currently considered 'online'.
        """
        now = int(time.time())
        cutoff = now - self.hb_ttl
        active_nodes = []
        try:
            con = _conn()
            cur = con.execute("""
                SELECT re.engine_id, 1.0 as weight, 100 as capacity,
                       STRFTIME('%s', re.last_seen) as last_seen_ts,
                       ues.internal_url
                FROM registered_engines re
                LEFT JOIN user_engine_session ues ON re.id = ues.engine_id AND ues.is_active = 1
                WHERE re.status = 'online'
            """)
            rows = cur.fetchall()
            con.close()
            for row in rows:
                eid, w, cap, ls_ts, url = row
                last_seen = int(ls_ts) if ls_ts else 0
                if last_seen >= cutoff:
                     active_nodes.append(EngineNode(eid, w, cap, last_seen, url))
        except Exception as e:
            log.error(f"[EngineRegistry] Failed to fetch active engines: {e}")
            return []
        return active_nodes
engine_registry = EngineRegistry()
def list_up_engines() -> Dict[str, Dict]:
    """Legacy wrapper returning dict format expected by older routes."""
    nodes = engine_registry.get_active_engines()
    return {n.id: {"weight": n.weight, "capacity": n.capacity} for n in nodes}
