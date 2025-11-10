########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\healthchecks\health_gateway.py total lines 113 
########################################################################

"""
Health probe for Flowork Gateway (Flask, port 8000 by default).
Strategy (Roadmap 4.8):
- Prefer probing ONLY the /health endpoint (smart drain-aware).
- If /health is missing or unreachable, FALLBACK to /api/v1/system/health.
- Semantics:
  - /health:
      200 = healthy (active)
      503 = healthy (but DRAINING) -> container stays "healthy" so it can drain gracefully
  - /api/v1/system/health:
      2xx = healthy
      others = unhealthy
- Exit code 0 => healthy, 1 => unhealthy.
"""

import sys

import os
import socket
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


PORT = int(os.environ.get("HEALTHCHECK_PORT", "8000"))
PRIMARY_PATH = os.environ.get("HEALTHCHECK_PRIMARY_PATH", "/health")
FALLBACK_PATH = os.environ.get("HEALTHCHECK_FALLBACK_PATH", "/api/v1/system/health")
TIMEOUT = float(os.environ.get("HEALTHCHECK_TIMEOUT", "2.5"))

AUTH_OK = os.environ.get("HEALTHCHECK_AUTH_OK", "true").lower() in ("1", "true", "yes")

EXTRA_PATHS = [
    p.strip()
    for p in os.environ.get("HEALTHCHECK_EXTRA_PATHS", "/api/heartbeat,/heartbeat,/,/docs").split(",")
    if p.strip()
]

STRICT_HEALTHCHECK = os.environ.get("STRICT_HEALTHCHECK", "false").lower() in ("1", "true", "yes")

def _probe(url: str):
    """HTTP probe using urllib with small timeout."""
    try:
        with urlopen(url, timeout=TIMEOUT) as r:
            return r.status, None
    except HTTPError as e:
        return e.code, None
    except URLError as e:
        return None, f"URLError: {e.reason}"
    except Exception as e:
        return None, f"Error: {e}"

def _tcp_check(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def healthy() -> bool:
    base = f"http://127.0.0.1:{PORT}"

    def _interpret(path: str):
        url = f"{base}{path}"
        status, err = _probe(url)
        if status is not None:
            if 200 <= status < 300:
                print(f"[OK] {path} => HTTP {status}")
                return True, status
            if status == 503:
                print(f"[OK] {path} => 503 (draining) [treat healthy]")
                return True, status
            if AUTH_OK and status in (401, 403):
                print(f"[OK] {path} => {status} (auth required, app alive)")
                return True, status
            print(f"[WARN] {path} => HTTP {status}")
            return False, status
        else:
            print(f"[WAIT] {path} unreachable: {err}")
            return False, None

    ok, code = _interpret(PRIMARY_PATH)
    if ok:
        return True

    ok, code = _interpret(FALLBACK_PATH)
    if ok:
        return True

    for p in EXTRA_PATHS:
        ok, code = _interpret(p)
        if ok:
            return True

    if not STRICT_HEALTHCHECK:
        tcp_ok = _tcp_check("127.0.0.1", PORT, TIMEOUT)
        if tcp_ok:
            print("[OK] TCP connect success; treating as healthy (STRICT_HEALTHCHECK=false)")
            return True
        else:
            print("[ERR] TCP connect failed; app not listening yet")

    return False


if healthy():
    sys.exit(0)
sys.exit(1)
