########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\queue\models.py total lines 148 
########################################################################

import os
import sqlite3
import json
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime # (ADDED) Dibutuhkan untuk 'get_job'
from .. import db
from ..models import Job
DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/gateway.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
def _conn():
    con = sqlite3.connect(DB_PATH, timeout=5.0, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA busy_timeout=5000;")
    return con
def init_queue_schema():
    con = _conn()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS jobs(
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        engine_id TEXT NOT NULL,
        payload TEXT NOT NULL,
        priority INTEGER NOT NULL DEFAULT 100,
        status TEXT NOT NULL DEFAULT 'queued', -- queued|claimed|done|error|expired
        retries INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 3,
        created_at INTEGER NOT NULL,
        available_at INTEGER NOT NULL,
        claimed_at INTEGER,
        worker_id TEXT,
        version INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_jobs_status_prio ON jobs(status, priority, available_at, created_at);
    CREATE INDEX IF NOT EXISTS idx_jobs_engine ON jobs(engine_id, status);
    """)
    con.close()
def enqueue_job(user_id:str, engine_id:str, payload:Dict[str,Any], priority:int=100, delay:int=0, job_id:str=None) -> str:
    """ (MODIFIED) Menerima job_id opsional """
    jid = job_id or str(uuid.uuid4())
    now = int(time.time())
    con = _conn()
    con.execute(
        "INSERT INTO jobs(id,user_id,engine_id,payload,priority,status,retries,max_retries,created_at,available_at,version)"
        "VALUES(?,?,?,?,?,'queued',0,3,?,?,0)",
        (jid, user_id, engine_id, json.dumps(payload), priority, now, now + delay)
    )
    con.close()
    return jid
def claim_next_job(engine_id:str, worker_id:str) -> Optional[Dict[str,Any]]:
    """
    Optimistic locking: update-one-where-queued; check rowcount to win the claim.
    """
    con = _conn()
    cur = con.cursor()
    now = int(time.time())
    row = cur.execute("""
        SELECT id, payload, priority, version
        FROM jobs
        WHERE engine_id=? AND status='queued' AND available_at<=?
        ORDER BY priority ASC, available_at ASC, created_at ASC
        LIMIT 1
    """, (engine_id, now)).fetchone()
    if not row:
        con.close()
        return None
    jid, payload, prio, ver = row
    upd = cur.execute("""
        UPDATE jobs
        SET status='claimed', claimed_at=?, worker_id=?, version=version+1
        WHERE id=? AND status='queued' AND version=?
    """, (now, worker_id, jid, ver))
    con.commit()
    if upd.rowcount != 1:  # lost the race; someone else claimed
        con.close()
        return None
    con.close()
    return {"id": jid, "payload": json.loads(payload), "priority": prio}
def finish_job(jid:str, ok:bool, retry_delay:int=0):
    con = _conn()
    cur = con.cursor()
    now = int(time.time())
    if ok:
        cur.execute("UPDATE jobs SET status='done', version=version+1 WHERE id=?", (jid,))
    else:
        cur.execute("SELECT retries, max_retries FROM jobs WHERE id=?", (jid,))
        row = cur.fetchone()
        if not row:
            con.close(); return
        retries, max_retries = row
        if retries + 1 >= max_retries:
            cur.execute("UPDATE jobs SET status='error', version=version+1 WHERE id=?", (jid,))
        else:
            cur.execute("""
                UPDATE jobs
                SET status='queued', retries=retries+1, available_at=?, version=version+1
                WHERE id=?""", (now + retry_delay, jid))
    con.commit()
    con.close()
def queue_depth(engine_id:str) -> int:
    con = _conn()
    row = con.execute("SELECT COUNT(*) FROM jobs WHERE engine_id=? AND status='queued'", (engine_id,)).fetchone()
    con.close()
    return row[0] if row else 0
def get_job(jid: str) -> Optional[Job]:
    """
    (ADDED) Fungsi ini hilang dan dibutuhkan oleh dispatch.py.
    (Hardcode English) This uses the SQLAlchemy session (g.db_session)
    (Hardcode English) because dispatch.py expects an SQLAlchemy Job object,
    (Hardcode English) NOT a raw dict from SQLite.
    """
    try:
        return db.session.get(Job, jid)
    except Exception as e:
        print(f"Error in get_job: {e}")
        return None
class JobDispatcher:
    """
    (ADDED) Class ini hilang dan dibutuhkan oleh dispatch.py.
    (Hardcode English) This class wraps the queue functions to match
    (Hardcode English) the interface expected by app/routes/dispatch.py.
    """
    def enqueue_job(self, job_id:str, user_id:str, engine_id:str, workflow_id:str, payload:Dict[str,Any]) -> Optional[Job]:
        """ (Hardcode English) This wrapper matches the call from dispatch.py """
        try:
            combined_payload = payload or {}
            combined_payload["_workflow_id"] = workflow_id
            jid = enqueue_job(
                user_id=user_id,
                engine_id=engine_id,
                payload=combined_payload,
                job_id=job_id # (Hardcode English) Pass the job_id
            )
            return Job(id=jid, created_at=datetime.utcnow())
        except Exception as e:
            print(f"Error in JobDispatcher.enqueue_job: {e}")
            return None
    def get_job(self, job_id: str) -> Optional[Job]:
        """ (Hardcode English) This wrapper calls the new get_job function """
        return get_job(job_id)
