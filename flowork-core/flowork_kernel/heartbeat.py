########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\heartbeat.py total lines 22 
########################################################################

import threading, time, requests, os, logging
log = logging.getLogger(__name__)
GW_URL = os.getenv("GATEWAY_API_URL", "http://gateway:8000")
ENGINE_ID = os.getenv("FLOWORK_ENGINE_ID", "engine-dev")
HB_INTERVAL = int(os.getenv("ENGINE_HB_INTERVAL", "15"))
def _beat():
    while True:
        try:
            requests.post(f"{GW_URL}/internal/engine/heartbeat", json={"engine_id": ENGINE_ID}, timeout=15)
        except Exception as e:
            log.warning("Heartbeat missed (non-fatal): %s", e)
        time.sleep(HB_INTERVAL)
def start_heartbeat():
    log.info(f"Starting heartbeat thread. Beating to {GW_URL} every {HB_INTERVAL}s for ENGINE_ID {ENGINE_ID}")
    t = threading.Thread(target=_beat, daemon=True)
    t.start()
