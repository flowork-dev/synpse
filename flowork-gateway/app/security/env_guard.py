########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\security\env_guard.py total lines 33 
########################################################################

import os
import sys
def check_strict_env():
    """
    (Roadmap 1.B)
    Checks critical environment variables.
    If 'STRICT_ENV' is true, this function will terminate the application
    if any default or weak credentials are found.
    """
    is_strict = os.environ.get('STRICT_ENV', 'true').lower() == 'true'
    if not is_strict:
        print("[BOOT][WARN] STRICT_ENV=false. Skipping default credential check. THIS IS INSECURE.")
        return
    print("[BOOT] STRICT_ENV=true. Checking for default credentials...")
    weak_creds = {
        "JWT_SECRET_KEY": "changeme",
        "ADMIN_DEFAULT_PASSWORD": "admin"
    }
    is_default = False
    for key, default_value in weak_creds.items():
        if os.environ.get(key) == default_value:
            print(f"[BOOT][FATAL] Default credential detected for '{key}'.", file=sys.stderr)
            is_default = True
    if is_default:
        print("[BOOT][FATAL] Please change these values in your .env file before starting.", file=sys.stderr)
        sys.exit(1) # Hard exit
    print("[BOOT] Strict ENV check passed.")
