########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\etl\outbox.py total lines 53 
########################################################################

import os
import sqlite3
import json
import time
import uuid
from typing import Dict, Any
DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/gateway.db")
def _conn():
    con = sqlite3.connect(DB_PATH, timeout=5.0, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA busy_timeout=5000;")
    return con
def init_outbox_schema():
    con = _conn()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS etl_outbox(
      id TEXT PRIMARY KEY,
      topic TEXT NOT NULL,
      payload TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      sent_at INTEGER
    );
    CREATE INDEX IF NOT EXISTS idx_outbox_unsent ON etl_outbox(sent_at) WHERE sent_at IS NULL;
    """)
    con.close()
def enqueue_event(topic:str, payload:Dict[str,Any]):
    con = _conn()
    eid = str(uuid.uuid4())
    con.execute(
      "INSERT INTO etl_outbox(id, topic, payload, created_at) VALUES(?,?,?,?)",
      (eid, topic, json.dumps(payload), int(time.time()))
    )
    con.commit(); con.close()
    return eid
def pull_batch(limit:int=500):
    con = _conn()
    rows = con.execute(
      "SELECT id, topic, payload FROM etl_outbox WHERE sent_at IS NULL ORDER BY created_at ASC LIMIT ?",
      (limit,)
    ).fetchall()
    con.close()
    return [{"id":r[0], "topic": r[1], "payload": r[2]} for r in rows]
def mark_sent(ids):
    con = _conn()
    now = int(time.time())
    con.executemany("UPDATE etl_outbox SET sent_at=? WHERE id=?", [(now, i) for i in ids])
    con.commit(); con.close()
