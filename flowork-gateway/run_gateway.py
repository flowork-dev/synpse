#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\run_gateway.py JUMLAH BARIS 33 
#######################################################################

import eventlet
eventlet.monkey_patch()
import sys
import os
import subprocess
import importlib.util
import threading
from app import create_app, socketio
def main():
    """
    Entry point utama untuk menjalankan Gateway.
    """
    app = create_app()
    app.logger.info("[Gateway] Starting FLOWORK Gateway Control Tower...")
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0"
    app.logger.info(f"[Gateway] Server listening on {host}:{port}")
    try:
        socketio.run(app, host=host, port=port, debug=False, use_reloader=False)
    except Exception as e:
        app.logger.critical(f"[Gateway] Failed to start server: {e}")
        if "Address already in use" in str(e):
            app.logger.critical(f"Port {port} is already in use. Is another instance running?")
        sys.exit(1)
if __name__ == "__main__":
    main()
