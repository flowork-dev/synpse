########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\gateway_connector_service\gateway_connector_service.py total lines 901 
########################################################################

import socketio
import os
import asyncio
import logging
import uuid
import json
import multiprocessing
import requests
import time
from dotenv import load_dotenv
from flowork_kernel.services.base_service import BaseService
from flowork_kernel.singleton import Singleton
from flowork_kernel.services.database_service.database_service import DatabaseService
from flowork_kernel.services.variable_manager_service.variable_manager_service import VariableManagerService

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))
CURRENT_PAYLOAD_VERSION = 2

class GatewayConnectorService(BaseService):
    def __init__(self, kernel, service_id):
        super().__init__(kernel, service_id)
        self.sio = socketio.AsyncClient(
            logger=False,
            engineio_logger=False,
            reconnection=True,
            reconnection_delay=5,
            reconnection_attempts=0 # 0 means infinite retries
        )
        self.gateway_url = os.getenv("GATEWAY_API_URL", "http://gateway:8000")
        self.engine_token = os.getenv("FLOWORK_ENGINE_TOKEN")
        self.engine_id = os.getenv("FLOWORK_ENGINE_ID")
        self.kernel_services = {}
        self.user_id = None                                  # (ADD) cache user id from auth_success
        self.internal_api_url = None                         # (ADD) cache internal api url for heartbeat
        self._hb_task = None                                 # (ADD) heartbeat task handle
        self.logger.info(f"GatewayConnectorService (Socket.IO Client Mode) initialized. URL: {self.gateway_url}") # (English Hardcode)
        self.register_event_handlers()

    def _resolve_home_gateway(self) -> str:
        """
        (ADDED FOR ROADMAP 4.1)
        (English Hardcode) Calls the Gateway's public resolver endpoint to find our home.
        """
        try:
            resolver_url = f"{self.gateway_url}/api/v1/cluster/resolve-home?key={self.engine_id}" #
            self.logger.info(f"[GatewayConnector] Resolving home gateway via: {resolver_url}") # (English Hardcode)
            res = requests.get(resolver_url, timeout=5.0) #
            res.raise_for_status() #
            data = res.json() #
            home_url = data.get("home_url") # e.g., "http://gw-b:8000"
            if not home_url:
                raise ValueError("Resolver did not return 'home_url'") # (English Hardcode)
            self.logger.info(f"[GatewayConnector] Home gateway resolved to: {data.get('home_id')}") # (English Hardcode)
            return home_url # (English Hardcode) Return "http://gw-b:8000"
        except Exception as e:
            self.logger.error(f"[GatewayConnector] CRITICAL: Failed to resolve home gateway: {e}") # (English Hardcode)
            self.logger.warning("[GatewayConnector] Fallback: connecting to default GATEWAY_API_URL.") # (English Hardcode)
            return self.gateway_url #

    def set_kernel_services(self, kernel_services: dict):
        """
        (English Hardcode) Inject kernel services from the main runner.
        """
        self.kernel_services = kernel_services #
        self.logger.info(f"Kernel services injected. {len(self.kernel_services)} services loaded.") # (English Hardcode)

    def register_event_handlers(self):
        @self.sio.event(namespace='/engine-socket') #
        async def connect():
            self.logger.info("Attempting to connect to Gateway at {}...".format(self.gateway_url)) # (English Hardcode)
            try:
                self.logger.info(f"Connection to /engine-socket established. Auth was sent in connect() call.") # (English Hardcode)
            except Exception as e:
                self.logger.error(f"Error during connect event: {e}", exc_info=True) # (English Hardcode)

        @self.sio.event(namespace='/engine-socket') #
        async def auth_success(data):
            user_id = data.get('user_id') #
            self.user_id = user_id                                  # (ADD) cache
            self.logger.info(f"Engine authenticated successfully for user: {user_id}") # (English Hardcode)

            try:
                await asyncio.sleep(0.5)

                api_server = self.kernel_services.get("api_server_service")
                loc_manager = self.kernel_services.get("localization_manager") # <-- (FIX 1) Get loc manager directly

                if not api_server or not loc_manager:
                    self.logger.error("[GatewayConnector] CRITICAL: ApiServer or LocalizationManager not found in kernel_services. Cannot send 'engine_ready'.") # (English Hardcode)
                    return

                port = loc_manager.get_setting("webhook_port", 8990) # <-- (FIX 2) Call get_setting on the real service

                internal_host = "flowork_core"
                internal_api_url = f"http://{internal_host}:{port}"
                self.internal_api_url = internal_api_url             # (ADD) cache for heartbeat


                ready_payload_v2 = {
                    'internal_api_url': internal_api_url,
                    'engine_id': self.engine_id,
                    'user_id': self.user_id,
                    'capabilities': ['workflow', 'datasets', 'variables']  # (ADD) hint capabilities
                }
                await self.sio.emit('engine_ready', ready_payload_v2, namespace='/engine-socket') # (ADD) flat payload
                self.logger.info(f"Sent 'engine_ready' to Gateway. Reported internal URL: {internal_api_url}") # (English Hardcode)

                if self._hb_task is None or self._hb_task.done():
                    self._hb_task = asyncio.create_task(self._engine_heartbeat())  # (ADD) heartbeat

            except Exception as e:
                self.logger.error(f"Failed to send 'engine_ready' event after auth: {e}", exc_info=True) # (English Hardcode)

        @self.sio.event(namespace='/engine-socket') #
        async def auth_failed(data):
            error_message = data.get('error') #
            self.logger.error(f"Engine authentication failed: {error_message}") # (English Hardcode)
            await self.stop() #

        @self.sio.event(namespace='/engine-socket') #
        async def disconnect():
            self.logger.info("Disconnected from Gateway /engine-socket.") # (English Hardcode)
            try:
                if self._hb_task and not self._hb_task.done():
                    self._hb_task.cancel()
            except Exception as _:
                pass

        @self.sio.event(namespace='/engine-socket') #
        async def request_presets_list(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: #
                self.logger.error(f"[Core] Received non-versioned 'request_presets_list'. Ignoring.") # (English log)
                return
            real_data = data.get('payload', {}) #
            user_context = real_data.get('user_context', {}) # (MODIFIED) Use real_data
            user_id = user_context.get('id') #
            self.logger.info(f"Received 'request_presets_list' from user {user_id}") # (English Hardcode)
            try:
                preset_manager = self.kernel_services.get("preset_manager_service") #
                if preset_manager:
                    presets = preset_manager.get_preset_list(user_id) #
                    versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {'presets': presets}} #
                    await self.sio.emit('response_presets_list', versioned_response, namespace='/engine-socket') # (MODIFIED)
                    self.logger.info(f"Sent preset list to user {user_id}. Count: {len(presets)}") # (English Hardcode)
                else:
                    self.logger.error("'preset_manager_service' not found in kernel services.") # (English Hardcode)
                    versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {'presets': [], 'error': 'Preset service unavailable'}} #
                    await self.sio.emit('response_presets_list', versioned_response, namespace='/engine-socket') # (MODIFIED)
            except Exception as e:
                self.logger.error(f"Error processing 'request_presets_list': {e}", exc_info=True) # (English Hardcode)
                versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {'presets': [], 'error': str(e)}} #
                await self.sio.emit('response_presets_list', versioned_response, namespace='/engine-socket') # (MODIFIED)

        @self.sio.event(namespace='/engine-socket') #
        async def execute_workflow(data):
            """
            (English Hardcode) Handler for 'execute_workflow' proxied from GUI.
            (English Hardcode) (MODIFIED - FASE 14) This now inserts jobs directly into the SQL database.
            """
            try:
                if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: #
                    self.logger.error(f"[Core] Received non-versioned 'execute_workflow'. Ignoring.") # (English log)
                    return
                real_data = data.get('payload', {}) #
                user_context = real_data.get('user_context', {}) # (MODIFIED) Use real_data
                user_id = user_context.get('id') #
                execution_id = real_data.get('job_id') # (MODIFIED) Use real_data, this is the Execution ID
                workflow_id = real_data.get('preset_name') # (MODIFIED) Use real_data
                initial_payload = real_data.get('initial_payload', {}) # (MODIFIED) Use real_data
                workflow_data = real_data.get('workflow_data', {}) # (English Hardcode) Get nodes/edges from payload
                start_node_id = real_data.get('start_node_id') # (English Hardcode) Get specific start node
                self.logger.info(f"Received 'execute_workflow' for user {user_id} (Exec ID: {execution_id}") # (English Hardcode)
                db_service = Singleton.get_instance(DatabaseService) #
                if not db_service: # (English Hardcode) Removed preset_manager check
                    self.logger.error("'db_service' not found. Cannot execute.") # (English Hardcode)
                    return
                nodes = workflow_data.get('nodes', []) #
                edges = workflow_data.get('connections', []) # (FIX) Key is 'connections'
                target_node_ids = {edge['target'] for edge in edges} #
                if start_node_id: #
                    starting_nodes = [start_node_id] # (English Hardcode) User specified start node
                    self.logger.info(f"Starting workflow {execution_id} from specific node: {start_node_id}") # (English Hardcode)
                else:
                    starting_nodes = [node['id'] for node in nodes if node['id'] not in target_node_ids] #
                if not starting_nodes: #
                    self.logger.warning(f"Workflow {workflow_id} has no starting nodes. Execution stopped.") # (English Hardcode)
                    return
                conn = db_service.create_connection() #
                if not conn: #
                    self.logger.error("Failed to create DB connection. Cannot queue jobs.") # (English Hardcode)
                    return
                try:
                    cursor = conn.cursor() #
                    cursor.execute( #
                        "INSERT INTO Executions (execution_id, workflow_id, user_id, status) VALUES (?, ?, ?, ?)",
                        (execution_id, workflow_id, user_id, 'RUNNING')
                    )
                    jobs_to_insert = [] #
                    for node_id in starting_nodes: #
                        job_id = str(uuid.uuid4()) #
                        jobs_to_insert.append(( #
                            job_id,
                            execution_id,
                            node_id,
                            'PENDING',
                            json.dumps(initial_payload) # (English Hardcode) Pass initial payload to all starting nodes
                        ))
                    cursor.executemany( #
                        "INSERT INTO Jobs (job_id, execution_id, node_id, status, input_data) VALUES (?, ?, ?, ?, ?)",
                        jobs_to_insert
                    )
                    conn.commit() #
                    self.logger.info(f"Successfully queued {len(starting_nodes)} starting jobs in DB for Exec ID: {execution_id}") # (English Hardcode)
                    try:
                        job_event = Singleton.get_instance(multiprocessing.Event) #
                        if job_event: #
                            job_event.set() #
                            self.logger.debug(f"Job event (bell) set for Exec ID: {execution_id}") # (English Hardcode)
                        else:
                            self.logger.error("Failed to get job_event from Singleton. Workers may not wake up immediately.") # (English Hardcode)
                    except Exception as e:
                        self.logger.error(f"Error while setting job_event (bell): {e}", exc_info=True) # (English Hardcode)
                except Exception as e:
                    conn.rollback() #
                    self.logger.error(f"Failed to insert jobs into DB: {e}", exc_info=True) # (English Hardcode)
                finally:
                    conn.close() #
            except Exception as e:
                self.logger.error(f"Error handling 'execute_workflow': {e}", exc_info=True) # (English Hardcode)

        @self.sio.event(namespace='/engine-socket') #
        async def save_preset(data):
            """
            (English Hardcode) Handler for 'save_preset' proxied from GUI.
            """
            try:
                if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: #
                    self.logger.error(f"[Core] Received non-versioned 'save_preset'. Ignoring.") # (English log)
                    return
                real_data = data.get('payload', {}) #
                user_context = real_data.get('user_context', {}) # (MODIFIED) Use real_data
                user_id = user_context.get('id') #
                preset_name = real_data.get('preset_name') # (MODIFIED) Use real_data
                preset_data = real_data.get('preset_data') # (MODIFIED) Use real_data
                signature = real_data.get('signature') # <-- START ADDED CODE (FIX)
                if not signature: # <-- START ADDED CODE (FIX)
                    self.logger.error(f"Received 'save_preset' without signature from user {user_id}. Ignoring.") # (English Hardcode)
                    return
                self.logger.info(f"Received 'save_preset' request from user {user_id} for preset: {preset_name}") # (English Hardcode)
                preset_manager = self.kernel_services.get("preset_manager_service") #
                if not preset_manager: #
                    self.logger.error("'preset_manager_service' not found. Cannot save preset.") # (English Hardcode)
                    return
                preset_manager.save_preset( #
                    name=preset_name,
                    workflow_data=preset_data,
                    user_id=user_id,
                    signature=signature
                )
                self.logger.info(f"Successfully saved preset {preset_name} for user {user_id}") # (English Hardcode)
            except Exception as e:
                self.logger.error(f"Error handling 'save_preset': {e}", exc_info=True) # (English Hardcode)

        @self.sio.event(namespace='/engine-socket') #
        async def request_variables(data):
            try:
                if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: #
                    self.logger.error(f"[Core] Received non-versioned 'request_variables'. Ignoring.") # (English log)
                    return
                real_data = data.get('payload', {}) #
                user_id = real_data.get('user_context', {}).get('id') # (MODIFIED) Use real_data
                self.logger.info(f"Received 'request_variables' from user {user_id}") # (English Hardcode)
                variable_manager = Singleton.get_instance(VariableManagerService) #
                variables_list = [] #
                if variable_manager: #
                    variables_list = variable_manager.get_all_variables_for_api(user_id=user_id) #
                else:
                    self.logger.error("VariableManagerService not found in Singleton. Cannot get variables.") # (English Hardcode)
                versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {'variables': variables_list}} #
                await self.sio.emit('response_variables', versioned_response, namespace='/engine-socket') # (MODIFIED)
                self.logger.info(f"Sent 'response_variables' back to user {user_id}") # (English Hardcode)
            except Exception as e:
                self.logger.error(f"Error handling 'request_variables': {e}", exc_info=True) # (English Hardcode)


        @self.sio.event(namespace='/engine-socket')
        async def request_components_list(data):
            """ (English Hardcode) Handles request for component lists from Gateway """
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION:
                self.logger.error(f"[Core] Received non-versioned 'request_components_list'. Ignoring.")
                return

            real_data = data.get('payload', {})
            user_context = real_data.get('user_context', {})
            user_id = user_context.get('id')
            component_type = real_data.get('component_type')
            self.logger.info(f"Received 'request_components_list' from user {user_id} for type: {component_type}")

            manager_map = {
                'modules': 'module_manager_service',
                'plugins': 'plugin_manager_service',
                'tools': 'tools_manager_service',
                'triggers': 'trigger_manager_service'
            }
            manager_name = manager_map.get(component_type)
            components_list = []
            error_msg = None

            if manager_name:
                manager = self.kernel_services.get(manager_name)
                if manager:
                    try:
                        items_attr_map = {
                            "module_manager_service": "loaded_modules",
                            "plugin_manager_service": "loaded_plugins",
                            "tools_manager_service": "loaded_tools",
                            "trigger_manager_service": "loaded_triggers",
                        }
                        items_attr_name = items_attr_map.get(manager.service_id)
                        items = getattr(manager, items_attr_name, {})

                        for item_id_loop, item_data in items.items():
                            manifest = item_data.get("manifest", {})
                            components_list.append(
                                {
                                    "id": item_id_loop,
                                    "name": manifest.get("name", item_id_loop),
                                    "version": manifest.get("version", "N/A"),
                                    "is_paused": item_data.get("is_paused", False),
                                    "description": manifest.get("description", ""),
                                    "is_core": False, # (English Hardcode) TODO: Add core file check
                                    "tier": manifest.get("tier", "free"),
                                    "is_installed": item_data.get("is_installed", False),
                                    "manifest": manifest,
                                }
                            )
                    except Exception as e:
                        error_msg = f"Error processing component list: {e}"
                        self.logger.error(f"[Core] {error_msg}", exc_info=True)
                else:
                    error_msg = f"Component manager '{manager_name}' not found."
                    self.logger.error(f"[Core] {error_msg}")
            else:
                error_msg = f"Invalid component type '{component_type}'."
                self.logger.error(f"[Core] {error_msg}")

            versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {
                'component_type': component_type,
                'components': components_list,
                'error': error_msg
            }}
            await self.sio.emit('response_component_list', versioned_response, namespace='/engine-socket')
            self.logger.info(f"Sent 'response_component_list' for {component_type} to user {user_id}. Count: {len(components_list)}")

        @self.sio.event(namespace='/engine-socket')
        async def request_settings(data):
            """ (English Hardcode) Handles request for settings from Gateway """
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION:
                self.logger.error(f"[Core] Received non-versioned 'request_settings'. Ignoring.")
                return

            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            self.logger.info(f"Received 'request_settings' from user {user_id}")
            settings_data = {}
            error_msg = None
            try:
                loc_manager = self.kernel_services.get("localization_manager")
                if loc_manager:
                    settings_data = loc_manager.get_all_settings(user_id=user_id)
                else:
                    error_msg = "LocalizationManager not found."
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"[Core] Error processing 'request_settings': {e}", exc_info=True)

            versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {
                'settings': settings_data,
                'error': error_msg
            }}
            await self.sio.emit('settings_response', versioned_response, namespace='/engine-socket')
            self.logger.info(f"Sent 'settings_response' to user {user_id}")

        @self.sio.event(namespace='/engine-socket')
        async def save_settings(data):
            """ (English Hardcode) Handles save settings request from Gateway """
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION:
                self.logger.error(f"[Core] Received non-versioned 'save_settings'. Ignoring.")
                return

            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            settings_to_save = real_data.get('settings')
            self.logger.info(f"Received 'save_settings' from user {user_id}")
            try:
                loc_manager = self.kernel_services.get("localization_manager")
                if loc_manager:
                    loc_manager._save_settings(settings_to_save, user_id=user_id)
                else:
                    raise Exception("LocalizationManager not found.")
            except Exception as e:
                self.logger.error(f"[Core] Error processing 'save_settings': {e}", exc_info=True)

        @self.sio.event(namespace='/engine-socket')
        async def update_variable(data):
            """ (English Hardcode) Handles variable update from Gateway """
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION:
                return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            var_name = real_data.get('name')
            var_data = real_data.get('data')
            self.logger.info(f"Received 'update_variable' from user {user_id} for var: {var_name}")
            try:
                var_manager = Singleton.get_instance(VariableManagerService)
                if var_manager:
                    var_manager.set_variable(
                        var_name,
                        var_data.get('value'),
                        var_data.get('is_secret', False),
                        var_data.get('is_enabled', True),
                        mode=var_data.get('mode', 'single'),
                        user_id=user_id
                    )
            except Exception as e:
                 self.logger.error(f"[Core] Error processing 'update_variable': {e}", exc_info=True)

        @self.sio.event(namespace='/engine-socket')
        async def delete_variable(data):
            """ (English Hardcode) Handles variable delete from Gateway """
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION:
                return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            var_name = real_data.get('name')
            self.logger.info(f"Received 'delete_variable' from user {user_id} for var: {var_name}")
            try:
                var_manager = Singleton.get_instance(VariableManagerService)
                if var_manager:
                    var_manager.delete_variable(var_name, user_id=user_id)
            except Exception as e:
                self.logger.error(f"[Core] Error processing 'delete_variable': {e}", exc_info=True)

        @self.sio.event(namespace='/engine-socket')
        async def request_prompts_list(data):
            """ (English Hardcode) Handles request for prompts list from Gateway """
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION:
                return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            self.logger.info(f"Received 'request_prompts_list' from user {user_id}")
            prompts_list = []
            error_msg = None
            try:
                prompt_manager = self.kernel_services.get("prompt_manager_service")
                if prompt_manager:
                    prompts_list = prompt_manager.get_all_prompts()
                else:
                    error_msg = "PromptManagerService not found."
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"[Core] Error processing 'request_prompts_list': {e}", exc_info=True)

            versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {
                'prompts': prompts_list,
                'error': error_msg
            }}
            await self.sio.emit('response_prompts_list', versioned_response, namespace='/engine-socket')
            self.logger.info(f"Sent 'response_prompts_list' to user {user_id}")

        @self.sio.event(namespace='/engine-socket')
        async def update_prompt(data):
            """ (English Hardcode) Handles create/update prompt from Gateway """
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION:
                return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            prompt_data = real_data.get('prompt_data')
            self.logger.info(f"Received 'update_prompt' from user {user_id}")
            try:
                prompt_manager = self.kernel_services.get("prompt_manager_service")
                if prompt_manager:
                    if 'id' in prompt_data and prompt_data['id']:
                        prompt_manager.update_prompt(prompt_data['id'], prompt_data)
                    else:
                        prompt_manager.create_prompt(prompt_data)
                    await request_prompts_list(data)
                else:
                    raise Exception("PromptManagerService not found.")
            except Exception as e:
                self.logger.error(f"[Core] Error processing 'update_prompt': {e}", exc_info=True)

        @self.sio.event(namespace='/engine-socket')
        async def delete_prompt(data):
            """ (English Hardcode) Handles delete prompt from Gateway """
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION:
                return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            prompt_id = real_data.get('prompt_id')
            self.logger.info(f"Received 'delete_prompt' from user {user_id} for prompt: {prompt_id}")
            try:
                prompt_manager = self.kernel_services.get("prompt_manager_service")
                if prompt_manager:
                    prompt_manager.delete_prompt(prompt_id)
                    await request_prompts_list(data) # (English Hardcode) Send refresh
                else:
                    raise Exception("PromptManagerService not found.")
            except Exception as e:
                self.logger.error(f"[Core] Error processing 'delete_prompt': {e}", exc_info=True)


        @self.sio.event(namespace='/engine-socket')
        async def request_local_models(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            self.logger.info(f"Received 'request_local_models' from user {user_id}")
            models_list = []
            error_msg = None
            try:
                ai_manager = self.kernel_services.get("ai_provider_manager_service")
                if ai_manager:
                    models_list = [
                        {"id": model_id, "name": model_data.get("name", model_id)}
                        for model_id, model_data in ai_manager.local_models.items()
                        if model_data.get("category") == "text" # (English Hardcode) Only text models for now
                    ]
                else:
                    error_msg = "AIProviderManagerService not found."
            except Exception as e:
                error_msg = str(e)
            versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {'models': models_list, 'error': error_msg}}
            await self.sio.emit('response_local_models', versioned_response, namespace='/engine-socket')

        @self.sio.event(namespace='/engine-socket')
        async def start_training_job(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            config = real_data.get('config')
            self.logger.info(f"Received 'start_training_job' from user {user_id} for {config.get('new_model_name')}")
            job_response = None
            try:
                training_service = self.kernel_services.get("ai_training_service")
                if training_service:
                    job_response = training_service.start_fine_tuning_job(
                        base_model_id=config.get('base_model_id'),
                        dataset_name=config.get('dataset_name'),
                        new_model_name=config.get('new_model_name'),
                        training_args=config.get('training_args', {})
                    )
                    await request_training_job_status(data)
                else:
                    raise Exception("AITrainingService not found.")
            except Exception as e:
                self.logger.error(f"[Core] Error processing 'start_training_job': {e}", exc_info=True)

        @self.sio.event(namespace='/engine-socket')
        async def request_training_job_status(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            self.logger.info(f"Received 'request_training_job_status' from user {user_id}")
            jobs_list = []
            error_msg = None
            try:
                training_service = self.kernel_services.get("ai_training_service")
                if training_service:
                    jobs_list = list(training_service.training_jobs.values())
                else:
                    error_msg = "AITrainingService not found."
            except Exception as e:
                error_msg = str(e)
            versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {'jobs': jobs_list, 'error': error_msg}}
            await self.sio.emit('response_training_job_status', versioned_response, namespace='/engine-socket')

        @self.sio.event(namespace='/engine-socket')
        async def request_datasets_list(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            self.logger.info(f"Received 'request_datasets_list' from user {user_id}")
            datasets_list = []
            error_msg = None
            try:
                dataset_manager = self.kernel_services.get("dataset_manager_service")
                if dataset_manager:
                    datasets_list = dataset_manager.list_datasets()
                else:
                    error_msg = "DatasetManagerService not found."
            except Exception as e:
                error_msg = str(e)
            versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {'datasets': datasets_list, 'error': error_msg}}
            await self.sio.emit('response_datasets_list', versioned_response, namespace='/engine-socket')

        @self.sio.event(namespace='/engine-socket')
        async def load_dataset_data(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            name = real_data.get('name')
            self.logger.info(f"Received 'load_dataset_data' from user {user_id} for {name}")
            dataset_data = []
            error_msg = None
            try:
                dataset_manager = self.kernel_services.get("dataset_manager_service")
                if dataset_manager:
                    dataset_data = dataset_manager.get_dataset_data(name)
                else:
                    error_msg = "DatasetManagerService not found."
            except Exception as e:
                error_msg = str(e)
            versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {'data': dataset_data, 'error': error_msg}}
            await self.sio.emit('response_dataset_data', versioned_response, namespace='/engine-socket')

        @self.sio.event(namespace='/engine-socket')
        async def create_dataset(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            name = real_data.get('name')
            self.logger.info(f"Received 'create_dataset' from user {user_id} for {name}")
            try:
                dataset_manager = self.kernel_services.get("dataset_manager_service")
                if dataset_manager:
                    dataset_manager.create_dataset(name)
                    await request_datasets_list(data) # (English Hardcode) Refresh list
                else:
                    raise Exception("DatasetManagerService not found.")
            except Exception as e:
                self.logger.error(f"[Core] Error processing 'create_dataset': {e}", exc_info=True)

        @self.sio.event(namespace='/engine-socket')
        async def add_dataset_data(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            name = real_data.get('name')
            rows = real_data.get('data')
            self.logger.info(f"Received 'add_dataset_data' from user {user_id} for {name}")
            try:
                dataset_manager = self.kernel_services.get("dataset_manager_service")
                if dataset_manager:
                    dataset_manager.add_data_to_dataset(name, rows)
                    await load_dataset_data(data) # (English Hardcode) Refresh data
                else:
                    raise Exception("DatasetManagerService not found.")
            except Exception as e:
                self.logger.error(f"[Core] Error processing 'add_dataset_data': {e}", exc_info=True)

        @self.sio.event(namespace='/engine-socket')
        async def delete_dataset(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            name = real_data.get('name')
            self.logger.info(f"Received 'delete_dataset' from user {user_id} for {name}")
            try:
                dataset_manager = self.kernel_services.get("dataset_manager_service")
                if dataset_manager:
                    dataset_manager.delete_dataset(name)
                    await request_datasets_list(data) # (English Hardcode) Refresh list
                else:
                    raise Exception("DatasetManagerService not found.")
            except Exception as e:
                self.logger.error(f"[Core] Error processing 'delete_dataset': {e}", exc_info=True)

        @self.sio.event(namespace='/engine-socket')
        async def update_dataset_row(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            name = real_data.get('name')
            row_data = real_data.get('row_data')
            self.logger.info(f"Received 'update_dataset_row' from user {user_id} for {name}")
            try:
                dataset_manager = self.kernel_services.get("dataset_manager_service")
                if dataset_manager:
                    dataset_manager.update_dataset_row(name, row_data)
                    await load_dataset_data(data) # (English Hardcode) Refresh data
                else:
                    raise Exception("DatasetManagerService not found.")
            except Exception as e:
                self.logger.error(f"[Core] Error processing 'update_dataset_row': {e}", exc_info=True)

        @self.sio.event(namespace='/engine-socket')
        async def delete_dataset_row(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            name = real_data.get('name')
            row_id = real_data.get('row_id')
            self.logger.info(f"Received 'delete_dataset_row' from user {user_id} for {name}")
            try:
                dataset_manager = self.kernel_services.get("dataset_manager_service")
                if dataset_manager:
                    dataset_manager.delete_dataset_row(name, row_id)
                    await load_dataset_data(data) # (English Hardcode) Refresh data
                else:
                    raise Exception("DatasetManagerService not found.")
            except Exception as e:
                self.logger.error(f"[Core] Error processing 'delete_dataset_row': {e}", exc_info=True)


        @self.sio.event(namespace='/engine-socket')
        async def install_component(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            component_type = real_data.get('component_type')
            component_id = real_data.get('component_id')
            self.logger.info(f"Received 'install_component' from user {user_id} for {component_id}")

            manager_map = {
                'modules': 'module_manager_service',
                'plugins': 'plugin_manager_service',
                'tools': 'tools_manager_service',
                'triggers': 'trigger_manager_service'
            }
            manager_name = manager_map.get(component_type)
            manager = self.kernel_services.get(manager_name)

            if not manager:
                self.logger.error(f"Cannot install {component_id}: Manager {manager_name} not found.")
                return

            def on_complete(cid, success, message):
                self.logger.info(f"Install complete for {cid}: Success={success}, Msg={message}")
                async def send_update():
                     versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {
                        'component_id': cid,
                        'component_type': component_type,
                        'success': success,
                        'message': message,
                        'is_installed': True
                    }}
                     await self.sio.emit('component_install_status', versioned_response, namespace='/engine-socket')
                     await request_components_list(data) # (English Hardcode) Refresh list
                asyncio.run(send_update())

            manager.install_component_dependencies(component_id, on_complete)

        @self.sio.event(namespace='/engine-socket')
        async def uninstall_component(data):
            if not isinstance(data, dict) or data.get('v') != CURRENT_PAYLOAD_VERSION: return
            real_data = data.get('payload', {})
            user_id = real_data.get('user_context', {}).get('id')
            component_type = real_data.get('component_type')
            component_id = real_data.get('component_id')
            self.logger.info(f"Received 'uninstall_component' from user {user_id} for {component_id}")

            manager_map = {
                'modules': 'module_manager_service',
                'plugins': 'plugin_manager_service',
                'tools': 'tools_manager_service',
                'triggers': 'trigger_manager_service'
            }
            manager_name = manager_map.get(component_type)
            manager = self.kernel_services.get(manager_name)

            if not manager:
                self.logger.error(f"Cannot uninstall {component_id}: Manager {manager_name} not found.")
                return

            def on_complete(cid, success, message):
                self.logger.info(f"Uninstall complete for {cid}: Success={success}, Msg={message}")
                async def send_update():
                    versioned_response = {'v': CURRENT_PAYLOAD_VERSION, 'payload': {
                        'component_id': cid,
                        'component_type': component_type,
                        'success': success,
                        'message': message,
                        'is_installed': False
                    }}
                    await self.sio.emit('component_install_status', versioned_response, namespace='/engine-socket')
                    await request_components_list(data) # (English Hardcode) Refresh list
                asyncio.run(send_update())

            manager.uninstall_component_dependencies(component_id, on_complete)


        @self.sio.on('*', namespace='/engine-socket') #
        async def catch_all(event, data):
            known_events = [ #
                'connect',
                'auth_success',
                'auth',
                'auth_failed',
                'disconnect',
                'request_presets_list',
                'save_preset',
                'request_variables',
                'engine_ready',
                'engine_vitals_update',
                'forward_event_to_gui',
                'execute_workflow',
                'request_components_list',
                'request_settings',
                'save_settings',
                'update_variable',
                'delete_variable',
                'request_prompts_list',
                'update_prompt',
                'delete_prompt',
                'request_local_models',
                'start_training_job',
                'request_training_job_status',
                'request_datasets_list',
                'load_dataset_data',
                'create_dataset',
                'add_dataset_data',
                'delete_dataset',
                'update_dataset_row',
                'delete_dataset_row',
                'install_component',
                'uninstall_component'
            ]
            if event not in known_events: #
                self.logger.warning(f"Received unhandled event '{event}' in /engine-socket namespace.") # (English Hardcode)

    async def _engine_heartbeat(self):
        """
        (English) Periodically send engine vitals to Gateway so it can keep user↔engine mapping alive.
        """
        self.logger.info("[GatewayConnector] Heartbeat task started.")  # (ADD)
        try:
            while True:
                try:
                    payload = {
                        'engine_id': self.engine_id,
                        'user_id': self.user_id,
                        'internal_api_url': self.internal_api_url,
                        'ts': int(time.time()),
                        'metrics': {
                            'pid': os.getpid(),
                        }
                    }
                    await self.sio.emit('engine_vitals_update', payload, namespace='/engine-socket')
                except Exception as e:
                    self.logger.error(f"[GatewayConnector] Heartbeat error: {e}", exc_info=True)
                await asyncio.sleep(10)  # (ADD) every 10s
        except asyncio.CancelledError:
            self.logger.info("[GatewayConnector] Heartbeat task cancelled.")
        except Exception as e:
            self.logger.error(f"[GatewayConnector] Heartbeat task crashed: {e}", exc_info=True)

    async def start(self):
        if not self.engine_id or not self.engine_token or not self.gateway_url: #
            self.logger.error("GatewayConnectorService not properly set up. Missing URL, Engine ID or Token.") # (English Hardcode)
            return
        self.logger.info(f"Starting GatewayConnectorService, resolving home gateway from {self.gateway_url}...") # (English Hardcode)
        resolved_http_url = self._resolve_home_gateway() # (English Hardcode) This is http://...:8000

        if resolved_http_url.startswith("https://"): # English Hardcode
            connect_url = resolved_http_url.replace("https://", "wss://") # English Hardcode
        else:
            connect_url = resolved_http_url.replace("http://", "ws://") # English Hardcode

        socketio_path = "/api/socket.io" # (FIX) Pastikan ini konsisten dengan GUI & Gateway
        self.logger.info(f"[GatewayConnector] Connecting to WebSocket at: {connect_url} with path {socketio_path}") # (FIX) Log URL & path

        auth_payload = { #
            'engine_id': self.engine_id,
            'token': self.engine_token
        }

        while True: #
            try:
                await self.sio.connect( #
                    connect_url, # (FIX) Gunakan URL yang udah di-resolve
                    headers={"Authorization": f"Bearer {self.engine_token}"}, # (ADD) Header (meski mungkin tdk dipake)
                    auth=auth_payload, # (English) Send plain auth fields expected by Gateway
                    namespaces=['/engine-socket'], #
                    socketio_path=socketio_path # (ADD) Path SocketIO
                )
                self.logger.info(f"[GatewayConnector] Initial connection successful to {connect_url}") # (English Hardcode)
                await self.sio.wait() #
            except socketio.exceptions.ConnectionError as e: #
                self.logger.error(f"Failed to connect to Gateway at {connect_url}: {e}. Retrying in 5 seconds...") # (FIX) Log URL yg bener
            except Exception as e:
                self.logger.error(f"An unexpected error occurred in GatewayConnectorService: {e}. Retrying in 5 seconds...", exc_info=True) # (English Hardcode)
            finally:
                self.logger.info("GatewayConnectorService stopped. Will attempt to restart connection loop.") # (English Hardcode)
                await asyncio.sleep(5) # (English Hardcode) Wait 5 seconds before retrying

    async def stop(self):
        self.logger.info("Stopping GatewayConnectorService...") # (English Hardcode)
        try:
            if self._hb_task and not self._hb_task.done():       # (ADD) stop heartbeat when stopping
                self._hb_task.cancel()
            if self.sio.connected: #
                await self.sio.disconnect() #
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}", exc_info=True) # (English Hardcode)
