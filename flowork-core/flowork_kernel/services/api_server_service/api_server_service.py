########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\api_server_service.py total lines 621 
########################################################################

import asyncio
from aiohttp import web
import threading
import json
import uuid
import time
import os
import re
import importlib
import inspect
import secrets
import sys
import importlib.util
import logging # <-- START PENAMBAHAN KODE (ROADMAP 4.4)
from urllib.parse import urlparse, unquote
from ..base_service import BaseService
from .routes.base_api_route import BaseApiRoute
from flowork_kernel.exceptions import PermissionDeniedError
from collections import deque
from flowork_kernel.utils.tracing_setup import (
    setup_tracing,
    get_trace_context_from_headers,
)
from .routes.filesystem_routes import FilesystemRoutes
from .routes.engine_routes import EngineRoutes
from .routes.preset_routes import PresetRoutes # Import class rute preset yang baru
from flowork_kernel.services.ops_service.ops_service import get_autoscaling_advice
class ApiServerService(BaseService):
    def __init__(self, kernel, service_id: str):
        BaseService.__init__(self, kernel, service_id)
        self.tracer = setup_tracing(service_name="flowork-core")
        self.job_statuses = {}
        self.job_statuses_lock = threading.Lock()
        self.recent_events = deque(maxlen=15)
        self.kernel.write_to_log("Service 'ApiServerService' initialized.", "DEBUG")
        self.core_component_ids = None
        self.variable_manager = None
        self.preset_manager = None
        self.state_manager = None
        self.trigger_manager = None
        self.scheduler_manager = None
        self.module_manager_service = None
        self.plugin_manager_service = None
        self.widget_manager_service = None
        self.trigger_manager_service = None
        self.ai_provider_manager_service = None
        self.addon_service = None
        self.db_service = None
        self.dataset_manager_service = None
        self.training_service = None
        self.converter_service = None
        self.agent_manager = None
        self.agent_executor = None
        self.prompt_manager_service = None
        self.diagnostics_service = None
        self.event_bus = None
        self.workflow_executor = None
        self.tools_manager_service = None
        self.metrics_service = None
        self.app = None
        self.runner = None
        self.site = None
    def update_job_status(self, job_id: str, status_data: dict):
        with self.job_statuses_lock:
            if job_id not in self.job_statuses:
                self.job_statuses[job_id] = {}
            if "user_context" in status_data:
                self.job_statuses[job_id]["user_context"] = status_data.pop("user_context")
            self.job_statuses[job_id].update(status_data)
            if self.event_bus:
                active_jobs = []
                for j_id, j_data in self.job_statuses.items():
                    if j_data.get("status") == "RUNNING":
                        start_time = j_data.get("start_time", 0)
                        duration = time.time() - start_time
                        active_jobs.append(
                            {
                                "id": j_id,
                                "preset": j_data.get("preset_name", "N/A"),
                                "duration_seconds": round(duration, 2),
                                "user_context": j_data.get("user_context")
                            }
                        )
                self.event_bus.publish(
                    "DASHBOARD_ACTIVE_JOBS_UPDATE", # English Hardcode
                    {"active_jobs": active_jobs},
                    publisher_id=self.service_id,
                )
    def get_job_status(self, job_id: str) -> dict | None:
        with self.job_statuses_lock:
            return self.job_statuses.get(job_id)
    def log_recent_event(self, event_string: str):
        if "dashboard/summary" in event_string or "/health" in event_string:
            return
        timestamp = time.strftime("%H:%M:%S")
        self.recent_events.appendleft(f"[{timestamp}] {event_string}")
    async def start(self):
        self._load_dependencies()
        self.app = web.Application(middlewares=[self.middleware_handler])
        self._load_api_routes()
        self.core_component_ids = await self._load_protected_component_ids()
        port = self.loc.get_setting("webhook_port", 8989) if self.loc else 8989
        host = "0.0.0.0"
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host, port)
        try:
            await self.site.start()
            self.kernel.write_to_log(
                self.loc.get(
                    "log_startup_async_server",
                    fallback="ApiServer: Now running on a high-performance asynchronous core (AIOHTTP).", # English Hardcode
                ),
                "SUCCESS",
            )
            self.kernel.write_to_log(
                f"API server (Asynchronous) started and listening at http://{host}:{port}", # English Hardcode
                "SUCCESS",
            )
        except OSError as e:
            if "address already in use" in str(e).lower(): # English Hardcode
                self.kernel.write_to_log(
                    f"FATAL: API server port {port} is already in use. Another instance running or port blocked?", # English Hardcode
                    "CRITICAL"
                )
            else:
                self.kernel.write_to_log(
                    f"FATAL: Could not start API server on port {port}: {e}", # English Hardcode
                    "CRITICAL"
                )
            import sys
            sys.exit(1)
        except Exception as e:
            self.kernel.write_to_log(
                f"FATAL: Unexpected error starting API server: {e}", # English Hardcode
                "CRITICAL"
            )
            import sys
            sys.exit(1)
    def _safe_get_service(self, service_id):
        try:
            return self.kernel.get_service(service_id)
        except PermissionDeniedError:
            self.kernel.write_to_log(
                f"ApiServer dependency '{service_id}' unavailable due to license tier.", # English Hardcode
                "WARN",
            )
            return None
    def _load_dependencies(self):
        self.kernel.write_to_log(
            "ApiServerService: Loading service dependencies...", "INFO" # English Hardcode
        )
        self.variable_manager = self._safe_get_service("variable_manager_service")
        self.preset_manager = self._safe_get_service("preset_manager_service")
        self.state_manager = self._safe_get_service("state_manager")
        self.trigger_manager = self._safe_get_service("trigger_manager_service")
        self.scheduler_manager = self._safe_get_service("scheduler_manager_service")
        self.module_manager_service = self._safe_get_service("module_manager_service")
        self.plugin_manager_service = self._safe_get_service("plugin_manager_service")
        self.tools_manager_service = self._safe_get_service("tools_manager_service")
        self.widget_manager_service = self._safe_get_service("widget_manager_service")
        self.trigger_manager_service = self._safe_get_service("trigger_manager_service")
        self.ai_provider_manager_service = self._safe_get_service(
            "ai_provider_manager_service"
        )
        self.addon_service = self._safe_get_service("community_addon_service")
        self.db_service = self._safe_get_service("database_service")
        self.dataset_manager_service = self._safe_get_service("dataset_manager_service")
        self.training_service = self._safe_get_service("ai_training_service")
        self.converter_service = self._safe_get_service("model_converter_service")
        self.agent_manager = self._safe_get_service("agent_manager_service")
        self.agent_executor = self._safe_get_service("agent_executor_service")
        self.prompt_manager_service = self._safe_get_service("prompt_manager_service")
        self.diagnostics_service = self._safe_get_service("diagnostics_service")
        self.event_bus = self._safe_get_service("event_bus")
        self.workflow_executor = self._safe_get_service("workflow_executor_service")
        self.metrics_service = self._safe_get_service("metrics_service")
        self.kernel.write_to_log(
            "ApiServerService: All available service dependencies loaded.", "SUCCESS" # English Hardcode
        )
    async def handle_webhook_trigger(self, request):
        """
        (MOVED FROM webhook_server.py)
        Handles incoming webhook triggers. This endpoint is public (no X-API-Key).
        """
        preset_name = request.match_info.get("preset_name")
        if not preset_name:
            return web.json_response({"error": "Preset name missing from URL."}, status=400) # English Hardcode
        try:
            webhook_data = await request.json()
            self.kernel.write_to_log(f"Webhook received for preset '{preset_name}'. Triggering execution...", "INFO") # English Hardcode
            user_context = request.get("user_context", None)
            job_id = await self.trigger_workflow_by_api(
                preset_name=preset_name,
                initial_payload=webhook_data,
                user_context=user_context, # Pass user context if available
                mode="EXECUTE" # English Hardcode
            )
            if job_id:
                return web.json_response(
                    {"status": "success", "message": f"Workflow for preset '{preset_name}' was triggered.", "job_id": job_id}, # English Hardcode
                    status=202
                )
            else:
                return web.json_response({"error": "Failed to trigger workflow (e.g., preset not found)."}, status=404) # English Hardcode
        except json.JSONDecodeError:
            return web.json_response({"error": "Bad Request: Body must be in valid JSON format."}, status=400) # English Hardcode
        except Exception as e:
            self.kernel.write_to_log(f"Error handling webhook for preset '{preset_name}': {e}", "ERROR") # English Hardcode
            return web.json_response({"error": f"Internal Server Error: {e}"}, status=500) # English Hardcode
    async def handle_ops_advice(self, request):
        """
        (ADDED FOR ROADMAP 4.4)
        Provides autoscaling advice based on the current queue depth.
        This is intended to be called by external autoscalers.
        """
        try:
            loop = asyncio.get_event_loop()
            advice_data = await loop.run_in_executor(None, get_autoscaling_advice)
            if "error" in advice_data:
                return web.json_response(advice_data, status=500)
            return web.json_response(advice_data, status=200)
        except Exception as e:
            logging.error(f"[OpsAdvice] Failed to generate advice: {e}", exc_info=True)
            return web.json_response({"error": "Internal Server Error", "message": str(e)}, status=500)
    def _load_api_routes(self):
        self.kernel.write_to_log(
            "ApiServer: Discovering and loading API routes...", "INFO" # English Hardcode
        )
        all_route_classes = [FilesystemRoutes, EngineRoutes, PresetRoutes] # Tambahkan PresetRoutes
        routes_dir = os.path.join(os.path.dirname(__file__), "routes")
        for filename in os.listdir(routes_dir):
            if (
                filename.endswith((".py", ".service")) # English Hardcode
                and not filename.startswith("__") # English Hardcode
                and "base_api_route" not in filename # English Hardcode
                and "filesystem_routes" not in filename # English Hardcode
                and "engine_routes" not in filename # English Hardcode
                and "preset_routes" not in filename # Hindari duplikasi preset_routes
            ):
                module_base_name = os.path.splitext(filename)[0]
                module_name = f"flowork_kernel.services.api_server_service.routes.{module_base_name}"
                try:
                    module_file_path = os.path.join(routes_dir, filename)
                    spec = importlib.util.spec_from_file_location(module_name, module_file_path)
                    if spec is None:
                        self.kernel.write_to_log(f"Could not create module spec from {module_file_path}", "ERROR") # English Hardcode
                        continue
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module # Tambahkan ke sys.modules
                    spec.loader.exec_module(module)
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BaseApiRoute) and obj is not BaseApiRoute:
                            all_route_classes.append(obj)
                except Exception as e:
                    self.kernel.write_to_log(
                        f"Failed to discover routes from {filename}: {e}", "ERROR" # English Hardcode
                    )
        for route_class in all_route_classes:
            try:
                self.kernel.write_to_log(
                    f"  -> Loading routes from: {route_class.__name__}", "DEBUG" # English Hardcode
                )
                route_instance = route_class(self)
                registered_routes = route_instance.register_routes()
                for route, handler in registered_routes.items():
                    method, pattern = route.split(" ", 1)
                    if not asyncio.iscoroutinefunction(handler):
                        self.kernel.write_to_log(
                            f"    - WARNING: Handler for {method} {pattern} is not async!", "WARN" # English Hardcode
                        )
                        self.app.router.add_route(method, pattern, handler) # Coba daftarkan saja
                    else:
                        self.app.router.add_route(method, pattern, handler)
                    self.kernel.write_to_log(
                        f"    - Registered: {method} {pattern}", "DETAIL" # English Hardcode
                    )
            except Exception as e:
                import traceback
                self.kernel.write_to_log(
                    f"Failed to load routes from {route_class.__name__}: {e}\n{traceback.format_exc()}", "ERROR" # English Hardcode
                )
        async def health_check(request):
            return web.json_response({"status": "ready"}) # English Hardcode
        self.app.router.add_get("/health", health_check) # English Hardcode
        self.app.router.add_post("/webhook/{preset_name}", self.handle_webhook_trigger) # English Hardcode
        self.app.router.add_get("/ops/advice", self.handle_ops_advice) # (English Hardcode)
        self.kernel.write_to_log("    - Registered: GET /ops/advice", "DETAIL") # (English Hardcode)
        self.kernel.write_to_log("    - Registered: POST /webhook/{preset_name}", "DETAIL") # English Hardcode
        self.kernel.write_to_log("API route discovery complete.", "SUCCESS") # English Hardcode
    async def _load_protected_component_ids(self):
        protected_ids = set()
        config_path = os.path.join(self.kernel.data_path, "protected_components.txt") # English Hardcode
        try:
            try:
                import aiofiles
                async with aiofiles.open(config_path, "r", encoding="utf-8") as f:
                    content = await f.read()
            except ImportError:
                self.kernel.write_to_log(
                    f"aiofiles not found, reading protected_components.txt synchronously.", "WARN" # English Hardcode
                )
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        content = f.read()
                else:
                    content = ""
            protected_ids = {
                line.strip()
                for line in content.splitlines()
                if line.strip() and not line.startswith("#") # English Hardcode
            }
            self.kernel.write_to_log(
                f"Loaded {len(protected_ids)} protected component IDs.", "INFO" # English Hardcode
            )
        except FileNotFoundError:
            self.kernel.write_to_log(
                f"Config 'protected_components.txt' not found. No components will be protected.", # English Hardcode
                "WARN",
            )
        except Exception as e:
            self.kernel.write_to_log(
                f"Could not load protected component IDs: {e}", "ERROR" # English Hardcode
            )
        return protected_ids
    async def stop(self):
        if self.runner:
            self.kernel.write_to_log("Stopping aiohttp server...", "INFO") # English Hardcode
            await self.runner.cleanup()
            self.kernel.write_to_log("aiohttp server stopped.", "SUCCESS") # English Hardcode
    @web.middleware
    async def middleware_handler(self, request, handler):
        start_time = time.time()
        client_ip = request.remote
        log_message = f"Request received: {request.method} {request.path} from {client_ip}" # English Hardcode
        trace_context = get_trace_context_from_headers(request.headers)
        span_name = f"{request.method} {request.path}"
        with self.tracer.start_as_current_span(span_name, context=trace_context) as span:
            span.set_attribute("http.method", request.method) # English Hardcode
            span.set_attribute("http.url", str(request.url)) # English Hardcode
            span.set_attribute("net.peer.ip", client_ip) # English Hardcode
            origin = request.headers.get("Origin") # English Hardcode
            allowed_origins = {
                "https://flowork.cloud", "https://momod.flowork.cloud", # English Hardcode
                "http://localhost:5173", "http://localhost:8002", # English Hardcode
                "http://localhost:5001" # Tambahkan dashboard lokal
            }
            cors_origin = "*" # Default fallback # English Hardcode
            if origin in allowed_origins:
                cors_origin = origin
            headers = {
                "Access-Control-Allow-Origin": cors_origin,
                "Access-Control-Allow-Credentials": "true", # English Hardcode
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS", # English Hardcode
                "Access-Control-Allow-Headers": "X-API-Key, Content-Type, Authorization, X-Flowork-User-ID, X-Flowork-Engine-ID, X-Signature, X-User-Address, X-Signed-Message, traceparent", # English Hardcode
            }
            if request.method == "OPTIONS": # English Hardcode
                return web.Response(status=204, headers=headers)
            if request.path not in ["/health"] and not request.path.startswith("/api/v1/localization/"): # English Hardcode

                if hasattr(self.kernel, 'startup_complete') and not self.kernel.startup_complete:

                    self.log_recent_event(f"[{request.method}] {request.path} [BLOCKED - KERNEL INITIALIZING]") # English Hardcode
                    span.set_attribute("http.status_code", 503) # English Hardcode
                    span.set_attribute("flowork.error_reason", "Kernel initializing") # English Hardcode
                    return web.json_response(
                        {"error": "Service Unavailable: Core Engine is still initializing. Please try again shortly."}, # English Hardcode
                        status=503, headers=headers
                    )
            self.log_recent_event(f"[{request.method}] {request.path}")
            public_routes_patterns = [
                r"^/health$", # English Hardcode
                r"^/metrics$", # English Hardcode
                r"^/webhook/.*$", # --- START ADDED CODE (FIX) --- Add webhook path
                r"^/api/v1/status$", # English Hardcode
                r"^/api/v1/localization/.*$", # English Hardcode
                r"^/api/v1/(modules|plugins|tools|widgets|triggers|ai_providers|components)/.*$", # English Hardcode
                r"^/api/v1/presets/.*$", # English Hardcode
                r"^/api/v1/dashboard/.*$", # English Hardcode
                r"^/api/v1/news$", # English Hardcode
            ]
            public_routes_patterns.append(r"^/ops/advice$")
            is_public_route = any(re.match(pattern, request.path) for pattern in public_routes_patterns)
            if not is_public_route and not self._authenticate_request(request):
                span.set_attribute("http.status_code", 401) # English Hardcode
                span.set_attribute("flowork.error_reason", "Invalid API Key") # English Hardcode
                return web.json_response(
                    {"error": "Unauthorized: API Key is missing or invalid."}, status=401, headers=headers # English Hardcode
                )
            request["user_context"] = {
                "user_id": request.headers.get("X-Flowork-User-ID"), # English Hardcode
                "engine_id": request.headers.get("X-Flowork-Engine-ID"), # English Hardcode
            }
            span.set_attribute("flowork.user_id", request["user_context"]["user_id"]) # English Hardcode
            span.set_attribute("flowork.engine_id", request["user_context"]["engine_id"]) # English Hardcode
            response = None
            try:
                response = await handler(request)
                if not isinstance(response, web.Response):
                    if isinstance(response, dict):
                        response = web.json_response(response)
                    else: # Jika tipe lain, log error
                        self.kernel.write_to_log(f"Handler for {request.path} returned non-Response object: {type(response)}", "ERROR") # English Hardcode
                        raise web.HTTPInternalServerError(text="Handler returned invalid response type.") # English Hardcode
                for key, value in headers.items():
                    response.headers[key] = value
                span.set_attribute("http.status_code", response.status) # English Hardcode
                return response
            except web.HTTPException as http_exc:
                span.set_attribute("http.status_code", http_exc.status_code) # English Hardcode
                span.set_attribute("flowork.error_reason", f"HTTPException: {http_exc.reason}") # English Hardcode
                http_exc.headers.update(headers) # Tambahkan CORS
                raise http_exc # Lempar kembali exception HTTP
            except Exception as e:
                self.kernel.write_to_log(f"Unhandled error in API handler for {request.path}: {e}", "CRITICAL") # English Hardcode
                import traceback
                self.kernel.write_to_log(traceback.format_exc(), "DEBUG") # English Hardcode
                span.set_attribute("http.status_code", 500) # English Hardcode
                span.set_attribute("flowork.error_reason", f"Unhandled Exception: {type(e).__name__}") # English Hardcode
                span.record_exception(e)
                response = web.json_response(
                    {"error": "Internal Server Error", "details": str(e)}, status=500, headers=headers # English Hardcode
                )
                return response
            finally:
                duration = time.time() - start_time
                status_code = response.status if response else (http_exc.status_code if 'http_exc' in locals() else 500)
                pass
    def _authenticate_request(self, request):
        """Authenticates internal requests using the shared secret token."""
        if hasattr(self.kernel, 'is_dev_mode') and self.kernel.is_dev_mode:
            return True
        expected_key = os.getenv("GATEWAY_SECRET_TOKEN")
        if not expected_key:
            self.kernel.write_to_log(
                "GATEWAY_SECRET_TOKEN not set. Skipping internal API authentication check.", "WARN" # English Hardcode
            )
            return True
        provided_key = request.headers.get("X-API-Key") # English Hardcode
        if provided_key and secrets.compare_digest(provided_key, expected_key):
            return True # Token cocok

        provided_key_snippet = f"'{provided_key[:5]}...'" if provided_key else "'None'"
        expected_key_snippet = f"'{expected_key[:5]}...'" if expected_key else "'None (Not Set)'"
        self.kernel.write_to_log(
            f"Unauthorized API access attempt to {request.path}. Provided key: {provided_key_snippet} (Expected starts with {expected_key_snippet})", "CRITICAL" # English Hardcode
        )
        return False
    async def trigger_workflow_by_api(
        self,
        preset_name: str,
        initial_payload: dict = None,
        raw_workflow_data: dict = None,
        start_node_id: str = None,
        mode: str = "EXECUTE", # English Hardcode
        user_context: dict = None,
    ) -> str | None:
        """(MODIFIED) Triggers a workflow execution asynchronously."""
        workflow_data = None
        trigger_source_log = "" # English Hardcode
        if raw_workflow_data:
            self.logger("Triggering workflow from raw data provided by API call.", "DEBUG") # English Hardcode
            workflow_data = raw_workflow_data
            trigger_source_log = "raw API call" # English Hardcode
        elif self.preset_manager:
            self.logger(f"Triggering workflow from saved preset: '{preset_name}'", "DEBUG") # English Hardcode
            user_id = user_context.get("user_id") if user_context else None # Ambil ID user dari context
            workflow_data = self.preset_manager.get_preset_data(preset_name, user_id=user_id)
            trigger_source_log = f"preset '{preset_name}'" # English Hardcode
        else:
            self.kernel.write_to_log(
                f"API Trigger failed: PresetManager service is not available.", "ERROR" # English Hardcode
            )
            return None
        if not workflow_data:
            self.kernel.write_to_log(
                f"API Trigger failed: workflow data for {trigger_source_log} not found or is empty.", # English Hardcode
                "ERROR",
            )
            return None
        if initial_payload is None: initial_payload = {}
        if not isinstance(initial_payload, dict):
            initial_payload = {"data": {"value_from_trigger": initial_payload}} # Wrap non-dict triggers # English Hardcode
        if "data" not in initial_payload: initial_payload["data"] = {} # English Hardcode
        if "history" not in initial_payload: initial_payload["history"] = [] # English Hardcode
        initial_payload["data"]["user_context"] = user_context # English Hardcode
        job_id = str(uuid.uuid4())
        initial_status = {
            "type": "workflow", # English Hardcode
            "status": "QUEUED", # English Hardcode
            "preset_name": preset_name if not raw_workflow_data else "Raw Execution", # English Hardcode
            "start_time": time.time(),
            "user_context": user_context # Simpan user context di status job
        }
        self.update_job_status(job_id, initial_status)
        self.kernel.write_to_log(
            f"Job '{job_id}' for {trigger_source_log} has been queued. User Context: {user_context}", "INFO" # English Hardcode
        )
        workflow_executor = self.kernel.get_service("workflow_executor_service")
        if workflow_executor:
            nodes_list = workflow_data.get("nodes", []) # English Hardcode
            connections_list = workflow_data.get("connections", []) # English Hardcode
            nodes_dict = {node["id"]: node for node in nodes_list} # English Hardcode
            connections_dict = {conn["id"]: conn for conn in connections_list} # English Hardcode
            global_loop_config = workflow_data.get("global_loop_config") # English Hardcode
            payload = {
                'workflow_id': job_id, # Kita gunakan job_id sebagai workflow_id
                'user_id': user_context.get("user_id") if user_context else "system",
                'initial_data': initial_payload
            }
            exec_thread = threading.Thread(
                target=workflow_executor.execute_workflow_legacy_sync_runner, # Asumsikan ada fungsi ini
                kwargs={
                    "nodes": nodes_dict,
                    "connections": connections_dict,
                    "initial_payload": initial_payload,
                    "logger": self.kernel.write_to_log,
                    "status_updater": lambda *args: None,
                    "highlighter": lambda *args: None,
                    "workflow_context_id": job_id,
                    "job_status_updater": self.update_job_status,
                    "start_node_id": start_node_id,
                    "mode": mode,
                    "user_context": user_context,
                    "global_loop_config": global_loop_config,
                    "preset_name": preset_name if not raw_workflow_data else "Raw Execution"
                }
            )
            exec_payload = {
                'workflow_id': preset_name, # Ini adalah ID alur kerja (misal 'test-webhook')
                'user_id': user_context.get("user_id") if user_context else "system",
                'initial_data': initial_payload,
                'execution_id': job_id # ID eksekusi unik ini
            }
            def run_async_in_thread(coro):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(coro)
                finally:
                    loop.close()
            async def run_workflow_coro():
                exec_payload = {
                    'workflow_id': preset_name,
                    'user_id': user_context.get("user_id") if user_context else "system",
                    'initial_data': initial_payload,
                    'execution_id': job_id
                }
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, # Gunakan thread pool default
                workflow_executor.execute_workflow_legacy_sync_runner, # Asumsikan ada fungsi ini
                nodes_dict,
                connections_dict,
                initial_payload,
                self.kernel.write_to_log,
                lambda *args: None,
                lambda *args: None,
                job_id,
                self.update_job_status,
                start_node_id,
                mode,
                user_context,
                global_loop_config,
                preset_name if not raw_workflow_data else "Raw Execution"
            )
        else:
            self.kernel.write_to_log(
                f"Cannot trigger workflow {trigger_source_log}, WorkflowExecutor service is unavailable (likely due to license tier).", # English Hardcode
                "ERROR",
            )
            fail_status = {
                "status": "FAILED", # English Hardcode
                "error": "WorkflowExecutor service unavailable.", # English Hardcode
                "end_time": time.time(),
                "user_context": user_context # Include context in fail status
            }
            self.update_job_status(job_id, fail_status)
            return None # Indicate failure
        return job_id
    def trigger_scan_by_api(self, scanner_id: str = None) -> str | None:
        """Triggers a diagnostics scan asynchronously."""
        if not self.diagnostics_service:
            self.kernel.write_to_log(
                "API Scan Trigger failed: DiagnosticsService not found.", "ERROR" # English Hardcode
            )
            return None
        job_id = f"scan_{uuid.uuid4()}" # English Hardcode
        with self.job_statuses_lock:
            self.job_statuses[job_id] = {
                "type": "diagnostics_scan", # English Hardcode
                "status": "QUEUED", # English Hardcode
                "start_time": time.time(),
                "target": "ALL" if not scanner_id else scanner_id, # English Hardcode
            }
        scan_thread = threading.Thread(
            target=self._run_scan_worker, args=(job_id, scanner_id), daemon=True
        )
        scan_thread.start()
        return job_id
    def _run_scan_worker(self, job_id, scanner_id: str = None):
        """Worker thread for running diagnostic scans."""
        self.update_job_status(job_id, {"status": "RUNNING"}) # English Hardcode
        try:
            result_data = self.diagnostics_service.start_scan_headless(
                job_id, target_scanner_id=scanner_id
            )
            self.update_job_status(
                job_id, {"status": "COMPLETED", "end_time": time.time(), "result": result_data} # English Hardcode
            )
        except Exception as e:
            self.kernel.write_to_log(f"Headless scan job '{job_id}' failed: {e}", "ERROR") # English Hardcode
            self.update_job_status(
                job_id, {"status": "FAILED", "end_time": time.time(), "error": str(e)} # English Hardcode
            )
