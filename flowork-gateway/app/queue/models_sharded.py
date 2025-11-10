########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\queue\models_sharded.py total lines 68 
########################################################################

import json
import time
import uuid
from typing import Optional, Dict, Any
from app.db.router import db_router
def enqueue_job(engine_id:str, user_id:str, payload:Dict[str,Any], priority:int=100, delay:int=0, job_id:str=None) -> str:
    db_router.ensure_engine_schema(engine_id)
    con = db_router.get_connection(engine_id)
    jid = job_id or str(uuid.uuid4())
    now = int(time.time())
    con.execute(
        "INSERT INTO jobs(id,user_id,payload,priority,status,retries,max_retries,created_at,available_at,version)"
        "VALUES(?,?,?,?, 'queued', 0, 3, ?, ?, 0)",
        (jid, user_id, json.dumps(payload), priority, now, now + delay)
    )
    con.commit()
    return jid
def claim_next_job(engine_id:str, worker_id:str) -> Optional[Dict[str,Any]]:
    con = db_router.get_connection(engine_id)
    now = int(time.time())
    row = con.execute("""
        SELECT id, payload, priority, version
          FROM jobs
         WHERE status='queued' AND available_at<=?
         ORDER BY priority ASC, available_at ASC, created_at ASC
         LIMIT 1
    """, (now,)).fetchone()
    if not row:
        return None
    jid, payload, prio, ver = row
    upd = con.execute("""
        UPDATE jobs
           SET status='claimed', claimed_at=?, worker_id=?, version=version+1
         WHERE id=? AND status='queued' AND version=?
    """, (now, worker_id, jid, ver))
    con.commit()
    if upd.rowcount != 1:
        return None
    return {"id": jid, "payload": json.loads(payload), "priority": prio}
def finish_job(engine_id:str, jid:str, ok:bool, retry_delay:int=0):
    con = db_router.get_connection(engine_id)
    now = int(time.time())
    if ok:
        con.execute("UPDATE jobs SET status='done', version=version+1 WHERE id=?", (jid,))
        con.commit()
        return
    row = con.execute("SELECT retries, max_retries FROM jobs WHERE id=?", (jid,)).fetchone()
    if not row:
        return
    retries, max_retries = row
    if retries + 1 >= max_retries:
        con.execute("UPDATE jobs SET status='error', version=version+1 WHERE id=?", (jid,))
    else:
        con.execute("""
            UPDATE jobs
               SET status='queued', retries=retries+1, available_at=?, version=version+1
             WHERE id=?""", (now + retry_delay, jid))
    con.commit()
def queue_depth(engine_id:str) -> int:
    con = db_router.get_connection(engine_id)
    row = con.execute("SELECT COUNT(*) FROM jobs WHERE status='queued'").fetchone()
    return row[0] if row else 0
