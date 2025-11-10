########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\idem\global_client.py total lines 56 
########################################################################

import requests
import logging
import json
from typing import Optional, Dict, Any
log = logging.getLogger(__name__)
class GlobalIdempotencyClient:
    """
    Client for interacting with the global idempotency service (e.g., Cloudflare D1 via worker).
    Used to ensure exactly-once processing across distributed Gateway nodes.
    """
    def __init__(self, db_url: str, db_token: str, api_key: str):
        self.base_url = db_url.rstrip('/') if db_url else None
        self.token = db_token
        self.api_key = api_key
    def check_global_idem(self, key: str, job_id: str, ttl_seconds: int = 3600) -> bool:
        """
        Checks (and atomically attempts to set) the idempotency key globally.
        Returns True if the key ALREADY EXISTS (duplicate request).
        Returns False if the key was new and successfully set (safe to proceed).
        """
        if not self.base_url or not self.token:
             return False
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "key": key,
            "job_id": job_id,
            "ttl": ttl_seconds
        }
        try:
            url = f"{self.base_url}/v1/idem/claim"
            resp = requests.post(url, json=payload, headers=headers, timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("claimed") is True:
                     return False
                return True
            elif resp.status_code == 409:
                return True
            else:
                log.warning(f"[GlobalIdem] Unexpected response from D1: {resp.status_code} - {resp.text}")
                return False # Fail-open on error to avoid blocking legit jobs if D1 is down
        except Exception as e:
            log.error(f"[GlobalIdem] Failed to connect to global service: {e}")
            return False # Fail-open
    def atomic_get_or_create_global(self, key: str, job_id: str, ttl: int = 3600) -> Optional[Dict[str, Any]]:
         pass
