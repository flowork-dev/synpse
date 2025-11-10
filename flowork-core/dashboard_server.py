########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\dashboard_server.py total lines 289 
########################################################################

import threading
import time
import json
import psutil
import os
import queue
import socket
import platform
import uuid
import requests
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO
from flowork_kernel.kernel import Kernel
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
pending_auth_requests = {}
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip
def run_dashboard_server(kernel_instance, host="0.0.0.0", port=5001):
    app = Flask(
        __name__,
        template_folder="dashboard_ui/templates",
        static_folder="dashboard_ui/static",
    )
    socketio = SocketIO(app, async_mode="eventlet")
    kernel_instance.dashboard_socketio = socketio
    process = psutil.Process(os.getpid())
    kernel_start_time = time.time()
    @app.route("/")
    def index():
        return render_template("index.html")
    @app.route("/api/vitals")
    def get_vitals():
        uptime_seconds = time.time() - kernel_start_time
        return jsonify(
            {
                "cpu_percent": process.cpu_percent(interval=0.1),
                "ram_mb": process.memory_info().rss / (1024**2),
                "kernel_version": Kernel.APP_VERSION,
                "license_tier": kernel_instance.license_tier.upper(),
                "uptime_seconds": uptime_seconds,
            }
        )
    @app.route("/api/server_info")
    def get_server_info():
        api_service = kernel_instance.get_service("api_server_service")
        api_server_status = "INACTIVE"
        api_server_port = "N/A"
        recent_events = []
        if api_service and api_service.site:
            api_server_status = "ACTIVE"
            try:
                api_server_port = api_service.site.name.split(":")[-1]
            except (AttributeError, IndexError):
                api_server_port = kernel_instance.loc.get_setting("webhook_port", 8989)
            if hasattr(api_service, "recent_events"):
                recent_events = list(api_service.recent_events)
        preset_manager = kernel_instance.get_service("preset_manager_service")
        preset_count = 0
        if preset_manager:
            user_id = (
                kernel_instance.current_user.get("id")
                if kernel_instance.current_user
                else None
            )
            if user_id:
                preset_count = len(preset_manager.get_preset_list(user_id=user_id))
            else:
                preset_count = 0  # Jika tidak ada user, tampilkan 0
        gateway_connector = kernel_instance.get_service("gateway_connector_service")
        gateway_status = "DISCONNECTED"
        if gateway_connector and gateway_connector.is_connected_and_authed:
            gateway_status = "CONNECTED & AUTHENTICATED"
        elif (
            gateway_connector
            and gateway_connector.sio
            and gateway_connector.sio.connected
        ):
            gateway_status = "CONNECTED (Authenticating...)"
        return jsonify(
            {
                "local_ip": get_local_ip(),
                "dashboard_port": port,
                "api_server": {"status": api_server_status, "port": api_server_port},
                "preset_count": preset_count,
                "recent_events": recent_events,
                "gateway_status": gateway_status,
            }
        )
    @app.route("/api/status")
    def get_status():
        components = {}
        managers = {
            "Modules": kernel_instance.get_service("module_manager_service"),
            "Plugins": kernel_instance.get_service("plugin_manager_service"),
            "Widgets": kernel_instance.get_service("widget_manager_service"),
            "Triggers": kernel_instance.get_service("trigger_manager_service"),
        }
        for name, manager in managers.items():
            if manager:
                items_attr_name = f"loaded_{name.lower()}"
                items_attr = getattr(manager, items_attr_name, {})
                component_list = []
                for item_id, item_data in items_attr.items():
                    manifest = item_data.get("manifest", {})
                    component_list.append(
                        {
                            "id": item_id,
                            "name": manifest.get("name", item_id),
                            "version": manifest.get("version", "N/A"),
                            "is_paused": item_data.get("is_paused", False),
                            "manifest_data": manifest,
                        }
                    )
                components[name] = {
                    "count": len(items_attr),
                    "items": sorted(component_list, key=lambda x: x["name"]),
                }
        return jsonify({"components": components})
    @app.route("/api/active_jobs")
    def get_active_jobs():
        api_service = kernel_instance.get_service("api_server_service")
        active_jobs = []
        if api_service and hasattr(api_service, "job_statuses"):
            with api_service.job_statuses_lock:
                for job_id, job_data in api_service.job_statuses.items():
                    if job_data.get("status") == "RUNNING":
                        start_time = job_data.get("start_time", 0)
                        duration = time.time() - start_time
                        active_jobs.append(
                            {
                                "id": job_id,
                                "preset": job_data.get("preset_name", "N/A"),
                                "duration_seconds": round(duration, 2),
                            }
                        )
        return jsonify(active_jobs)
    @app.route("/api/system_specs")
    def get_system_specs():
        specs = {}
        try:
            specs["os"] = platform.platform()
            specs["architecture"] = platform.machine()
            specs["processor"] = platform.processor()
            specs["cpu_cores"] = psutil.cpu_count(logical=False)
            specs["cpu_threads"] = psutil.cpu_count(logical=True)
            svmem = psutil.virtual_memory()
            specs["ram_total_gb"] = round(svmem.total / (1024**3), 2)
            if GPU_AVAILABLE:
                gpus = GPUtil.getGPUs()
                if gpus:
                    specs["gpus"] = [
                        {"name": gpu.name, "memory_total_mb": gpu.memoryTotal}
                        for gpu in gpus
                    ]
                else:
                    specs["gpus"] = "No compatible GPU detected."
            else:
                specs["gpus"] = "GPUtil library not installed."
            gateway_connector = kernel_instance.get_service("gateway_connector_service")
            specs["engine_token"] = (
                gateway_connector.engine_token
                if gateway_connector
                else "Service not available"
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        return jsonify(specs)
    @app.route("/api/actions/reconnect_gateway", methods=["POST"])
    def reconnect_gateway():
        gateway_connector = kernel_instance.get_service("gateway_connector_service")
        if gateway_connector:
            result = gateway_connector.force_reconnect()
            return jsonify(result), 200
        return jsonify({"error": "GatewayConnectorService not found"}), 503
    @app.route("/api/auth/initiate", methods=["POST"])
    def initiate_auth():
        req_id = str(uuid.uuid4())
        pending_auth_requests[req_id] = {"status": "pending", "timestamp": time.time()}
        gateway_connector = kernel_instance.get_service("gateway_connector_service")
        webapp_url = "https://flowork.cloud"
        if gateway_connector and gateway_connector.config:
            webapp_url = gateway_connector.config.get("gateway_webapp_url", webapp_url)
        redirect_url = f"{webapp_url}/authorize-engine?req_id={req_id}"
        return jsonify({"redirect_url": redirect_url, "request_id": req_id})
    @app.route("/api/auth/receive_token", methods=["POST"])
    def receive_token():
        if request.remote_addr != "127.0.0.1":
            return jsonify({"error": "Forbidden"}), 403
        data = request.get_json()
        req_id = data.get("request_id")
        token = data.get("token")
        if not req_id or not token:
            return jsonify({"error": "request_id and token are required"}), 400
        if (
            req_id in pending_auth_requests
            and pending_auth_requests[req_id]["status"] == "pending"
        ):
            gateway_connector = kernel_instance.get_service("gateway_connector_service")
            if gateway_connector:
                gateway_connector.update_engine_token(token)
                pending_auth_requests[req_id]["status"] = "success"
                return jsonify({"status": "success"})
            else:
                return jsonify({"error": "GatewayConnectorService not available"}), 500
        else:
            return jsonify({"error": "Invalid or expired request_id"}), 404
    @app.route("/api/auth/status/<request_id>")
    def auth_status(request_id):
        if pending_auth_requests.get(request_id, {}).get("status") == "success":
            pending_auth_requests.pop(request_id, None)  # Hapus setelah berhasil
            return jsonify({"status": "success"})
        gateway_connector = kernel_instance.get_service("gateway_connector_service")
        if not gateway_connector or not gateway_connector.config:
            return (
                jsonify(
                    {"status": "error", "message": "GatewayConnector not configured."}
                ),
                500,
            )
        gateway_api_url = gateway_connector.config.get("gateway_api_url")
        if not gateway_api_url:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Gateway API URL not found in engine.conf",
                    }
                ),
                500,
            )
        claim_url = f"{gateway_api_url}/api/v1/engine/claim-token?req_id={request_id}"
        api_key = os.getenv(
            "GATEWAY_SECRET_TOKEN"
        )  # Kunci rahasia antara Core & Gateway
        headers = {"X-API-Key": api_key} if api_key else {}
        try:
            kernel_instance.write_to_log(
                f"Polling Gateway: Mencoba klaim token di {claim_url}", "DEBUG"
            )
            response = requests.get(claim_url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                new_token = data.get("token")
                if new_token:
                    kernel_instance.write_to_log(
                        "Berhasil mengklaim token baru dari Gateway.", "SUCCESS"
                    )
                    gateway_connector.update_engine_token(new_token)
                    pending_auth_requests[request_id] = {
                        "status": "success"
                    }  # Tandai berhasil
                    return jsonify({"status": "success"})
            return jsonify({"status": "pending"})
        except requests.exceptions.RequestException as e:
            kernel_instance.write_to_log(
                f"Gagal menghubungi Gateway untuk klaim token: {e}", "ERROR"
            )
            return jsonify({"status": "pending", "error": "Could not reach Gateway."})
    @socketio.on("connect", namespace="/dashboard_events")
    def handle_dashboard_connect():
        kernel_instance.write_to_log(
            "Dashboard client connected via WebSocket.", "SUCCESS"
        )
    def start_server():
        print(f"[Dashboard] Core Mission Control is running on http://{host}:{port}")
        print(
            f"[Dashboard] Access from other devices on your network at: http://{get_local_ip()}:{port}"
        )
        socketio.run(app, host=host, port=port, debug=False, use_reloader=False)
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
