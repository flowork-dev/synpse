########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\webhook.py total lines 27 
########################################################################

import requests
import json
preset_name = "test-webhook"
url = f"http://localhost:8989/webhook/{preset_name}"
payload = {
    "message_from_webhook": "Hello from the Python script!",
    "data_source": "Automated Test"
}
headers = {
    "Content-Type": "application/json"
}
try:
    print(f"Sending POST request to: {url}")
    print(f"With data: {json.dumps(payload, indent=2)}")
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    print(f"\nStatus Code: {response.status_code}")
    print("Server Response:")
    print(response.json())
except requests.exceptions.ConnectionError as e:
    print(f"\n[ERROR] Failed to connect to the server. Make sure the Flowork application is running.")
    print(f"Details: {e}")
