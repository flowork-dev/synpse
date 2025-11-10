########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\cluster\peers.py total lines 108 
########################################################################

"""
Peer registry compatible with eventlet/Flask-SocketIO.
ENV:
- GATEWAY_ID=gw-a
- GATEWAY_URL=http://gw-a:8000
- GATEWAY_PEERS="gw-a=http://gw-a:8000,gw-b=http://gw-b:8000"
- GATEWAY_PUBLIC_MAP="gw-a=https://gw-a.flowork.cloud,gw-b=https://gw-b.flowork.cloud"  (optional)
- PEER_PING_PATH="/health" (optional, default "/")
- PEER_PING_INTERVAL=5  (seconds)
"""
import os
import time
import logging
from typing import Dict, List, Tuple
from urllib.parse import urlparse
import requests
try:
    from eventlet import spawn_n, sleep  # Prefer eventlet in this project
    _HAVE_EVENTLET = True
except Exception:
    _HAVE_EVENTLET = False
log = logging.getLogger(__name__)
SELF_ID = os.getenv("GATEWAY_ID", "gw-0")
SELF_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
_RAW = os.getenv("GATEWAY_PEERS", "").strip()
_PING_PATH = os.getenv("PEER_PING_PATH", "/").strip() or "/"
_PING_INTERVAL = int(os.getenv("PEER_PING_INTERVAL", "5"))
_peer_map: Dict[str, str] = {}         # {"gw-a": "http://gw-a:8000", ...}
_peer_state: Dict[str, dict] = {}      # {"gw-a": {"up": bool, "rtt": float, "ts": int, "url": str}}
def _parse_peers(raw: str) -> Dict[str, str]:
    m: Dict[str, str] = {}
    if not raw:
        return m
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            pid, url = item.split("=", 1)
            m[pid.strip()] = url.strip()
        else:
            url = item
            host = urlparse(url).hostname or "peer"
            pid = host.replace(".", "-")
            m[pid] = url
    return m
def _init_peers():
    global _peer_map
    _peer_map = _parse_peers(_RAW)
    if SELF_ID not in _peer_map:
        _peer_map[SELF_ID] = SELF_URL
    for pid, url in _peer_map.items():
        _peer_state[pid] = {"up": True, "rtt": 0.0, "ts": int(time.time()), "url": url}
def get_peer_map() -> Dict[str, str]:
    """Return {'peer_id': 'base_url', ...} including self."""
    return dict(_peer_map)
def get_candidate_ids() -> List[str]:
    """Return list of peer IDs (including SELF_ID)."""
    return list(_peer_map.keys())
def get_all_up_candidates() -> List[str]:
    """Return peer IDs currently considered UP."""
    return [pid for pid, st in _peer_state.items() if st.get("up")]
def get_url_for(peer_id: str) -> str:
    """Return base URL for a given peer ID."""
    return _peer_map.get(peer_id, "")
def peers_state() -> Dict[str, dict]:
    """Return deep copy of current peer state."""
    return {k: dict(v) for k, v in _peer_state.items()}
def _ping_once(url: str, timeout: float = 1.0) -> Tuple[bool, float]:
    start = time.time()
    try:
        r = requests.head(url + _PING_PATH, timeout=timeout)
        if r.status_code >= 500:
            return False, (time.time() - start)
        return True, (time.time() - start)
    except Exception:
        try:
            r = requests.get(url + _PING_PATH, timeout=timeout)
            return (r.status_code < 500), (time.time() - start)
        except Exception:
            return False, (time.time() - start)
def _health_loop(interval: float):
    while True:
        try:
            for pid, url in list(_peer_map.items()):
                up, rtt = _ping_once(url, timeout=1.0)
                was_up = _peer_state[pid]["up"]
                _peer_state[pid].update({"up": up, "rtt": rtt, "ts": int(time.time()), "url": url})
                if up != was_up:
                    log.warning(f"[peers] {pid} state changed -> {'UP' if up else 'DOWN'}")
        except Exception as e:
            log.warning(f"[peers] health loop error: {e}")
        finally:
            if _HAVE_EVENTLET:
                sleep(interval)
            else:
                break
_init_peers()
if _HAVE_EVENTLET:
    spawn_n(_health_loop, _PING_INTERVAL)
else:
    pass  # unused path kept for compatibility
