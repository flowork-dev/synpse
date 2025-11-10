########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\queue\api.py total lines 373 
########################################################################

import os
import time
import json
import inspect
import threading
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
from flask import Blueprint, request, jsonify, current_app
from app.metrics import (
    ENQ_TOTAL,
    ENQ_IDEM_HIT,
    ENQ_RATE_LIMIT_USER,
    ENQ_RATE_LIMIT_ENGINE,
    ENQ_USER_WINDOW_SIZE,
    ENQ_ENGINE_WINDOW_SIZE,
)
queue_bp = Blueprint("queue_api", __name__, url_prefix="/api/v1/queue")
def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")
def _import_backend():
    use_sharded = _bool_env("ENGINE_QUEUE_SHARDED", False)
    mod = None
    tried = []
    try:
        if use_sharded:
            tried.append("app.queue.models_sharded")
            from . import models_sharded as mod  # type: ignore
        else:
            tried.append("app.queue.models")
            from . import models as mod  # type: ignore
    except Exception as e:
        current_app.logger.warning(f"[QueueAPI] Preferred backend import failed ({tried[-1]}): {e}")
        alt = "app.queue.models" if use_sharded else "app.queue.models_sharded"
        try:
            tried.append(alt)
            if use_sharded:
                from . import models as mod  # type: ignore
            else:
                from . import models_sharded as mod  # type: ignore
        except Exception as e2:
            current_app.logger.error(f"[QueueAPI] Fallback backend import failed ({alt}): {e2}")
            mod = None
    return mod
def _backend_module():
    mod = getattr(current_app, "_queue_backend_mod", None)
    if mod is None:
        mod = _import_backend()
        current_app._queue_backend_mod = mod  # type: ignore
        if mod:
            current_app.logger.info(f"[QueueAPI] Using backend module: {mod.__name__}")
    return mod
def _prepare_kwargs(fn, **kwargs):
    """Pass only supported kwargs (avoid TypeError on unknown names)."""
    if fn is None:
        return {}
    try:
        sig = inspect.signature(fn)
        supported = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return supported
    except Exception:
        return {}
def _call_backend(fn_names: List[str], **kwargs) -> Tuple[bool, Any]:
    """
    Try a list of candidate function names on the backend module.
    Return (ok, result_or_error).
    """
    mod = _backend_module()
    if mod is None:
        return False, "queue backend unavailable"
    for name in fn_names:
        fn = getattr(mod, name, None)
        if fn is None:
            continue
        try:
            passed = _prepare_kwargs(fn, **kwargs)
            res = fn(**passed)
            return True, res
        except TypeError as e:
            current_app.logger.debug(f"[QueueAPI] Signature mismatch for {name}: {e}")
            continue
        except Exception as e:
            current_app.logger.error(f"[QueueAPI] Backend call {name} failed: {e}", exc_info=True)
            return False, f"backend error: {e}"
    return False, "no compatible function in backend"
_IDEM_TTL_S = int(os.getenv("IDEM_TTL_S", "600"))
_idem_lock = threading.Lock()
_idem_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
IDEM_GLOBAL_URL = os.getenv("IDEM_GLOBAL_URL", "").strip().rstrip("/")
IDEM_API_KEY = os.getenv("IDEM_API_KEY", "").strip()
def _make_idem_key(engine_id: str, idem_key: str) -> str:
    return f"{engine_id}|{idem_key}"
def _idem_local_get(k: str) -> Optional[Dict[str, Any]]:
    now = time.time()
    with _idem_lock:
        item = _idem_cache.get(k)
        if not item:
            return None
        ts, payload = item
        if now - ts > _IDEM_TTL_S:
            try:
                del _idem_cache[k]
            except Exception:
                pass
            return None
        return payload
def _idem_local_put(k: str, payload: Dict[str, Any]) -> None:
    with _idem_lock:
        _idem_cache[k] = (time.time(), payload)
def _http_get_json(url: str, headers: Dict[str, str]) -> Tuple[int, Optional[Dict[str, Any]]]:
    try:
        try:
            import requests  # type: ignore
            r = requests.get(url, headers=headers, timeout=2)
            if r.status_code == 200:
                return 200, r.json()
            return r.status_code, None
        except Exception:
            import urllib.request
            import urllib.error
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                code = resp.getcode()
                body = resp.read().decode("utf-8", errors="ignore") if code == 200 else ""
                return code, (json.loads(body) if body else None)
    except Exception:
        return 0, None
def _http_post_json(url: str, headers: Dict[str, str], obj: Dict[str, Any]) -> int:
    try:
        try:
            import requests  # type: ignore
            r = requests.post(url, headers=headers, json=obj, timeout=2)
            return r.status_code
        except Exception:
            import urllib.request
            data = json.dumps(obj).encode("utf-8")
            h = {"Content-Type": "application/json"}
            h.update(headers or {})
            req = urllib.request.Request(url, headers=h, method="POST", data=data)
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.getcode()
    except Exception:
        return 0
def _global_idem_get(k: str) -> Optional[Dict[str, Any]]:
    if not IDEM_GLOBAL_URL:
        return None
    try:
        from urllib.parse import quote
        url = f"{IDEM_GLOBAL_URL}/v1/idem?key={quote(k)}"
        headers = {"X-API-Key": IDEM_API_KEY} if IDEM_API_KEY else {}
        code, body = _http_get_json(url, headers)
        if code == 200 and body and body.get("ok") and "value" in body:
            return body["value"]
        return None
    except Exception:
        return None
def _global_idem_put(k: str, payload: Dict[str, Any], ttl_s: int) -> None:
    if not IDEM_GLOBAL_URL:
        return
    try:
        url = f"{IDEM_GLOBAL_URL}/v1/idem"
        headers = {"X-API-Key": IDEM_API_KEY} if IDEM_API_KEY else {}
        obj = {"key": k, "value": payload, "ttl": int(ttl_s)}
        _http_post_json(url, headers, obj)
    except Exception:
        pass  # best-effort
_ENQ_WIN_S = max(1, int(os.getenv("ENQUEUE_RATE_WINDOW_S", "60")))
_ENQ_MAX = max(1, int(os.getenv("ENQUEUE_RATE_MAX", "120")))
_U_ENQ_WIN_S = max(1, int(os.getenv("USER_ENQUEUE_RATE_WINDOW_S", "60")))
_U_ENQ_MAX = max(1, int(os.getenv("USER_ENQUEUE_RATE_MAX", "60")))
_enq_lock = threading.Lock()
_enq_user_lock = threading.Lock()
_enq_window: Dict[str, deque] = {}
_enq_user_window: Dict[str, deque] = {}
def _rate_limit_engine(engine_id: str) -> Tuple[bool, int, int]:
    """
    Return (allowed, retry_after_seconds, window_size_after).
    """
    now = time.time()
    with _enq_lock:
        dq = _enq_window.get(engine_id)
        if dq is None:
            dq = deque()
            _enq_window[engine_id] = dq
        cutoff = now - _ENQ_WIN_S
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= _ENQ_MAX:
            retry_after = int(max(0.0, _ENQ_WIN_S - (now - dq[0])))
            return False, retry_after, len(dq)
        dq.append(now)
        return True, 0, len(dq)
def _rate_limit_user(user_id: str) -> Tuple[bool, int, int]:
    """
    Return (allowed, retry_after_seconds, window_size_after).
    No-op if user_id is falsy.
    """
    if not user_id:
        return True, 0, 0
    now = time.time()
    with _enq_user_lock:
        dq = _enq_user_window.get(user_id)
        if dq is None:
            dq = deque()
            _enq_user_window[user_id] = dq
        cutoff = now - _U_ENQ_WIN_S
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= _U_ENQ_MAX:
            retry_after = int(max(0.0, _U_ENQ_WIN_S - (now - dq[0])))
            return False, retry_after, len(dq)
        dq.append(now)
        return True, 0, len(dq)
def _extract_job_id(res: Any) -> Optional[str]:
    job_id = None
    if isinstance(res, dict):
        job_id = res.get("job_id") or res.get("id")
    elif hasattr(res, "job_id"):
        job_id = getattr(res, "job_id")
    elif hasattr(res, "id"):
        job_id = getattr(res, "id")
    if job_id is not None:
        job_id = str(job_id)
    return job_id
@queue_bp.post("/enqueue")
def enqueue():
    """
    Enqueue a job for an engine.
    Idempotency:
      - Client SHOULD send Idempotency-Key header OR 'idempotency_key' in JSON body.
      - If global provider configured (IDEM_GLOBAL_URL), we check/put there first.
      - Otherwise local in-process cache is used.
    Rate limit:
      - Per-user (if user_id available) via USER_ENQUEUE_RATE_* envs.
      - Per-engine via ENQUEUE_RATE_* envs.
    """
    if not request.is_json:
        ENQ_TOTAL.labels(outcome="bad_req").inc()
        return jsonify({"ok": False, "error": "invalid json"}), 400
    body = request.get_json(silent=True) or {}
    engine_id = (body.get("engine_id") or "").strip()
    payload = body.get("payload")
    user_id = str(body.get("user_id")).strip() if body.get("user_id") is not None else (request.headers.get("X-User-Id") or "").strip()
    body_idem = (body.get("idempotency_key") or "").strip()
    hdr_idem = (request.headers.get("Idempotency-Key") or "").strip()
    idem_key = hdr_idem or body_idem
    if not engine_id or payload is None:
        ENQ_TOTAL.labels(outcome="bad_req").inc()
        return jsonify({"ok": False, "error": "engine_id and payload are required"}), 400
    allowed_u, retry_u, size_u = _rate_limit_user(user_id)
    if user_id:
        try:
            ENQ_USER_WINDOW_SIZE.labels(user_id=user_id).set(size_u)
        except Exception:
            pass
    if not allowed_u:
        ENQ_RATE_LIMIT_USER.inc()
        ENQ_TOTAL.labels(outcome="rate_user").inc()
        return jsonify({
            "ok": False,
            "error": "rate_limited_user",
            "retry_after": retry_u
        }), 429
    allowed_e, retry_e, size_e = _rate_limit_engine(engine_id)
    try:
        ENQ_ENGINE_WINDOW_SIZE.labels(engine_id=engine_id).set(size_e)
    except Exception:
        pass
    if not allowed_e:
        ENQ_RATE_LIMIT_ENGINE.inc()
        ENQ_TOTAL.labels(outcome="rate_engine").inc()
        return jsonify({
            "ok": False,
            "error": "rate_limited_engine",
            "retry_after": retry_e
        }), 429
    cached_payload: Optional[Dict[str, Any]] = None
    if idem_key:
        k = _make_idem_key(engine_id, idem_key)
        g_val = _global_idem_get(k)
        if g_val is not None:
            ENQ_IDEM_HIT.inc()
            ENQ_TOTAL.labels(outcome="idem_hit").inc()
            out = dict(g_val)
            out.setdefault("idempotent_replay", True)
            return jsonify(out), 200
        cached_payload = _idem_local_get(k)
        if cached_payload is not None:
            ENQ_IDEM_HIT.inc()
            ENQ_TOTAL.labels(outcome="idem_hit").inc()
            out = dict(cached_payload)
            out.setdefault("idempotent_replay", True)
            return jsonify(out), 200
    ok, res = _call_backend(
        ["enqueue_job", "enqueue", "put"],
        engine_id=engine_id,
        payload=payload,
        user_id=user_id if user_id else None,
        idempotency_key=idem_key if idem_key else None,
        priority=body.get("priority"),
    )
    if not ok:
        ENQ_TOTAL.labels(outcome="backend_err").inc()
        status = 501 if "no compatible function" in str(res) or "unavailable" in str(res) else 500
        return jsonify({"ok": False, "error": str(res)}), status
    job_id = _extract_job_id(res)
    response_payload: Dict[str, Any] = {
        "ok": True,
        "job_id": job_id,
        "result": res
    }
    if idem_key:
        k = _make_idem_key(engine_id, idem_key)
        _idem_local_put(k, response_payload)  # local
        _global_idem_put(k, response_payload, _IDEM_TTL_S)  # best-effort
    ENQ_TOTAL.labels(outcome="ok").inc()
    return jsonify(response_payload), 200
@queue_bp.get("/dequeue")
def dequeue():
    """
    Dequeue one or more jobs for an engine worker.
    Query params:
      engine_id (str) : required
      max (int)       : optional (default=1, [1..100])
    """
    engine_id = request.args.get("engine_id", "").strip()
    try:
        max_n = int(request.args.get("max", "1"))
    except Exception:
        max_n = 1
    max_n = max(1, min(max_n, 100))
    if not engine_id:
        return jsonify({"ok": False, "error": "engine_id is required"}), 400
    ok, res = _call_backend(
        ["dequeue_jobs", "dequeue", "take"],
        engine_id=engine_id,
        max_n=max_n
    )
    if not ok:
        status = 501 if "no compatible function" in str(res) or "unavailable" in str(res) else 500
        return jsonify({"ok": False, "error": str(res)}), status
    items: List[Any] = []
    if isinstance(res, list):
        items = res
    elif res is None:
        items = []
    else:
        items = [res]
    return jsonify({"ok": True, "items": items}), 200
@queue_bp.get("/stats")
def stats():
    """
    Queue statistics (global or per engine).
    Query params:
      engine_id (str) : optional filter
    """
    engine_id = request.args.get("engine_id", "").strip() or None
    ok, res = _call_backend(
        ["queue_stats", "stats", "get_stats"],
        engine_id=engine_id
    )
    if not ok:
        status = 501 if "no compatible function" in str(res) or "unavailable" in str(res) else 500
        return jsonify({"ok": False, "error": str(res)}), status
    return jsonify({"ok": True, "stats": res}), 200
