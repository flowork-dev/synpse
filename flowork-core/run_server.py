########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\run_server.py total lines 405 
########################################################################

import sys
import os
import time
import importlib.util
from dotenv import load_dotenv

core_path_for_guard = os.path.abspath(os.path.dirname(__file__))
if core_path_for_guard not in sys.path:
    sys.path.insert(0, core_path_for_guard)

from flowork_kernel.security.env_guard import enforce_strict_env
enforce_strict_env()

import asyncio
import subprocess
import traceback
import logging
import multiprocessing  # <-- START ADDED CODE (FIX - RISK #6)
from multiprocessing import Process, Queue, Event  # <-- START MODIFIED CODE (FIX - RISK #7)

from flowork_kernel.singleton import Singleton
from flowork_kernel.services.database_service.database_service import DatabaseService
from flowork_kernel.workers.job_worker import worker_process
from flowork_kernel.services.gateway_connector_service.gateway_connector_service import GatewayConnectorService
from flowork_kernel.services.module_manager_service.module_manager_service import ModuleManagerService
from flowork_kernel.services.plugin_manager_service.plugin_manager_service import PluginManagerService
from flowork_kernel.services.tools_manager_service.tools_manager_service import ToolsManagerService
from flowork_kernel.services.trigger_manager_service.trigger_manager_service import TriggerManagerService
from flowork_kernel.services.ai_provider_manager_service.ai_provider_manager_service import AIProviderManagerService
from flowork_kernel.services.workflow_executor_service.workflow_executor_service import WorkflowExecutorService
from flowork_kernel.services.preset_manager_service.preset_manager_service import PresetManagerService
from flowork_kernel.services.api_server_service.api_server_service import ApiServerService
from flowork_kernel.services.localization_manager_service.localization_manager_service import LocalizationManagerService
from flowork_kernel.services.state_manager_service.state_manager_service import StateManagerService
from flowork_kernel.heartbeat import start_heartbeat

class SafeDict(dict):
    """
    Resilient mapping for config/settings:
    - .get(...) never returns None; returns SafeDict() for missing/None values.
    - Accepts non-standard kwarg `fallback` for compatibility with custom config APIs.
    - Nested access like x.get('a').get('b') won't crash.
    This is a defensive wrapper; it does NOT remove original logic anywhere.
    """
    def get(self, key, default=None, **kwargs):  # noqa: D401
        fallback = kwargs.pop("fallback", None)
        if default is None and fallback is not None:
            default = fallback
        val = super().get(key, default)
        if val is None:
            return SafeDict()
        if isinstance(val, dict) and not isinstance(val, SafeDict):
            return SafeDict(val)
        return val

    def __getattr__(self, item):
        return self.get(item, SafeDict())

    def setdefault(self, key, default=None):
        if key not in self:
            super().setdefault(key, {} if default is None else default)
        return self.get(key)

    def __getitem__(self, key):
        if key in self:
            val = super().__getitem__(key)
            if val is None:
                return SafeDict()
            if isinstance(val, dict) and not isinstance(val, SafeDict):
                return SafeDict(val)
            return val
        return SafeDict()

def display_banner():
    print("=" * 70)
    print(
        r"""
  _____ _   ____ _    ____ ____ _ __
 /  __// \  /  _ \/ \  /|/  _ \/  __\/ |/ /
 |  __\| |  | / \|| | ||| / \||  \/||   /
 | |   | |_/\| \_/|| |/\||| \_/||    /|   \
 \_/   \____/\____/\_/  \|\____/\_/\_\\_|\_\
    """
    )
    print(" CORE SERVER ENGINE BY FLOWORK (v2.0 - Async Orchestrator)") # English Hardcode
    print("=" * 70)

def ensure_packages_exist():
    project_root = os.path.abspath(os.path.dirname(__file__))
    packages_to_check = ["generated_services"] # English Hardcode
    for package in packages_to_check:
        package_path = os.path.join(project_root, package)
        init_file = os.path.join(package_path, "__init__.py")
        os.makedirs(package_path, exist_ok=True)
        if not os.path.exists(init_file):
            try:
                with open(init_file, "w") as f:
                    pass
                print(
                    f"[INFO] Created missing package file: {os.path.relpath(init_file)}" # English Hardcode
                )
            except Exception as e:
                print(f"[WARN] Could not create __init__.py for {package}: {e}") # English Hardcode

def _harden_api_server(api_server):
    """
    Defensive defaults so ApiServerService never crashes on None config.
    We only add wrappers; we do not remove existing logic.
    """
    current = getattr(api_server, "config", None)
    if current is None:
        api_server.config = SafeDict()
    elif isinstance(current, dict) and not isinstance(current, SafeDict):
        api_server.config = SafeDict(current)

    for section in ("cors", "server", "uvicorn", "security", "auth"):
        _ = api_server.config.setdefault(section, SafeDict())

    if not hasattr(api_server, "settings") or getattr(api_server, "settings") is None:
        api_server.settings = api_server.config  # alias to SafeDict

    if not hasattr(api_server, "_safe_get"):
        api_server._safe_get = staticmethod(
            lambda d, k, default=None, **kw: (
                d.get(k, default, **kw) if isinstance(d, dict) else default
            )
        )

    orig_start = api_server.start

    async def _wrapped_start(*args, **kwargs):
        if getattr(api_server, "config", None) is None:
            api_server.config = SafeDict()
        elif not isinstance(api_server.config, SafeDict):
            api_server.config = SafeDict(api_server.config)

        for section in ("cors", "server", "uvicorn", "security", "auth"):
            api_server.config.setdefault(section, SafeDict())

        if getattr(api_server, "settings", None) is None:
            api_server.settings = api_server.config

        try:
            return await orig_start(*args, **kwargs)
        except AttributeError as e:
            logging.error("[ApiServerService] AttributeError during start; applying SafeDict fallback", exc_info=True)
            if not isinstance(api_server.config, SafeDict):
                api_server.config = SafeDict(api_server.config or {})
            for section in ("cors", "server", "uvicorn", "security", "auth"):
                api_server.config.setdefault(section, SafeDict())
            api_server.settings = api_server.config
            return await orig_start(*args, **kwargs)

    api_server.start = _wrapped_start

async def main_async(gateway_connector):
    """
    (Per Roadmap 6/8)
    Main entry point for all asynchronous services.
    HANYA MENJALANKAN Gateway Connector.
    """
    if not gateway_connector:
        logging.critical("GatewayConnectorService not found in Singleton. Cannot start.") # English Hardcode
        return

    api_server = Singleton.get_instance(ApiServerService)
    if not api_server:
        logging.critical("ApiServerService not found in Singleton. Cannot start.") # English Hardcode
        return

    print(f"--- FLOWORK Core Async Services are running ---") # English Hardcode
    print("--- Connecting to Gateway... Press Ctrl+C to stop. ---") # English Hardcode

    await asyncio.gather(
        asyncio.create_task(gateway_connector.start()), # (MODIFIED) Menjalankan client
        asyncio.create_task(api_server.start()), # (PENAMBAHAN KODE) Menjalankan server API
        asyncio.Event().wait() # (ADDED) This waits forever
    )

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [MainProcess] - %(message)s')

    db_service = None
    gateway_connector = None
    workers = []

    try:
        db_service = DatabaseService()
        Singleton.set_instance(DatabaseService, db_service)
        DB_PATH = db_service.db_path
        logging.info(f"DatabaseService initialized. DB path set to: {DB_PATH}") # English Hardcode
    except Exception as e:
        logging.error(f"CRITICAL: Failed to initialize DatabaseService. {e}") # English Hardcode
        sys.exit(1)

    try:
        job_event = multiprocessing.Event()
        Singleton.set_instance(multiprocessing.Event, job_event)
        logging.info("Multiprocessing Job Event (bell) initialized and stored in Singleton.") # English Hardcode
    except Exception as e:
        logging.error(f"CRITICAL: Failed to initialize multiprocessing.Event: {e}") # English Hardcode
        sys.exit(1)

    project_root = os.path.abspath(os.path.dirname(__file__))

    class MockKernel:
        def __init__(self):
            self.APP_VERSION = "1.0.0" # (English Hardcode) Add missing attribute
            self.license_tier = "architect" # (English Hardcode) Add missing attribute

            self.project_root_path = project_root

            self.true_root_path = os.path.abspath(os.path.join(self.project_root_path, ".."))
            self.data_path = db_service.data_dir # Gunakan data_dir dari db_service (ini /app/data, sudah benar)


            self.modules_path = "/app/flowork_kernel/modules"
            self.plugins_path = "/app/flowork_kernel/plugins"
            self.tools_path = "/app/flowork_kernel/tools"
            self.triggers_path = "/app/flowork_kernel/triggers"
            self.ai_providers_path = "/app/flowork_kernel/ai_providers"
            self.ai_models_path = "/app/flowork_kernel/ai_models"
            self.formatters_path = "/app/flowork_kernel/formatters"
            self.scanners_path = "/app/flowork_kernel/scanners"
            self.assets_path = "/app/flowork_kernel/assets" # (English Hardcode) ADDED
            self.widgets_path = os.path.join(self.true_root_path, "widgets") # (English Hardcode) This path is not in docker-compose, but keeping original logic


            self.logs_path = os.path.join(self.project_root_path, "logs")
            self.system_plugins_path = os.path.join(
                self.project_root_path, "system_plugins"
            )
            self.themes_path = os.path.join(self.project_root_path, "themes")
            self.locales_path = os.path.join(self.project_root_path, "locales")

            self.globally_disabled_components = set()  # English Hardcode
            self.globally_disabled_types = set()       # English Hardcode

        def write_to_log(self, message, level="INFO", source="MockKernel"):
            log_level = getattr(logging, level.upper(), logging.INFO)
            logging.log(log_level, f"[{level}] [{source}] {message}")

        def get_service(self, service_id, *args, **kwargs):
            """
            Backward-compatible accessor that tolerates extra kwargs (e.g. is_system_call).
            Also returns SafeDict() when service is absent, to avoid None.get crashes.
            """
            kwargs.pop("is_system_call", None)  # ignore control flags safely
            try:
                inst = Singleton.get_instance(service_id)
            except Exception:
                inst = None

            if inst is None and isinstance(service_id, type):
                try:
                    inst = service_id(kernel=self)  # many services accept kernel=...
                    try:
                        Singleton.set_instance(service_id, inst)
                    except Exception:
                        pass
                except Exception:
                    inst = None

            if inst is None:
                return SafeDict()
            return inst

    mock_kernel = MockKernel()

    try:
        ENGINE_TOKEN = os.getenv("FLOWORK_ENGINE_TOKEN")
        if not ENGINE_TOKEN:
            logging.critical("FLOWORK_ENGINE_TOKEN environment variable is not set.") # English Hardcode
            sys.exit(1)

        loc_manager = LocalizationManagerService(mock_kernel, "localization_manager")
        loc_manager.load_all_languages() # Penting: load bahasa sebelum service lain membutuhkannya
        Singleton.set_instance(LocalizationManagerService, loc_manager)
        Singleton.set_instance("localization_manager", loc_manager)
        logging.info("LocalizationManagerService initialized and stored in Singleton.") # English Hardcode

        state_manager = StateManagerService(mock_kernel, "state_manager_service")
        Singleton.set_instance(StateManagerService, state_manager)
        Singleton.set_instance("state_manager", state_manager) # (English Hardcode) Add alias for ApiServerService
        logging.info("StateManagerService initialized and stored in Singleton (with 'state_manager' alias).")

        gateway_connector = GatewayConnectorService(mock_kernel, "gateway_connector_service")
        Singleton.set_instance(GatewayConnectorService, gateway_connector)
        logging.info("GatewayConnectorService initialized and stored in Singleton.") # English Hardcode

        workflow_executor = WorkflowExecutorService(mock_kernel, "workflow_executor_service") # <-- (FIX) Pass mock_kernel
        Singleton.set_instance(WorkflowExecutorService, workflow_executor)
        logging.info("WorkflowExecutorService initialized and stored in Singleton.") # English Hardcode

        api_server = ApiServerService(mock_kernel, "api_server_service")
        _harden_api_server(api_server)
        Singleton.set_instance(ApiServerService, api_server)
        logging.info("ApiServerService initialized and stored in Singleton.") # English Hardcode

    except Exception as e:
        logging.error(f"CRITICAL: Failed to initialize core services: {e}", exc_info=True) # English Hardcode
        sys.exit(1)

    try:
        preset_manager = PresetManagerService(mock_kernel, "preset_manager_service")
        preset_manager.start() # Panggil start() untuk inject db_service
        Singleton.set_instance(PresetManagerService, preset_manager)

        module_manager = ModuleManagerService(mock_kernel, "module_manager_service")
        module_manager.discover_and_load_modules()
        Singleton.set_instance(ModuleManagerService, module_manager)

        plugin_manager = PluginManagerService(mock_kernel, "plugin_manager_service")
        plugin_manager.discover_and_load_plugins()
        Singleton.set_instance(PluginManagerService, plugin_manager)

        tools_manager = ToolsManagerService(mock_kernel, "tools_manager_service")
        tools_manager.discover_and_load_tools()
        Singleton.set_instance(ToolsManagerService, tools_manager)

        trigger_manager = TriggerManagerService(mock_kernel, "trigger_manager_service")
        trigger_manager.discover_and_load_triggers()
        Singleton.set_instance(TriggerManagerService, trigger_manager)

        ai_provider_manager = AIProviderManagerService(mock_kernel, "ai_provider_manager_service")
        Singleton.set_instance(AIProviderManagerService, ai_provider_manager)

        logging.info("All component managers initialized and stored in Singleton.") # English Hardcode

        kernel_services = {
            "preset_manager_service": preset_manager,
            "workflow_executor_service": workflow_executor,
            "module_manager_service": module_manager,
            "plugin_manager_service": plugin_manager,
            "tools_manager_service": tools_manager,
            "trigger_manager_service": trigger_manager,
            "ai_provider_manager_service": ai_provider_manager,
            "api_server_service": api_server, # (PENAMBAHAN KODE)
            "localization_manager": loc_manager, # (PENAMBAHAN KODE BARU)
            "state_manager_service": state_manager, # (PENAMBAHAN KODE OLEH GEMINI)
        }
        gateway_connector.set_kernel_services(kernel_services)
        logging.info("Core services injected into GatewayConnectorService.") # English Hardcode

    except Exception as e:
        logging.error(f"CRITICAL: Failed to initialize component managers: {e}", exc_info=True) # English Hardcode
        sys.exit(1)

    num_workers = os.cpu_count()
    logging.info(f"Starting {num_workers} worker processes...") # English Hardcode
    for _ in range(num_workers):
        try:
            p = Process(target=worker_process, args=(DB_PATH, project_root))
            p.start()
            workers.append(p)
        except Exception as e:
            logging.error(f"Failed to start a worker process: {e}") # English Hardcode
    logging.info(f"All {len(workers)} workers started successfully.") # English Hardcode

    start_heartbeat()

    try:
        asyncio.run(main_async(gateway_connector))
    except ImportError as e:
        print(f"[FATAL] Failed to import core logic: {e}") # English Hardcode
    except KeyboardInterrupt:
        print("\n[INFO] Shutdown signal received. Stopping Core Server...") # English Hardcode
    except Exception as e:
        print(f"[FATAL] A critical error occurred: {e}") # English Hardcode
        traceback.print_exc()
    finally:
        logging.info("Initiating graceful shutdown for workers...") # English Hardcode
        for w in workers:
            try:
                w.join(timeout=5)
                if w.is_alive():
                    logging.warning(f"Worker {w.pid} did not exit gracefully. Terminating...") # English Hardcode
                    w.terminate()
            except Exception as e:
                logging.error(f"Error during worker shutdown: {e}") # English Hardcode

        if gateway_connector:
            try:
                asyncio.run(gateway_connector.stop())
            except Exception as e:
                logging.error(f"Error stopping GatewayConnectorService: {e}") # English Hardcode

        logging.info("All processes stopped.") # English Hardcode
        print("[SUCCESS] Core Server stopped gracefully.") # English Hardcode

if __name__ == "__main__":
    multiprocessing.freeze_support()
    load_dotenv()
    display_banner()
    core_path = os.path.abspath(os.path.dirname(__file__))
    if core_path not in sys.path:
        sys.path.insert(0, core_path)
    ensure_packages_exist()
    main()
