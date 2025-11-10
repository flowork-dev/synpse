########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\app\worker\bootstrap.py total lines 37 
########################################################################

import os
from pathlib import Path
def _load_root_dotenv():
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    root = os.getenv("FLOWORK_ROOT", "")
    if root:
        env_path = Path(root) / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"[CoreBootstrap] Loaded .env from {env_path}", flush=True)
            return
    here = Path(__file__).resolve()
    for up in (here.parent, here.parent.parent, here.parent.parent.parent, here.parent.parent.parent.parent):
        candidate = up / ".env"
        if candidate.exists():
            load_dotenv(candidate)
            print(f"[CoreBootstrap] Loaded .env from {candidate}", flush=True)
            return
try:
    _load_root_dotenv()
except Exception as e:
    print(f"[CoreBootstrap] .env load skipped: {e}", flush=True)
try:
    from flowork_kernel.services.prewarm_service.prewarm_service import prewarm_models
    print("[CoreBootstrap] Import OK: flowork_kernel prewarm_service", flush=True)
    prewarm_models()
except Exception as e:
    print(f"[CoreBootstrap] Prewarm import/call failed: {e}", flush=True)
