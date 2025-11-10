########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\security\env_guard.py total lines 25 
########################################################################

import os
import sys
def enforce_strict_env():
    strict = os.getenv("STRICT_ENV", "true").lower() == "true"
    if not strict:
        return
    default_markers = {
        "FLOWORK_ENGINE_TOKEN": {"empty_ok": False, "bad_values": {"changeme", "dev", "default", "secret", "dev_engine_ded42245c01fa579ccce90faab1ea693"}},
    }
    failures = []
    for key, rule in default_markers.items():
        val = os.getenv(key, "")
        if not val and not rule["empty_ok"]:
            failures.append(f"{key}=<empty>")
        elif val.lower() in rule["bad_values"]:
            failures.append(f"{key}={val} (bad)")
    if failures:
        sys.stderr.write("[FATAL] STRICT_ENV violations (Core):\n - " + "\n - ".join(failures) + "\n")
        sys.exit(1)
