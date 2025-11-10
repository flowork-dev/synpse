########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\ops\drain.py total lines 75 
########################################################################

import time
import os
from typing import Dict, Any
from flask import Blueprint, jsonify, request, current_app
drain_bp = Blueprint("ops_drain", __name__, url_prefix="/ops")
def init_drain_state(app):
    """
    Initialize drain state. Kept in app.extensions for simplicity.
    """
    if "drain_state" not in app.extensions:
        app.extensions["drain_state"] = {"on": False, "since": None}
def _get_state() -> Dict[str, Any]:
    try:
        st = current_app.extensions.get("drain_state", {"on": False, "since": None})
    except Exception:
        st = {"on": False, "since": None}
    return {
        "draining": bool(st.get("on", False)),
        "since": st.get("since"),
    }
def is_draining() -> bool:
    """
    Global helper used by sockets/HTTP to check drain quickly.
    """
    try:
        return bool(current_app.extensions.get("drain_state", {}).get("on", False))
    except Exception:
        return False
def _require_admin() -> bool:
    """
    Simple header token check. Admin sends: X-Admin-Token: <ADMIN_TOKEN>
    """
    admin_token_env = os.getenv("ADMIN_TOKEN", "").strip()
    supplied = request.headers.get("X-Admin-Token", "").strip()
    return bool(admin_token_env) and (admin_token_env == supplied)
@drain_bp.get("/drain/status")
def drain_status():
    """
    Read-only: get current drain status.
    """
    return jsonify({"ok": True, "state": _get_state()}), 200
@drain_bp.post("/drain")
def drain_toggle():
    """
    Toggle drain mode (admin only).
    Body JSON or query string: {"on": true/false} or ?on=1/0
    """
    if not _require_admin():
        return jsonify({"ok": False, "error": "forbidden"}), 403
    val = None
    if request.is_json:
        try:
            body = request.get_json(silent=True) or {}
            val = body.get("on", None)
        except Exception:
            val = None
    if val is None:
        args_on = request.args.get("on", "").strip().lower()
        if args_on in ("1", "true", "on"):
            val = True
        elif args_on in ("0", "false", "off"):
            val = False
    if val is None:
        return jsonify({"ok": False, "error": "missing 'on' flag"}), 400
    st = current_app.extensions.get("drain_state", {"on": False, "since": None})
    st["on"] = bool(val)
    st["since"] = time.time() if st["on"] else None
    current_app.extensions["drain_state"] = st
    return jsonify({"ok": True, "state": _get_state()}), 200
