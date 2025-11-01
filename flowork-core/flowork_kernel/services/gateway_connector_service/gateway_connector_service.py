#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\gateway_connector_service\gateway_connector_service.py JUMLAH BARIS 488 
#######################################################################

import socketio
import threading
import time
import os
import json
import random
import psutil
import requests
import traceback # <-- PENAMBAHAN KODE
from ..base_service import BaseService
try:
    from get_ip import get_local_ip # Try to import from root
except ImportError:
    from ...get_ip import get_local_ip # Fallback for relative path
class GatewayConnectorService(BaseService):
    """
    (REMASTERED V5.0) Service ini sekarang juga bertanggung jawab untuk
    mengelola daftar otorisasi user (siapa saja yang boleh mengakses engine ini).
    """
    def __init__(self, kernel, service_id):
        super().__init__(kernel, service_id)
        self.sio = None
        self._config_lock = threading.Lock()
        self.authorized_addresses = set()
        self._auth_list_lock = threading.Lock()
        self.is_auth_list_fetched = False # Flag untuk startup
        env_token = os.getenv("FLOWORK_ENGINE_TOKEN")
        conf_token = None
        docker_conf_path = os.path.join(self.kernel.data_path, "docker-engine.conf")
        if os.path.exists(docker_conf_path):
            self.logger("Found docker-engine.conf, loading it for config.", "INFO") # English log
            self.config = self._load_config(is_docker=True)
            conf_token = self.config.get("engine_token")
            if not self.config.get("gateway_api_url"):
                fallback_config = self._load_config(is_docker=False)
                self.config.setdefault("gateway_api_url", fallback_config.get("gateway_api_url", "https://api.flowork.cloud"))
                self.config.setdefault("gateway_webapp_url", fallback_config.get("gateway_webapp_url", "https://flowork.cloud"))
        else:
            self.logger("docker-engine.conf not found, using engine.conf.", "INFO") # English log
            self.config = self._load_config(is_docker=False)
            conf_token = self.config.get("engine_token")
        if env_token:
            self.engine_token = env_token
            self.logger("Using Engine Token from FLOWORK_ENGINE_TOKEN environment variable.", "SUCCESS") # English log
        elif conf_token:
            self.engine_token = conf_token
            self.logger("Using Engine Token from config file (docker-engine.conf / engine.conf).", "INFO") # English log
        else:
            self.engine_token = None
            self.logger("CRITICAL: No Engine Token found in environment variables or config files.", "CRITICAL") # English log
        if not self.config:
            self.config = {
                "gateway_api_url": "https://api.flowork.cloud",
                "gateway_webapp_url": "https://flowork.cloud",
            }
        self.gateway_url = self.config.get("gateway_api_url", "https://api.flowork.cloud")
        local_ip = get_local_ip()
        port = int(os.getenv("CORE_API_PORT", self.loc.get_setting("webhook_port", 8989) if self.loc else 8989))
        self.core_server_url = f"http://{local_ip}:{port}"
        self.is_connected_and_authed = False
        self.ping_thread = None
        self.event_bus = self.kernel.get_service("event_bus")
        self.stop_ping_event = threading.Event()
        self.process = psutil.Process(os.getpid())
        self.api_server_service = None # Akan diisi di start()
    def fetch_and_update_auth_list(self) -> bool:
        """
        Saat startup atau saat ada notifikasi, hubungi Gateway untuk mengambil DAFTAR
        alamat publik (User ID) yang diotorisasi mengakses engine ini.
        """
        self.logger("[AuthZ] Attempting to fetch/refresh engine authorization info from Gateway...", "INFO") # English Hardcode
        try:
            gateway_url = self.config.get("gateway_api_url")
            if not gateway_url:
                 gateway_url = os.getenv("GATEWAY_API_URL", "http://gateway:8000") # English Hardcode
            engine_token = self.engine_token
            if not gateway_url or not engine_token or "PLEASE_REPLACE_ME" in engine_token: # English Hardcode
                self.logger("[AuthZ] CRITICAL: Gateway URL or Engine Token is not configured. Cannot fetch auth info.", "CRITICAL") # English Hardcode
                self.is_auth_list_fetched = True # Tandai tetap selesai agar server tidak hang
                return False
            target_url = f"{gateway_url}/api/v1/engine/get-engine-auth-info"
            headers = { "X-Engine-Token": engine_token }
            self.logger(f"[AuthZ] Contacting Gateway at: {target_url}", "DEBUG") # English Log (Debug)
            response = requests.get(target_url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                addresses = data.get("authorized_addresses")
                if addresses and isinstance(addresses, list):
                    with self._auth_list_lock:
                        self.authorized_addresses.clear()
                        for addr in addresses:
                            if isinstance(addr, str) and addr.startswith('0x'):
                                self.authorized_addresses.add(addr.lower())
                    if not self.authorized_addresses:
                        self.logger(f"[AuthZ] CRITICAL: Gateway returned an empty or invalid authorized list.", "CRITICAL") # English Hardcode
                        self.is_auth_list_fetched = True # Tandai selesai
                        return False
                    self.logger(f"[AuthZ] SUCCESS: Engine authorization list refreshed. Authorized users count: {len(self.authorized_addresses)}", "SUCCESS") # English Hardcode
                    self.logger(f"[AuthZ] Sample Authorized: {list(self.authorized_addresses)[:3]}", "DEBUG") # English Hardcode
                    self.is_auth_list_fetched = True # Tandai selesai
                    return True
                else:
                    self.logger(f"[AuthZ] CRITICAL: Gateway response missing or invalid 'authorized_addresses' list.", "CRITICAL") # English Hardcode
            else:
                self.logger(f"[AuthZ] CRITICAL: Gateway rejected request. Status: {response.status_code}, Body: {response.text}", "CRITICAL") # English Hardcode
        except requests.exceptions.Timeout:
            self.logger(f"[AuthZ] CRITICAL: Timeout connecting to Gateway at {gateway_url}. Cannot fetch auth info.", "CRITICAL") # English Hardcode
        except requests.exceptions.RequestException as e:
            self.logger(f"[AuthZ] CRITICAL: Failed to connect to Gateway. Error: {e}", "CRITICAL") # English Hardcode
        except Exception as e:
            self.logger(f"[AuthZ] CRITICAL: Unexpected error fetching auth info: {e}", "CRITICAL") # English Hardcode
            self.logger(traceback.format_exc(), "DEBUG")
        self.is_auth_list_fetched = True # Tandai selesai (meskipun gagal) agar server tidak hang
        return False
    def is_user_authorized(self, public_address: str) -> bool:
        """
        Memeriksa (thread-safe) apakah suatu public address ada di dalam daftar yang diizinkan.
        """
        if not public_address:
            return False
        with self._auth_list_lock:
            return public_address.lower() in self.authorized_addresses
    def on_force_refresh_auth_list(self, data=None):
        """
        Handler saat Gateway mengirim event 'force_refresh_auth_list' via WebSocket.
        """
        self.logger("Received 'force_refresh_auth_list' signal from Gateway. Re-fetching...", "WARN") # English Log
        threading.Thread(target=self.fetch_and_update_auth_list, daemon=True).start()
    def force_reconnect(self):
        if self.sio and self.sio.connected:
            self.logger(
                "Received force reconnect command. Resending authentication token...", # English log
                "WARN",
            )
            engine_id_from_env = os.getenv("FLOWORK_ENGINE_ID")
            auth_payload = {"token": self.engine_token, "engine_id": engine_id_from_env} # English Hardcode
            try:
                self.sio.emit("auth", auth_payload, namespace="/engine-socket")
            except Exception as e:
                self.logger(f"Failed to resend auth token: {e}", "ERROR") # English log
        else:
            self.logger(
                "Received force reconnect command. Attempting to reconnect...", "INFO" # English log
            )
            self.connect()
        return {"status": "success", "message": "Reconnect initiated."} # English log
    def update_engine_token(self, new_token: str):
        with self._config_lock:
            self.logger("Attempting to update Engine Token...", "WARN") # English log
            docker_conf_path = os.path.join(self.kernel.data_path, "docker-engine.conf")
            conf_path_to_update = docker_conf_path if os.path.exists(docker_conf_path) else os.path.join(self.kernel.data_path, "engine.conf")
            self.logger("Please also update FLOWORK_ENGINE_TOKEN in your main .env file for persistence.", "WARN") # English log
            try:
                current_config = {}
                if os.path.exists(conf_path_to_update):
                    with open(conf_path_to_update, "r", encoding="utf-8") as f:
                        current_config = json.load(f)
                current_config["engine_token"] = new_token
                with open(conf_path_to_update, "w", encoding="utf-8") as f:
                    json.dump(current_config, f, indent=4)
                self.engine_token = new_token
                self.logger(f"Engine Token successfully updated in {os.path.basename(conf_path_to_update)} and config reloaded.", "SUCCESS") # English log
                self.fetch_and_update_auth_list()
                self.force_reconnect()
                return {
                    "status": "success",
                    "message": "Token updated and reconnect initiated.", # English log
                }
            except Exception as e:
                self.logger(f"Failed to update {os.path.basename(conf_path_to_update)}: {e}", "CRITICAL") # English log
                return {"status": "error", "message": str(e)}
    def _load_config(self, is_docker=False):
        with self._config_lock:
            return self._load_config_unsafe(is_docker)
    def _load_config_unsafe(self, is_docker=False):
        if is_docker:
            config_path = os.path.join(self.kernel.data_path, "docker-engine.conf")
            if not os.path.exists(config_path):
                 self.logger("File 'docker-engine.conf' not found in data volume.", "WARN") # English log
                 return {} # Kembalikan dict kosong jika tidak ada
        else:
            config_path = os.path.join(self.kernel.data_path, "engine.conf")
            if not os.path.exists(config_path):
                self.logger(
                    "File 'engine.conf' not found. Creating default file...", "WARN" # English log
                )
                default_config = {
                    "gateway_api_url": "https://api.flowork.cloud", # Default URL public
                    "gateway_webapp_url": "https://flowork.cloud",
                    "engine_token": "PLEASE_REPLACE_ME_WITH_TOKEN_FROM_WEBSITE", # English log
                }
                try:
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(default_config, f, indent=4)
                    return default_config
                except Exception as e:
                    self.logger(f"Failed to create default engine.conf: {e}", "CRITICAL") # English log
                    return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger(f"Failed to read config file {os.path.basename(config_path)}: {e}", "CRITICAL") # English log
            return {}
    def _ping_worker(self):
        while not self.stop_ping_event.is_set():
            if self.is_connected_and_authed:
                try:
                    self.logger("Sending ping and vitals to Gateway...", "DEBUG") # English log
                    vitals_payload = {
                        "cpu_percent": self.process.cpu_percent(interval=0.1),
                        "ram_percent": self.process.memory_percent(),
                        "ram_rss_mb": self.process.memory_info().rss / (1024 * 1024),
                        "kernel_version": self.kernel.APP_VERSION,
                    }
                    self.sio.emit(
                        "engine_vitals_update",
                        vitals_payload,
                        namespace="/engine-socket",
                    )
                except Exception as e:
                    self.logger(f"Failed to send ping/vitals: {e}", "WARN") # English log
            self.stop_ping_event.wait(5) # Tunggu 5 detik sebelum ping lagi
        self.logger("Ping worker stopped.", "INFO") # English log
    def _forward_event_to_gateway(self, event_name, event_data):
        if self.is_connected_and_authed and self.sio:
            payload = {"event_name": event_name, "event_data": event_data}
            try:
                self.sio.emit("forward_event_to_gui", payload, namespace="/engine-socket")
            except Exception as e:
                self.logger(f"Failed to forward event '{event_name}' to Gateway: {e}", "ERROR") # English log
    def _handle_internal_event(self, event_name, event_data):
        self._forward_event_to_gateway(event_name, event_data)
    def _forward_job_status_to_gateway(self, data):
        job_id = data.get("job_id")
        status_data = data.get("status_data")
        if self.api_server_service:
            user_context = data.get("user_context")
            status_data_with_context = status_data.copy()
            if user_context:
                status_data_with_context["user_context"] = user_context
            self.api_server_service.update_job_status(job_id, status_data_with_context)
        self._forward_event_to_gateway("WORKFLOW_JOB_STATUS_UPDATE", data) # Nama event harus konsisten
    def _sync_kill_switch_list(self):
        self.logger("Syncing global kill switch list from Gateway...", "INFO") # English log
        try:
            target_url = f"{self.gateway_url}/api/v1/system/disabled-components"
            api_key = os.getenv("GATEWAY_SECRET_TOKEN")
            headers = {"X-API-Key": api_key} if api_key else {}
            response = requests.get(target_url, headers=headers, timeout=10)
            response.raise_for_status()
            disabled_ids = response.json()
            if isinstance(disabled_ids, list):
                self.kernel.set_globally_disabled_components(disabled_ids)
            else:
                self.logger(
                    "Received invalid data format for kill switch list.", "ERROR" # English log
                )
        except requests.exceptions.RequestException as e:
            self.logger(f"Failed to sync kill switch list from Gateway: {e}", "ERROR") # English log
        except Exception as e:
            self.logger(
                f"An unexpected error occurred during kill switch sync: {e}", "ERROR" # English log
            )
    def connect(self):
        if not self.sio:
            self.logger("SocketIO client not initialized. Cannot connect.", "ERROR") # English log
            return
        if self.sio.connected:
            self.logger("Already connected to Gateway.", "DEBUG") # English log
            return
        try:
            connect_target_url = self.gateway_url or self.config.get("gateway_api_url", "https://api.flowork.cloud")
            self.logger(
                f"Attempting to connect to Gateway at {connect_target_url}...", "INFO" # English log
            )
            self.sio.connect(
                connect_target_url,
                namespaces=["/engine-socket"],
                transports=["websocket"],
            )
        except socketio.exceptions.ConnectionError as e:
            self.logger(f"Connection to Gateway failed: {e}", "ERROR") # English log
        except Exception as e:
             self.logger(f"Unexpected error during connection attempt: {e}", "ERROR") # English log
    def start(self):
        self.api_server_service = self.kernel.get_service("api_server_service")
        if not self.api_server_service:
            self.logger("ApiServerService not found, job status forwarding to local dashboard might fail.", "WARN") # English log
        if not self.engine_token or "PLEASE_REPLACE_ME" in self.engine_token: # English log
            self.logger(
                "Engine Token is not configured correctly. Authentication will likely fail.", "WARN" # English log
            )
        if self.event_bus:
            events_to_forward = [
                "WORKFLOW_LOG_ENTRY",
                "NODE_EXECUTION_METRIC",
                "CONNECTION_STATUS_UPDATE",
                "DASHBOARD_ACTIVE_JOBS_UPDATE",
            ]
            for event_name in events_to_forward:
                self.event_bus.subscribe(
                    event_name,
                    f"GatewayForwarder_{event_name}",
                    lambda data, name=event_name: self._handle_internal_event(name, data),
                )
            self.event_bus.subscribe(
                "WORKFLOW_JOB_STATUS_UPDATE",
                "GatewayConnectorJobStatusForwarder",
                self._forward_job_status_to_gateway,
            )
            self.logger(
                "GatewayConnector is now listening to internal events for forwarding.", # English log
                "INFO",
            )
        self.sio = socketio.Client(
            logger=False, # Set True untuk debug socketio
            engineio_logger=False, # Set True untuk debug engineio
            reconnection=True,
            reconnection_attempts=0, # Coba reconnect selamanya
            reconnection_delay=5,
            reconnection_delay_max=300,
            randomization_factor=0.5,
        )
        self.sio.on("connect", self.on_connect, namespace="/engine-socket")
        self.sio.on("disconnect", self.on_disconnect, namespace="/engine-socket")
        self.sio.on("auth_success", self.on_auth_success, namespace="/engine-socket")
        self.sio.on("auth_failed", self.on_auth_failed, namespace="/engine-socket")
        self.sio.on("new_job", self.on_new_job, namespace="/engine-socket")
        self.sio.on(
            "trigger_backup", self.on_trigger_backup, namespace="/engine-socket"
        )
        self.sio.on(
            "trigger_restore", self.on_trigger_restore, namespace="/engine-socket"
        )
        self.sio.on(
            "force_sync_kill_switch",
            self.on_force_sync_kill_switch,
            namespace="/engine-socket",
        )
        self.sio.on(
            "force_refresh_auth_list",
            self.on_force_refresh_auth_list,
            namespace="/engine-socket"
        )
        self.logger("Fetching initial authorization list...", "INFO") # English Log
        self.fetch_and_update_auth_list() # Lakukan fetch SYNC saat startup
        self.connect()
    def on_force_sync_kill_switch(self, data=None):
        self.logger(
            "Received 'force_sync_kill_switch' signal from Gateway. Re-syncing...", # English log
            "WARN",
        )
        self._sync_kill_switch_list()
    def on_connect(self):
        self.logger(
            "Successfully connected to Gateway. Sending authentication token...", "SUCCESS" # English log
        )
        engine_id_from_env = os.getenv("FLOWORK_ENGINE_ID")
        if not engine_id_from_env:
            self.logger("CRITICAL: FLOWORK_ENGINE_ID not set in env. Auth will fail.", "CRITICAL") # English Hardcode
        auth_payload = {"token": self.engine_token, "engine_id": engine_id_from_env} # English Hardcode
        try:
            self.sio.emit("auth", auth_payload, namespace="/engine-socket")
        except Exception as e:
            self.logger(f"Failed to send auth token on connect: {e}", "ERROR") # English log
    def on_disconnect(self):
        self.is_connected_and_authed = False
        self.logger("Disconnected from Gateway.", "WARN") # English log
        self.stop_ping_event.set() # Hentikan ping worker
    def on_auth_success(self, data):
        self.is_connected_and_authed = True
        self.logger(
            f"Engine successfully authenticated by Gateway: {data.get('message')}", # English log
            "SUCCESS",
        )
        try:
            self.sio.emit(
                "register_engine_http_info",
                {"http_url": self.core_server_url},
                namespace="/engine-socket",
            )
        except Exception as e:
             self.logger(f"Failed to register engine HTTP info: {e}", "ERROR") # English log
        self.fetch_and_update_auth_list()
        self._sync_kill_switch_list()
        self.stop_ping_event.clear()
        if self.ping_thread is None or not self.ping_thread.is_alive():
            self.ping_thread = threading.Thread(target=self._ping_worker, daemon=True)
            self.ping_thread.start()
    def on_auth_failed(self, data):
        self.logger(
            f"Authentication FAILED: {data.get('message')}. Please check your engine token.", # English log
            "CRITICAL",
        )
        self.sio.disconnect() # Putuskan koneksi jika token salah
    def on_new_job(self, data):
        job_id = data.get("job_id")
        preset_name = data.get("preset_name", "N/A")
        self.logger(
            f"New job '{preset_name}' received from Gateway! Job ID: {job_id}", # English log
            "INFO",
        )
        workflow_data = data.get("workflow_data")
        initial_payload = data.get("initial_payload", {"data": {}, "history": []})
        if not workflow_data:
            self.logger(
                f"Job {job_id} cancelled because 'workflow_data' is missing.", "ERROR" # English log
            )
            return
        user_context = data.get("user_context")
        initial_status = {
            "type": "workflow", # English log
            "status": "QUEUED", # English log
            "preset_name": preset_name,
            "start_time": time.time(),
        }
        self._forward_job_status_to_gateway({"job_id": job_id, "status_data": initial_status, "user_context": user_context})
        try:
            executor = self.kernel.get_service("workflow_executor_service")
            if executor:
                nodes = {node["id"]: node for node in workflow_data.get("nodes", [])}
                connections_list = workflow_data.get("connections", [])
                connections = {conn["id"]: conn for conn in connections_list}
                global_loop_config = workflow_data.get("global_loop_config")
                threading.Thread(
                    target=executor.execute_workflow,
                    kwargs={
                        "nodes": nodes,
                        "connections": connections,
                        "initial_payload": initial_payload,
                        "logger": self.logger, # Gunakan logger dari service ini
                        "workflow_context_id": job_id,
                        "job_status_updater": lambda jid, sdata: self._forward_job_status_to_gateway({"job_id": jid, "status_data": sdata, "user_context": user_context}),
                        "global_loop_config": global_loop_config,
                        "preset_name": preset_name,
                        "mode": "EXECUTE", # Jobs from Gateway are always EXECUTE
                        "user_context": user_context # Teruskan user context
                    },
                    daemon=True
                ).start()
            else:
                self.logger(
                    "WorkflowExecutorService not found. Cannot execute job.", # English log
                    "CRITICAL",
                )
        except Exception as e:
            self.logger(
                f"Error occurred while trying to execute job {job_id}: {e}", "CRITICAL" # English log
            )
            failed_status = {
                 "type": "workflow", # English log
                 "status": "FAILED", # English log
                 "preset_name": preset_name,
                 "start_time": initial_status["start_time"],
                 "end_time": time.time(),
                 "error": f"Failed to start execution: {e}" # English log
             }
            self._forward_job_status_to_gateway({"job_id": job_id, "status_data": failed_status, "user_context": user_context})
    def on_trigger_backup(self, data):
        user_id = data.get("user_id")
        password = data.get("password")
        self.logger(
            f"BACKUP command received from Gateway for user: {user_id}", "INFO" # English log
        )
        if not user_id or not password:
            self.logger(
                "Backup command incomplete (missing user_id or password).", "ERROR" # English log
            )
            return
    def on_trigger_restore(self, data):
        user_id = data.get("user_id")
        password = data.get("password")
        self.logger(
            f"RESTORE command received from Gateway for user: {user_id}", "INFO" # English log
        )
        if not user_id or not password:
            self.logger(
                "Restore command incomplete (missing user_id or password).", "ERROR" # English log
            )
            return
