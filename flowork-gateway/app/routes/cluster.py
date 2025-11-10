########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\cluster.py total lines 70 
########################################################################

import os
import hashlib
from typing import Dict, Tuple, Optional
from flask import Blueprint, jsonify, request, current_app
cluster_bp = Blueprint("cluster_api", __name__, url_prefix="/api/v1/cluster")
def _parse_peers(env_val: str) -> Dict[str, str]:
    """
    Parse peer map "gw-a=http://gw-a:8000,gw-b=http://gw-b:8000" -> dict
    """
    res: Dict[str, str] = {}
    if not env_val:
        return res
    for item in env_val.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            k, v = item.split("=", 1)
            res[k.strip()] = v.strip()
    return res
def _public_map(env_val: str) -> Dict[str, str]:
    return _parse_peers(env_val)
def _sticky_pick(key: str, choices: Tuple[str, ...]) -> Optional[str]:
    if not choices:
        return None
    h = hashlib.sha256(key.encode("utf-8")).digest()
    idx = int.from_bytes(h[:4], "big") % len(choices)
    return choices[idx]
@cluster_bp.route("/resolve-home", methods=["GET"])
def resolve_home():
    """
    Decide the user's 'home' gateway for sticky routing.
    Inputs (query):
      user_address: wallet addr (preferred)
      engine_id:    engine id (fallback)
    Returns:
      { id, url, public_url }
    """
    user_address = (request.args.get("user_address") or "").strip().lower()
    engine_id = (request.args.get("engine_id") or "").strip().lower()
    peers_str = os.getenv("GATEWAY_PEERS", "")
    pubmap_str = os.getenv("GATEWAY_PUBLIC_MAP", "")
    peers = _parse_peers(peers_str)
    pubmap = _public_map(pubmap_str)
    self_id = os.getenv("GATEWAY_ID", "gw-a")
    self_url = os.getenv("GATEWAY_URL", "http://gw-a:8000")
    if not peers:
        return jsonify({
            "id": self_id,
            "url": self_url,
            "public_url": pubmap.get(self_id)
        }), 200
    key = user_address or engine_id or "fallback"
    target_id = _sticky_pick(key, tuple(peers.keys())) or self_id
    target_url = peers.get(target_id, self_url)
    return jsonify({
        "id": target_id,
        "url": target_url,
        "public_url": pubmap.get(target_id)
    }), 200
@cluster_bp.route("/health", methods=["GET"])
def health():
    """Lightweight health endpoint for peer ping."""
    return jsonify({"ok": True, "service": "gateway", "draining": False}), 200
