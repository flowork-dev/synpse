########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\run_gateway.py total lines 65 
########################################################################

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
try:
    import gevent.monkey
    gevent.monkey.patch_all()
    print("[BOOT] gevent monkey_patch applied.")
except Exception as e:
    print(f"[BOOT] WARNING: gevent unavailable or monkey_patch failed: {e}")
def _load_env():
    env_path = r"C:\FLOWORK\.env"
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(env_path, override=False)
        print(f"[BOOT] .env loaded from {env_path}")
    except Exception as e:
        print(f"[BOOT] WARNING: python-dotenv not found or load failed ({e}). "
              f"Make sure environment variables are present.")
_load_env()
FLOWORK_ROOT = os.path.dirname(os.path.abspath(__file__))
GATEWAY_DIR = os.path.join(FLOWORK_ROOT, "flowork-gateway")
if GATEWAY_DIR not in sys.path:
    sys.path.insert(0, GATEWAY_DIR)
from app import __init__ as app_init  # noqa: E402
from app.sockets import register_socket_handlers  # noqa: E402
from app.extensions import socketio  # noqa: E402
def _setup_logger():
    try:
        logs_dir = os.path.join(GATEWAY_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        handler = RotatingFileHandler(
            os.path.join(logs_dir, "gateway-runtime.log"), maxBytes=2_000_000, backupCount=5
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(handler)
        print("[BOOT] RotatingFileHandler attached at flowork-gateway/logs/gateway-runtime.log")
    except Exception as e:
        print(f"[BOOT] WARNING: logger setup failed: {e}")
def main():
    _setup_logger()
    app = app_init.create_app()
    try:
        register_socket_handlers(app)
    except Exception as e:
        app.logger.warning(f"[BOOT] register_socket_handlers failed: {e}")
    host = os.getenv("GATEWAY_BIND", "0.0.0.0")
    try:
        port = int(os.getenv("GATEWAY_PORT", "8000"))
    except Exception:
        port = 8000
    app.logger.info(f"[BOOT] Starting Flowork Gateway on {host}:{port} ...")
    socketio.run(app, host=host, port=port)
if __name__ == "__main__":
    main()
