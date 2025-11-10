########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\health_gateway.py total lines 26 
########################################################################

import sys
import requests
import os

try:
    response = requests.get("http://localhost:8000/health", timeout=2) # English Hardcode

    if response.status_code == 200:
        print("Gateway is healthy.") # English Hardcode
        sys.exit(0)
    else:
        print(f"Gateway is unhealthy, status code: {response.status_code}") # English Hardcode
        sys.exit(1)

except requests.exceptions.ConnectionError:
    print("Gateway is not yet responding to connections.") # English Hardcode
    sys.exit(1)
except Exception as e:
    print(f"Health check failed with unexpected error: {e}") # English Hardcode
    sys.exit(1)
