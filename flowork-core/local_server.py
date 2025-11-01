#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\local_server.py JUMLAH BARIS 897 
#######################################################################

import asyncio
import websockets
import json
import traceback
import sys
import os
import threading
import uuid
import requests # Dibutuhkan untuk memanggil Gateway
from urllib.parse import urlparse, parse_qs # Baru: Untuk parse query param
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("[LocalServer] WARNING: psutil library not found. System vitals will not be sent.") # English Hardcode
from web3.auto import w3
from eth_account.messages import encode_defunct
from flowork_kernel.kernel import Kernel
MY_ENGINE_ID = os.getenv("FLOWORK_ENGINE_ID")
if not MY_ENGINE_ID:
    print("[LocalServer] CRITICAL: FLOWORK_ENGINE_ID environment variable not set!") # English Hardcode
    print("[LocalServer] Please set this in the .env file with the ID from the GUI.") # English Hardcode
    sys.exit(1) # Gagal start jika ID tidak ada
print(f"[LocalServer] Identifying as Engine ID: {MY_ENGINE_ID}") # English Hardcode
async def send_status_updates(websocket, kernel):
    """
    Background task to periodically send engine status updates to this client.
    """
    global MY_ENGINE_ID, PSUTIL_AVAILABLE
    executor = kernel.get_service("workflow_executor_service")
    while websocket.open:
        try:
            is_busy = False
            if executor:
                is_busy = executor.is_running() # Cek apakah executor sedang sibuk
            cpu_percent = None
            memory_percent = None
            if PSUTIL_AVAILABLE:
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
            status_payload = {
                "type": "engine_status_update", # English Hardcode
                "engineId": MY_ENGINE_ID,
                "isBusy": is_busy,
                "cpuPercent": cpu_percent,
                "memoryPercent": memory_percent,
            }
            await websocket.send(json.dumps(status_payload, default=str))
        except websockets.exceptions.ConnectionClosed:
            print("[LocalServer Status] Connection closed, stopping status updates for this client.") # English Hardcode
            break # Hentikan loop jika koneksi ditutup
        except Exception as e:
            print(f"[LocalServer Status] Error sending status: {e}") # English Hardcode
        await asyncio.sleep(10) # Tunggu 10 detik
def _get_safe_roots(kernel):
    """
    Menggabungkan semua path yang aman: dari config, folder user, drive,
    DAN path volume yang di-map dari host.
    """
    roots = [os.path.abspath(kernel.project_root_path)]
    host_mapped_paths = [
        "/host_desktop", # English Hardcode
        "/host_documents", # English Hardcode
        "/host_videos", # English Hardcode
        "/host_music", # English Hardcode
        "/host_pictures", # English Hardcode
    ]
    for path in host_mapped_paths:
        abs_path = os.path.abspath(path)
        if os.path.isdir(abs_path):
            roots.append(abs_path)
            kernel.write_to_log(f"Added host mapped path to safe roots: {abs_path}", "DEBUG", source="LocalServerFS")
    browseable_paths_config = os.path.join(kernel.data_path, "browseable_paths.json")
    try:
        if os.path.exists(browseable_paths_config):
            with open(browseable_paths_config, "r", encoding="utf-8") as f:
                user_defined_paths = json.load(f)
                if isinstance(user_defined_paths, list):
                    for path in user_defined_paths:
                        if os.path.isdir(path):
                            abs_path = os.path.abspath(path)
                            roots.append(abs_path)
                            kernel.write_to_log(f"Added user defined path to safe roots: {abs_path}", "DEBUG", source="LocalServerFS")
    except Exception as e:
        kernel.write_to_log(f"Could not load or parse 'browseable_paths.json': {e}", "WARN", source="LocalServerFS") # English Hardcode
    if PSUTIL_AVAILABLE:
        try:
            for partition in psutil.disk_partitions(all=False):
                 mountpoint = os.path.abspath(partition.mountpoint)
                 if mountpoint.startswith(('/proc', '/dev', '/sys', '/run', '/var/lib/docker')):
                     continue
                 if os.path.isdir(mountpoint):
                     roots.append(mountpoint)
                     kernel.write_to_log(f"Added partition mount to safe roots: {mountpoint}", "DEBUG", source="LocalServerFS")
        except Exception as e:
            kernel.write_to_log(f"Error listing partitions with psutil: {e}", "WARN", source="LocalServerFS") # English Hardcode
    else:
        if os.path.isdir("/"):
             roots.append("/") # Root filesystem container
             kernel.write_to_log(f"Added container root '/' to safe roots (psutil unavailable).", "DEBUG", source="LocalServerFS")
    unique_roots = sorted(list(set(roots)))
    kernel.write_to_log(f"Final safe filesystem roots determined: {unique_roots}", "INFO", source="LocalServerFS") # English Hardcode
    return unique_roots
def _list_safe_directory(kernel, req_path):
    """List isi direktori dengan aman, hanya dalam safe roots."""
    safe_roots = _get_safe_roots(kernel)
    target_path = None
    if not req_path:
         kernel.write_to_log(f"Listing safe root drives/folders.", "DEBUG", source="LocalServerFS") # English Hardcode
         drive_items = []
         host_mapped_names = {
             "/host_desktop": "My Desktop", # English Hardcode
             "/host_documents": "My Documents", # English Hardcode
             "/host_videos": "My Videos", # English Hardcode
             "/host_music": "My Music", # English Hardcode
             "/host_pictures": "My Pictures", # English Hardcode
         }
         for root in safe_roots:
             abs_root = os.path.abspath(root)
             if not os.path.isdir(abs_root):
                 kernel.write_to_log(f"Skipping invalid safe root: {abs_root}", "WARN", source="LocalServerFS")
                 continue
             name = host_mapped_names.get(abs_root) # Coba dapatkan nama khusus
             if not name: # Jika tidak ada nama khusus, buat nama generik
                 if abs_root == os.path.abspath(kernel.project_root_path):
                     name = "Flowork Project (Container)" # English Hardcode
                 elif abs_root == "/":
                     name = "Container Root ( / )" # English Hardcode
                 elif abs_root == "/app": # Biasanya WORKDIR di Docker
                     name = "Container App ( /app )" # English Hardcode
                 else:
                     name = os.path.basename(abs_root)
                     if not name: name = abs_root # Fallback ke path absolut jika nama kosong (misal, root '/')
             drive_items.append({
                 "name": name,
                 "type": "drive", # Tandai sebagai 'drive' atau root folder # English Hardcode
                 "path": abs_root.replace(os.sep, "/") # Gunakan '/' sebagai separator universal
             })
         unique_drive_items = {item['path']: item for item in drive_items}.values()
         return sorted(list(unique_drive_items), key=lambda x: x['name']) # Urutkan berdasarkan nama
    target_path = os.path.abspath(req_path)
    target_path = os.path.normpath(target_path) # Normalisasi path (hapus .., //, dsb)
    is_safe = False
    for root in safe_roots:
        norm_root = os.path.normpath(root)
        if target_path == norm_root or target_path.startswith(norm_root + os.sep):
            is_safe = True
            break
    if not is_safe:
        kernel.write_to_log(f"Forbidden path access attempt via WebSocket: {target_path}", "CRITICAL", source="LocalServerFS") # English Hardcode
        raise PermissionError("Access to the requested path is forbidden.") # English Hardcode
    if not os.path.isdir(target_path):
        raise FileNotFoundError(f"Path is not a valid directory: {target_path}") # English Hardcode
    kernel.write_to_log(f"Listing directory content for: {target_path}", "DEBUG", source="LocalServerFS") # English Hardcode
    items = []
    try:
        for item_name in sorted(os.listdir(target_path), key=lambda s: s.lower()):
            item_path = os.path.join(target_path, item_name)
            try:
                is_dir = os.path.isdir(item_path)
                items.append({
                    "name": item_name,
                    "type": "directory" if is_dir else "file", # English Hardcode
                    "path": os.path.abspath(item_path).replace(os.sep, "/") # Gunakan '/'
                })
            except OSError as e: # Tangani error permission saat mengakses item individual
                kernel.write_to_log(f"Permission error accessing item '{item_path}': {e}", "WARN", source="LocalServerFS") # English Hardcode
                continue # Lanjutkan ke item berikutnya
    except OSError as e: # Tangani error saat listing direktori utama (misal, permission denied)
        kernel.write_to_log(f"Error listing directory '{target_path}': {e}", "ERROR", source="LocalServerFS") # English Hardcode
        raise PermissionError(f"Cannot access directory: {e}") # English Hardcode
    return items
def _send_to_websocket_threadsafe(ws, loop, payload_dict):
    """ Safely sends a JSON payload to the websocket from another thread. """
    payload_type_for_log = payload_dict.get("type", "Unknown Type") # English Hardcode
    try:
        if 'content' in payload_dict and isinstance(payload_dict['content'], str):
            try:
                parsed_content = json.loads(payload_dict['content'])
                payload_dict['content'] = parsed_content # Ganti string dengan objek hasil parse
            except json.JSONDecodeError:
                pass # Abaikan error parsing, kirim sebagai string biasa
        json_payload = json.dumps(payload_dict, default=str) # default=str untuk handle objek non-serializable
        asyncio.run_coroutine_threadsafe(
            ws.send(json_payload), loop
        )
    except websockets.exceptions.ConnectionClosed:
        print(f"[LocalServer SEND Debug] Connection already closed. Cannot send message type: {payload_type_for_log}.") # English Hardcode
        pass
    except TypeError as te:
         print(f"[LocalServer SEND] CRITICAL JSON Serialization Error: {te}") # English Hardcode
         print(f"[LocalServer SEND] Payload Type: {payload_type_for_log}") # English Hardcode
         print(traceback.format_exc())
    except Exception as e:
        print(f"[LocalServer SEND] CRITICAL Error sending message type {payload_type_for_log}: {e}") # English Hardcode
        print(traceback.format_exc())
async def handler(websocket, path):
    """
    Fungsi utama yang menangani setiap koneksi WebSocket yang masuk dari GUI.
    Sekarang memeriksa engineId dan otorisasi user.
    """
    kernel = Kernel.instance
    if not kernel:
        print("[LocalServer] CRITICAL: Kernel instance is not available.") # English Hardcode
        await websocket.close(1011, "Kernel not ready") # English Hardcode
        return
    loop = asyncio.get_running_loop()
    remote_addr_tuple = websocket.remote_address
    remote_addr_str = f"{remote_addr_tuple[0]}:{remote_addr_tuple[1]}" if remote_addr_tuple else "Unknown Address" # English Hardcode
    status_task = None # Inisialisasi variabel status_task
    connector = kernel.get_service("gateway_connector_service")
    if not connector:
        print("[LocalServer] CRITICAL: GatewayConnectorService not found. Authorization checks will fail.") # English Hardcode
        await websocket.close(1011, "Authorization service unavailable") # English Hardcode
        return
    try:
        query = urlparse(path).query
        params = parse_qs(query)
        requested_engine_id = params.get('engineId', [None])[0] # Ambil engineId
        if not requested_engine_id:
            print(f"[LocalServer] Connection rejected: Missing engineId from {remote_addr_str}") # English Hardcode
            await websocket.close(1008, "engineId query parameter required") # English Hardcode
            return
        if requested_engine_id != MY_ENGINE_ID:
            print(f"[LocalServer] Connection rejected: Incorrect engineId '{requested_engine_id}' from {remote_addr_str}. Expected '{MY_ENGINE_ID}'.") # English Hardcode
            await websocket.close(1008, "Incorrect engineId") # English Hardcode
            return
        print(f"[LocalServer] Client connected for engine {MY_ENGINE_ID} from {remote_addr_str}") # English Hardcode
    except Exception as e:
        print(f"[LocalServer] Error processing connection path '{path}' from {remote_addr_str}: {e}") # English Hardcode
        print(traceback.format_exc())
        await websocket.close(1011, "Internal server error during connection setup") # English Hardcode
        return
    executor = kernel.get_service("workflow_executor_service")
    preset_manager = kernel.get_service("preset_manager_service")
    module_manager = kernel.get_service("module_manager_service")
    plugin_manager = kernel.get_service("plugin_manager_service")
    tools_manager = kernel.get_service("tools_manager_service")
    trigger_manager = kernel.get_service("trigger_manager_service")
    ai_provider_manager = kernel.get_service("ai_provider_manager_service")
    variable_manager = kernel.get_service("variable_manager")
    settings_manager = kernel.get_service("localization_manager") # Nama service asli
    dataset_manager = kernel.get_service("dataset_manager_service")
    training_manager = kernel.get_service("ai_training_service")
    prompt_manager = kernel.get_service("prompt_manager_service")
    event_bus = kernel.get_service("event_bus")
    authed_user_id = None # Alamat publik user yang terotentikasi untuk sesi ini
    session_job_ids = set() # Set untuk menyimpan job_id yang relevan dengan sesi ini
    subscriber_id = f"ws_session_{str(uuid.uuid4())}" # ID unik untuk langganan event bus
    events_to_listen = [
        "SHOW_DEBUG_POPUP", # English Hardcode
        "WORKFLOW_JOB_STATUS_UPDATE", # English Hardcode
        "NODE_EXECUTION_METRIC", # English Hardcode
        "CONNECTION_STATUS_UPDATE", # English Hardcode
        "WORKFLOW_LOG_ENTRY", # English Hardcode
        "MANUAL_APPROVAL_REQUESTED", # English Hardcode
        "TRAINING_JOB_STATUS_UPDATE" # English Hardcode
    ]
    def create_async_install_callback(component_type, operation_type):
        """
        Factory to create a thread-safe callback for component operations.
        `operation_type` should be 'install' or 'uninstall'.
        This function is called from the main async handler.
        """
        def on_complete_from_thread(component_id, success, message):
            """
            This callback is executed by the manager's worker thread (a sync thread).
            It uses the thread-safe sender to push the result back to the GUI.
            """
            kernel.write_to_log(f"Component operation '{operation_type}' for {component_type} '{component_id}' finished. Success: {success}", "INFO", "LocalServer") # English Log
            is_installed_state = False
            if operation_type == 'install' and success: # English Hardcode
                is_installed_state = True
            elif operation_type == 'uninstall' and success: # English Hardcode
                is_installed_state = False
            elif operation_type == 'install' and not success: # English Hardcode
                is_installed_state = False # Install failed, so it's not installed
            elif operation_type == 'uninstall' and not success: # English Hardcode
                manager_to_check = None
                if component_type == 'modules': manager_to_check = module_manager
                elif component_type == 'plugins': manager_to_check = plugin_manager
                elif component_type == 'tools': manager_to_check = tools_manager
                elif component_type == 'triggers': manager_to_check = trigger_manager
                if manager_to_check and component_id in getattr(manager_to_check, f"loaded_{component_type}", {}):
                     component_path = getattr(manager_to_check, f"loaded_{component_type}", {}).get(component_id, {}).get('path')
                     if component_path:
                         install_marker_path = os.path.join(component_path, ".installed") # English Hardcode
                         is_installed_state = os.path.exists(install_marker_path)
                else:
                     is_installed_state = True # Assume still installed if we can't check
            payload_dict = {
                "type": "component_install_status", # English Hardcode
                "component_id": component_id,
                "component_type": component_type, # From closure
                "operation": operation_type, # From closure
                "success": success,
                "message": message,
                "is_installed": is_installed_state # The new state
            }
            _send_to_websocket_threadsafe(websocket, loop, payload_dict)
        return on_complete_from_thread
    def handle_bus_event(event_name, event_data):
        """
        Callback Event Bus: Filter dan teruskan event ke client WebSocket yang TEPAT.
        """
        try:
            event_user_context = event_data.get("user_context")
            event_user_id = event_user_context.get("id") if isinstance(event_user_context, dict) else None
            event_job_id = event_data.get("job_id") or event_data.get("workflow_context_id") or (event_user_context and event_user_context.get("workflow_context_id"))
            event_training_job_id = event_data.get("training_job_id")
            user_match = authed_user_id and event_user_id and event_user_id.lower() == authed_user_id.lower()
            job_match = event_job_id and event_job_id in session_job_ids
            training_job_match = event_training_job_id is not None
            is_relevant = False
            match_reason = "No match" # English Hardcode
            if not user_match:
                 if event_name == "TRAINING_JOB_STATUS_UPDATE":
                     is_relevant = True
                     match_reason = "General training job update (no user context)" # English Hardcode
                 else:
                    is_relevant = False
                    match_reason = "User ID mismatch" # English Hardcode
            else:
                job_specific_events = [
                    "SHOW_DEBUG_POPUP", "WORKFLOW_JOB_STATUS_UPDATE", "NODE_EXECUTION_METRIC", # English Hardcode
                    "WORKFLOW_LOG_ENTRY", "MANUAL_APPROVAL_REQUESTED", "CONNECTION_STATUS_UPDATE" # English Hardcode
                ]
                training_events = ["TRAINING_JOB_STATUS_UPDATE"]
                if event_name in job_specific_events:
                    if job_match:
                        is_relevant = True
                        match_reason = f"User ID and Job ID ({event_job_id}) matched" # English Hardcode
                    else:
                        is_relevant = False
                        match_reason = f"User ID matched but Job ID ({event_job_id}) not tracked by this session" # English Hardcode
                elif event_name in training_events:
                    is_relevant = True # Send all training updates to this user
                    match_reason = f"User ID matched (training event '{event_name}')" # English Hardcode
                else:
                    is_relevant = True
                    match_reason = f"User ID matched (general event '{event_name}')" # English Hardcode
            if not is_relevant:
                return # Jangan teruskan event ini
            payload_to_gui = event_data.copy() # Salin data asli
            payload_type_gui = None # Tipe event untuk GUI
            if event_name == "SHOW_DEBUG_POPUP":
                payload_type_gui = "SHOW_DEBUG_POPUP" # English Hardcode
            elif event_name == "WORKFLOW_JOB_STATUS_UPDATE":
                payload_type_gui = "workflow_status_update" # English Hardcode
            elif event_name == "NODE_EXECUTION_METRIC":
                payload_type_gui = "NODE_EXECUTION_METRIC" # English Hardcode
            elif event_name == "CONNECTION_STATUS_UPDATE":
                payload_type_gui = "CONNECTION_STATUS_UPDATE" # English Hardcode
            elif event_name == "WORKFLOW_LOG_ENTRY":
                payload_type_gui = "log" # English Hardcode
            elif event_name == "MANUAL_APPROVAL_REQUESTED":
                 payload_type_gui = "MANUAL_APPROVAL_REQUESTED" # English Hardcode
            elif event_name == "TRAINING_JOB_STATUS_UPDATE":
                 payload_type_gui = "training_job_status_update" # English Hardcode
                 payload_to_gui["status"] = payload_to_gui.pop("job_status", {}) # Rename key for GUI
            if payload_type_gui:
                payload_to_gui["type"] = payload_type_gui # Tambahkan field 'type' untuk GUI
                _send_to_websocket_threadsafe(websocket, loop, payload_to_gui)
        except Exception as e:
            print(f"[LocalServer] CRITICAL Error in handle_bus_event: {e}") # English Hardcode
            print(traceback.format_exc())
    if event_bus:
        for event_name in events_to_listen:
            event_bus.subscribe(
                event_name,
                subscriber_id,
                lambda data, name=event_name: handle_bus_event(name, data)
            )
        print(f"[LocalServer] Session {subscriber_id} subscribed to Event Bus for {len(events_to_listen)} events.")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                auth_payload = data.get('auth')
                main_payload = data.get('payload')
                if not auth_payload or not main_payload:
                    print(f"[LocalServer] RECV Error from {remote_addr_str}: Auth or main payload missing.") # English Hardcode
                    await websocket.send(json.dumps({"error": "Auth or main payload missing"})) # English Hardcode
                    continue
                message_to_verify_str = auth_payload.get('message')
                signature_str = auth_payload.get('signature')
                address_str = auth_payload.get('address')
                if not message_to_verify_str or not signature_str or not address_str:
                    print(f"[LocalServer] RECV Error from {remote_addr_str}: Incomplete auth payload fields.") # English Hardcode
                    await websocket.send(json.dumps({"error": "Incomplete auth payload"})) # English Hardcode
                    continue
                message_to_verify = encode_defunct(text=message_to_verify_str)
                try:
                    recovered_address = w3.eth.account.recover_message(
                        message_to_verify, signature=signature_str
                    )
                except Exception as sig_err:
                    print(f"[LocalServer] Signature verification error from {remote_addr_str} (Address: {address_str[:10]}...): {sig_err}") # English Hardcode
                    await websocket.send(json.dumps({"error": "Invalid signature format"})) # English Hardcode
                    continue
                recovered_address_lower = recovered_address.lower()
                address_lower = address_str.lower()
                if recovered_address_lower != address_lower:
                    print(f"[LocalServer] Invalid signature from: {address_str}. Recovered: {recovered_address}") # English Hardcode
                    await websocket.send(json.dumps({"error": "Invalid signature"})) # English Hardcode
                    continue
                if not connector.is_user_authorized(recovered_address_lower):
                    print(f"[LocalServer AuthZ] DENIED: User {recovered_address} is NOT in the authorized list for engine {MY_ENGINE_ID}.") # English Hardcode
                    await websocket.send(json.dumps({"error": f"User not authorized for engine {MY_ENGINE_ID}."})) # English Hardcode
                    continue # Langsung ke iterasi berikutnya (abaikan pesan ini)
                current_authed_user_id = recovered_address
                if authed_user_id != current_authed_user_id:
                     authed_user_id = current_authed_user_id
                     session_job_ids = set() # Reset job ID yang dipantau sesi ini
                     print(f"[LocalServer] User {authed_user_id[:8]}... authenticated for session {subscriber_id} on engine {MY_ENGINE_ID}.") # English Hardcode
                     if status_task is None: # Hanya mulai jika belum berjalan
                         print(f"[LocalServer Status] Starting status update task for user {authed_user_id[:8]}...")
                         status_task = asyncio.create_task(send_status_updates(websocket, kernel))
                kernel.current_user = {"id": authed_user_id}
                payload_type = main_payload.get('type')
                response_payload = None # Payload respons default
                if payload_type == 'execute_workflow': # English Hardcode
                    if executor:
                        job_id = main_payload.get('job_id')
                        if job_id:
                            session_job_ids.add(job_id) # Tambahkan job ID ke daftar pantauan sesi ini
                            print(f"[LocalServer] Session {subscriber_id} (User {authed_user_id[:8]}) added job to watch list: {job_id}")
                        else:
                             print(f"[LocalServer] WARNING: execute_workflow received without job_id from {authed_user_id[:8]}. Event filtering might be affected.")
                        def ws_logger_threadsafe(message, level="INFO", source="Executor"): # English Hardcode
                            log_payload = {
                                "type": "log", # English Hardcode
                                "level": level.upper(),
                                "source": source,
                                "message": message,
                                "user_context": {"id": authed_user_id}, # Sertakan konteks user
                                "workflow_context_id": job_id # Sertakan konteks job
                            }
                            _send_to_websocket_threadsafe(websocket, loop, log_payload)
                        workflow_data_from_gui = main_payload.get('workflow_data', {})
                        global_loop_config_from_gui = workflow_data_from_gui.get("global_loop_config")
                        threading.Thread(
                            target=executor.execute_workflow,
                            args=(
                                {node["id"]: node for node in workflow_data_from_gui.get("nodes", [])},
                                {conn["id"]: conn for conn in workflow_data_from_gui.get("connections", [])},
                                main_payload.get('initial_payload', {}),
                            ),
                            kwargs={
                                'logger': ws_logger_threadsafe, # Gunakan logger WS kita
                                'status_updater': None, # Status node dikirim via event bus
                                'highlighter': None, # Highlight koneksi dikirim via event bus
                                'workflow_context_id': job_id, # ID job ini
                                'user_context': {'id': authed_user_id}, # Konteks user
                                'preset_name': main_payload.get('preset_name'), # Nama preset (jika ada)
                                'mode': main_payload.get('mode', 'EXECUTE'), # Mode eksekusi (EXECUTE/SIMULATE)
                                'global_loop_config': global_loop_config_from_gui,
                            },
                            daemon=True
                        ).start()
                        response_payload = {"status": "Workflow execution started"} # English Hardcode
                    else:
                        response_payload = {"error": "WorkflowExecutorService not available."} # English Hardcode
                elif payload_type == 'request_drives': # English Hardcode
                     try:
                         drive_items = _list_safe_directory(kernel, None) # Panggil helper tanpa path
                         response_payload = {"type": "drives_list_response", "drives": drive_items} # English Hardcode
                     except Exception as fs_e:
                         response_payload = {"type": "drives_list_response", "error": str(fs_e)} # English Hardcode
                elif payload_type == 'request_directory_list': # English Hardcode
                     path_to_list = main_payload.get('path')
                     try:
                         dir_items = _list_safe_directory(kernel, path_to_list) # Panggil helper dengan path
                         response_payload = {"type": "directory_list_response", "path": path_to_list, "items": dir_items} # English Hardcode
                     except FileNotFoundError as fnf_e:
                          response_payload = {"type": "directory_list_response", "path": path_to_list, "error": str(fnf_e)} # English Hardcode
                     except PermissionError as perm_e:
                          response_payload = {"type": "directory_list_response", "path": path_to_list, "error": str(perm_e)} # English Hardcode
                     except Exception as fs_e:
                         response_payload = {"type": "directory_list_response", "path": path_to_list, "error": f"Unexpected filesystem error: {str(fs_e)}"} # English Hardcode
                elif payload_type == 'execute_standalone_node': # English Hardcode
                    kernel.write_to_log(f"Received request for standalone node execution from {authed_user_id[:8]}...", "INFO") # English Log
                    if executor:
                        job_id = main_payload.get('job_id')
                        node_data = main_payload.get('node_data')
                        mode = main_payload.get('mode', 'EXECUTE') # English Hardcode
                        user_context = {'id': authed_user_id}
                        if not job_id or not node_data or not node_data.get('module_id'):
                            response_payload = {"error": "Invalid payload: job_id and node_data (with module_id) are required."} # English Hardcode
                        else:
                            session_job_ids.add(job_id) # Tambahkan job ID ke daftar pantauan sesi ini
                            executor.execute_standalone_node(
                                node_data=node_data,
                                job_id=job_id,
                                user_context=user_context,
                                mode=mode
                            )
                            response_payload = {"status": f"Standalone execution for {node_data.get('module_id')} started."} # English Hardcode
                    else:
                        response_payload = {"error": "WorkflowExecutorService not available."} # English Hardcode
                elif payload_type == 'stop_workflow': # English Hardcode
                    job_id_to_stop = main_payload.get('job_id')
                    if executor:
                         executor.stop_execution() # Versi saat ini stop semua
                    response_payload = {"status": "Stop signal sent"} # English Hardcode
                elif payload_type == 'pause_workflow': # English Hardcode
                    if executor: executor.pause_execution()
                    response_payload = {"status": "Pause signal sent"} # English Hardcode
                elif payload_type == 'resume_workflow': # English Hardcode
                    if executor: executor.resume_execution()
                    response_payload = {"status": "Resume signal sent"} # English Hardcode
                elif payload_type == 'install_component': # English Hardcode
                    comp_type = main_payload.get('component_type')
                    comp_id = main_payload.get('component_id')
                    manager = None
                    if comp_type == 'modules': manager = module_manager
                    elif comp_type == 'plugins': manager = plugin_manager
                    elif comp_type == 'tools': manager = tools_manager
                    elif comp_type == 'triggers': manager = trigger_manager
                    if manager and comp_id:
                        kernel.write_to_log(f"Received request to INSTALL {comp_type} '{comp_id}'", "WARN", "LocalServer") # English Log
                        response_payload = {"type": "status_response", "status": f"Install command received for {comp_id}."} # English Hardcode
                        install_callback = create_async_install_callback(comp_type, 'install') # English Hardcode
                        manager.install_component_dependencies(comp_id, on_complete=install_callback)
                    else:
                        response_payload = {"type": "status_response", "error": "Invalid component type or ID for install."} # English Hardcode
                elif payload_type == 'uninstall_component': # English Hardcode
                    comp_type = main_payload.get('component_type')
                    comp_id = main_payload.get('component_id')
                    manager = None
                    if comp_type == 'modules': manager = module_manager
                    elif comp_type == 'plugins': manager = plugin_manager
                    elif comp_type == 'tools': manager = tools_manager
                    elif comp_type == 'triggers': manager = trigger_manager
                    if manager and comp_id:
                        kernel.write_to_log(f"Received request to UNINSTALL {comp_type} '{comp_id}'", "WARN", "LocalServer") # English Log
                        response_payload = {"type": "status_response", "status": f"Uninstall command received for {comp_id}."} # English Hardcode
                        uninstall_callback = create_async_install_callback(comp_type, 'uninstall') # English Hardcode
                        manager.uninstall_component_dependencies(comp_id, on_complete=uninstall_callback)
                    else:
                        response_payload = {"type": "status_response", "error": "Invalid component type or ID for uninstall."} # English Hardcode
                elif payload_type == 'request_components_list': # English Hardcode
                    comp_type = main_payload.get('component_type')
                    manager = None
                    if comp_type == 'modules': manager = module_manager
                    elif comp_type == 'plugins': manager = plugin_manager
                    elif comp_type == 'tools': manager = tools_manager
                    elif comp_type == 'triggers': manager = trigger_manager
                    elif comp_type == 'ai_providers': manager = kernel.get_service("ai_provider_manager_service")
                    components = []
                    if manager:
                        items_attr_name = None
                        if comp_type == 'modules': items_attr_name = 'loaded_modules'
                        elif comp_type == 'plugins': items_attr_name = 'loaded_plugins'
                        elif comp_type == 'tools': items_attr_name = 'loaded_tools'
                        elif comp_type == 'triggers': items_attr_name = 'loaded_triggers'
                        elif comp_type == 'ai_providers': items_attr_name = 'loaded_providers'
                        if items_attr_name:
                            loaded_items = getattr(manager, items_attr_name, {})
                            for item_id, item_data in loaded_items.items():
                                if isinstance(item_data, dict) and not item_data.get('is_paused', False):
                                    manifest_data = {}
                                    if comp_type == 'ai_providers':
                                        instance = item_data
                                        if hasattr(instance, 'get_manifest'):
                                            manifest_data = instance.get_manifest()
                                    else:
                                        manifest_data = item_data.get("manifest", {})
                                    components.append({
                                        "id": item_id,
                                        "name": manifest_data.get("name", item_id),
                                        "manifest": manifest_data,
                                        "is_installed": item_data.get("is_installed", False) # Sertakan status instalasi
                                    })
                        else:
                             print(f"[LocalServer] Error: Attribute name not mapped for component type '{comp_type}'")
                    response_payload = {
                        "type": "components_list_response", # English Hardcode
                        "component_type": comp_type,
                        "components": sorted(components, key=lambda x: x['name'])
                    }
                elif payload_type == 'request_presets_list': # English Hardcode
                    presets = []
                    if preset_manager:
                        presets = preset_manager.get_preset_list(user_id=authed_user_id)
                    response_payload = {
                        "type": "presets_list_response", # English Hardcode
                        "presets": presets,
                    }
                elif payload_type == 'load_preset': # English Hardcode
                    preset_name = main_payload.get('name')
                    owner_id = main_payload.get('owner_id')
                    user_id_to_load = owner_id if owner_id else authed_user_id
                    print(f"[LocalServer] Load preset request for '{preset_name}'. Requester: {authed_user_id[:8]}... Owner: {user_id_to_load[:8]}...")
                    workflow_data = None
                    if preset_manager:
                        workflow_data = preset_manager.get_preset_data(preset_name, user_id=user_id_to_load)
                    if workflow_data is None:
                         print(f"[LocalServer] Preset '{preset_name}' not found for user {user_id_to_load[:8]}")
                    response_payload = {
                        "type": "load_preset_response", # English Hardcode
                        "name": preset_name,
                        "workflow_data": workflow_data # Akan jadi null jika tidak ditemukan
                    }
                elif payload_type == 'save_preset': # English Hardcode
                    preset_name = main_payload.get('name')
                    workflow_data = main_payload.get('workflow_data')
                    signature = main_payload.get('signature') # Ambil tanda tangan dari GUI
                    if preset_manager:
                        success = preset_manager.save_preset(
                            preset_name,
                            workflow_data,
                            user_id=authed_user_id,
                            signature=signature
                        )
                        if success:
                            response_payload = {"status": f"Preset '{preset_name}' saved successfully."} # English Hardcode
                            presets = preset_manager.get_preset_list(user_id=authed_user_id)
                            await websocket.send(json.dumps({"type": "presets_list_response", "presets": presets}, default=str)) # English Hardcode # Kirim balik hanya presets
                        else:
                             response_payload = {"error": f"Failed to save preset '{preset_name}'. Check logs for details (e.g., signature mismatch)."} # English Hardcode
                    else:
                         response_payload = {"error": "PresetManagerService not available."} # English Hardcode
                elif payload_type == 'delete_preset': # English Hardcode
                    preset_name = main_payload.get('name')
                    if preset_manager:
                        success = preset_manager.delete_preset(preset_name, user_id=authed_user_id)
                        if success:
                            response_payload = {"status": f"Preset '{preset_name}' deleted."} # English Hardcode
                            presets = preset_manager.get_preset_list(user_id=authed_user_id)
                            await websocket.send(json.dumps({"type": "presets_list_response", "presets": presets}, default=str)) # English Hardcode # Kirim balik hanya presets
                        else:
                             response_payload = {"error": f"Failed to delete preset '{preset_name}' (maybe not found or permission issue)."} # English Hardcode
                    else:
                        response_payload = {"error": "PresetManagerService not available."} # English Hardcode
                elif payload_type == 'request_settings': # English Hardcode
                    settings = {}
                    if settings_manager:
                        settings = settings_manager.get_all_settings(user_id=authed_user_id)
                    response_payload = {"type": "settings_response", "settings": settings} # English Hardcode
                elif payload_type == 'save_settings': # English Hardcode
                    if settings_manager:
                        settings_manager._save_settings(main_payload.get('settings', {}), user_id=authed_user_id)
                        response_payload = {"status": "Settings saved successfully."} # English Hardcode
                    else:
                        response_payload = {"error": "Settings manager not available."} # English Hardcode
                elif payload_type == 'request_variables': # English Hardcode
                    variables = []
                    if variable_manager:
                        variables = variable_manager.get_all_variables_for_api(user_id=authed_user_id)
                    response_payload = {"type": "variables_response", "variables": variables} # English Hardcode
                elif payload_type == 'request_prompts_list': # English Hardcode
                    prompts = []
                    if prompt_manager:
                        prompts = prompt_manager.get_all_prompts() # Panggil service
                    response_payload = {"type": "prompts_list_response", "prompts": prompts} # English Hardcode
                elif payload_type == 'update_variable': # English Hardcode
                    var_name = main_payload.get('name')
                    var_data = main_payload.get('data')
                    if variable_manager and var_name and var_data:
                        try:
                             variable_manager.set_variable(
                                 var_name,
                                 var_data.get('value'),
                                 var_data.get('is_secret', False),
                                 var_data.get('is_enabled', True),
                                 mode=var_data.get('mode', 'single'),
                                 user_id=authed_user_id
                             )
                             response_payload = {"status": f"Variable '{var_name}' updated successfully."} # English Hardcode
                             variables = variable_manager.get_all_variables_for_api(user_id=authed_user_id)
                             await websocket.send(json.dumps({"type": "variables_response", "variables": variables}, default=str)) # English Hardcode
                        except ValueError as ve:
                             response_payload = {"error": str(ve)}
                    else:
                        response_payload = {"error": "Variable manager not available or invalid payload."} # English Hardcode
                elif payload_type == 'delete_variable': # English Hardcode
                    var_name = main_payload.get('name')
                    if variable_manager and var_name:
                        success = variable_manager.delete_variable(var_name, user_id=authed_user_id)
                        if success:
                            response_payload = {"status": f"Variable '{var_name}' deleted."} # English Hardcode
                            variables = variable_manager.get_all_variables_for_api(user_id=authed_user_id)
                            await websocket.send(json.dumps({"type": "variables_response", "variables": variables}, default=str)) # English Hardcode
                        else:
                            response_payload = {"error": f"Variable '{var_name}' not found."} # English Hardcode
                    else:
                         response_payload = {"error": "Variable manager not available or variable name missing."} # English Hardcode
                elif payload_type == 'request_connection_history': # English Hardcode
                    if executor:
                         job_id_hist = main_payload.get('job_id')
                         conn_id_hist = main_payload.get('connection_id')
                         history_data = executor.get_connection_history(job_id_hist, conn_id_hist)
                         response_payload = {
                             "type": "connection_history_response", # English Hardcode
                             "job_id": job_id_hist,
                             "connection_id": conn_id_hist,
                             "history": history_data
                         }
                    else:
                         response_payload = {"error": "Executor service not available."} # English Hardcode
                elif payload_type == 'request_ai_status': # English Hardcode
                    if ai_provider_manager:
                        providers = ai_provider_manager.get_available_providers()
                        response_payload = {"type": "ai_status_response", "providers": providers} # English Hardcode
                    else:
                        response_payload = {"type": "ai_status_response", "error": "AIProviderManagerService not available."} # English Hardcode
                elif payload_type == 'request_ai_playground': # English Hardcode
                    if ai_provider_manager:
                        prompt = main_payload.get('prompt')
                        endpoint_id = main_payload.get('endpoint_id')
                        result = ai_provider_manager.query_ai_by_task('text', prompt, endpoint_id=endpoint_id) # English Hardcode
                        response_payload = {"type": "ai_playground_response", "result": result} # English Hardcode
                    else:
                        response_payload = {"type": "ai_playground_response", "result": {"error": "AIProviderManagerService not available."}} # English Hardcode
                elif payload_type == 'request_datasets_list': # English Hardcode
                    datasets = []
                    if dataset_manager:
                        datasets = dataset_manager.list_datasets() # user_id handled by manager
                    response_payload = {"type": "datasets_list_response", "datasets": datasets} # English Hardcode
                elif payload_type == 'load_dataset_data': # English Hardcode
                    name = main_payload.get('name')
                    data = []
                    if dataset_manager and name:
                        data = dataset_manager.get_dataset_data(name) # user_id handled by manager
                    response_payload = {"type": "dataset_data_response", "name": name, "data": data} # English Hardcode
                elif payload_type == 'create_dataset': # English Hardcode
                    name = main_payload.get('name')
                    if dataset_manager and name:
                        dataset_manager.create_dataset(name) # user_id handled by manager
                        datasets = dataset_manager.list_datasets() # Fetch list baru
                        response_payload = {"type": "datasets_list_response", "datasets": datasets} # English Hardcode
                    else:
                        response_payload = {"type": "datasets_list_response", "error": "Invalid name or dataset manager unavailable."} # English Hardcode
                elif payload_type == 'delete_dataset': # English Hardcode
                    name = main_payload.get('name')
                    if dataset_manager and name:
                        dataset_manager.delete_dataset(name) # user_id handled by manager
                        datasets = dataset_manager.list_datasets() # Fetch list baru
                        response_payload = {"type": "datasets_list_response", "datasets": datasets} # English Hardcode
                    else:
                        response_payload = {"type": "datasets_list_response", "error": "Invalid name or dataset manager unavailable."} # English Hardcode
                elif payload_type == 'add_dataset_data': # English Hardcode
                    name = main_payload.get('name')
                    data_rows = main_payload.get('data')
                    if dataset_manager and name and data_rows:
                        dataset_manager.add_data_to_dataset(name, data_rows) # user_id handled by manager
                        updated_data = dataset_manager.get_dataset_data(name)
                        await websocket.send(json.dumps({"type": "dataset_data_response", "name": name, "data": updated_data}, default=str)) # English Hardcode
                        datasets = dataset_manager.list_datasets()
                        response_payload = {"type": "datasets_list_response", "datasets": datasets} # English Hardcode
                    else:
                        response_payload = {"type": "dataset_data_response", "error": "Invalid payload or dataset manager unavailable."} # English Hardcode
                elif payload_type == 'update_dataset_row': # English Hardcode
                    name = main_payload.get('name')
                    row_data = main_payload.get('row_data')
                    if dataset_manager and name and row_data:
                        dataset_manager.update_dataset_row(name, row_data) # user_id handled by manager
                        updated_data = dataset_manager.get_dataset_data(name)
                        response_payload = {"type": "dataset_data_response", "name": name, "data": updated_data} # English Hardcode
                    else:
                        response_payload = {"type": "dataset_data_response", "error": "Invalid payload or dataset manager unavailable."} # English Hardcode
                elif payload_type == 'delete_dataset_row': # English Hardcode
                    name = main_payload.get('name')
                    row_id = main_payload.get('row_id')
                    if dataset_manager and name and row_id:
                        dataset_manager.delete_dataset_row(name, row_id) # user_id handled by manager
                        updated_data = dataset_manager.get_dataset_data(name)
                        response_payload = {"type": "dataset_data_response", "name": name, "data": updated_data} # English Hardcode
                    else:
                        response_payload = {"type": "dataset_data_response", "error": "Invalid payload or dataset manager unavailable."} # English Hardcode
                elif payload_type == 'request_local_models': # English Hardcode
                    models = []
                    if ai_provider_manager:
                        all_models = getattr(ai_provider_manager, 'local_models', {})
                        for model_id, model_data in all_models.items():
                            if model_data.get("category") == "text": # English Hardcode
                                models.append({"id": model_data.get("name"), "name": model_data.get("name")})
                    response_payload = {"type": "local_models_response", "models": sorted(models, key=lambda x: x['name'])} # English Hardcode
                elif payload_type == 'start_training_job': # English Hardcode
                    config = main_payload.get('config')
                    if training_manager and config:
                        try:
                            job_status = training_manager.start_fine_tuning_job(
                                base_model_id=config["base_model_id"],
                                dataset_name=config["dataset_name"],
                                new_model_name=config["new_model_name"],
                                training_args=config["training_args"]
                            )
                            response_payload = {"type": "training_job_status_response", "status": [job_status]} # English Hardcode
                        except Exception as train_e:
                            response_payload = {"type": "training_job_status_response", "error": str(train_e)} # English Hardcode
                    else:
                        response_payload = {"type": "training_job_status_response", "error": "Invalid config or Training manager unavailable."} # English Hardcode
                elif payload_type == 'request_training_job_status': # English Hardcode
                    job_id = main_payload.get('job_id')
                    status_data = []
                    if training_manager:
                        if job_id:
                            job_status = training_manager.get_job_status(job_id)
                            if job_status: status_data = [job_status]
                        else:
                            all_jobs = getattr(training_manager, 'training_jobs', {})
                            status_data = list(all_jobs.values())
                    response_payload = {"type": "training_job_status_response", "status": status_data} # English Hardcode
                else:
                    response_payload = {"status": f"Command '{payload_type}' received but not handled.", "type": "status_response"} # English Hardcode
                if response_payload:
                    await websocket.send(json.dumps(response_payload, default=str))
            except json.JSONDecodeError:
                print(f"[LocalServer] RECV Error from {remote_addr_str}: Invalid JSON format received.") # English Hardcode
                await websocket.send(json.dumps({"error": "Invalid JSON format"})) # English Hardcode
            except websockets.exceptions.ConnectionClosed:
                print(f"[LocalServer] Connection closed during message processing from {remote_addr_str}") # English Hardcode
                break
            except Exception as e:
                print(f"[LocalServer] CRITICAL Handler Error processing message from {remote_addr_str}: {str(e)}") # English Hardcode
                print(traceback.format_exc())
                try:
                    await websocket.send(json.dumps({"error": f"An unexpected server error occurred: {str(e)}"})) # English Hardcode
                except websockets.exceptions.ConnectionClosed:
                     print(f"[LocalServer] Connection closed before sending error report from {remote_addr_str}") # English Hardcode
    except websockets.exceptions.ConnectionClosedOK:
        print(f"[LocalServer] Connection closed normally from: {remote_addr_str} (Session: {subscriber_id})") # English Hardcode
    except websockets.exceptions.ConnectionClosedError as e:
         print(f"[LocalServer] Connection closed with error from {remote_addr_str} (Session: {subscriber_id}): {e}") # English Hardcode
    except Exception as e:
         print(f"[LocalServer] UNEXPECTED Error in handler loop for {remote_addr_str} (Session: {subscriber_id}): {e}") # English Hardcode
         print(traceback.format_exc())
    finally:
        if status_task:
            status_task.cancel()
            print(f"[LocalServer Status] Status update task cancelled for session {subscriber_id}.")
        if event_bus:
            for event_name in events_to_listen:
                event_bus.unsubscribe(event_name, subscriber_id)
            print(f"[LocalServer] Session {subscriber_id} unsubscribed from Event Bus.")
        user_display = f"{authed_user_id[:8]}..." if authed_user_id else 'Unknown' # English Hardcode
        print(f"[LocalServer] Client {user_display} disconnected from engine {MY_ENGINE_ID} (Session: {subscriber_id}).") # English Hardcode
async def main():
    """
    Fungsi utama untuk menjalankan server WebSocket.
    """
    while Kernel.instance is None:
        print("[LocalServer] Waiting for Kernel instance...") # English Hardcode
        await asyncio.sleep(1)
    kernel = Kernel.instance
    connector = kernel.get_service("gateway_connector_service")
    if not connector:
        print("[LocalServer] FATAL: GatewayConnectorService not found. Cannot start.") # English Hardcode
        sys.exit(1)
    print("[LocalServer] Waiting for initial authorization list from Gateway...") # English Hardcode
    while not connector.is_auth_list_fetched:
        await asyncio.sleep(0.5)
    if not connector.authorized_addresses:
        print("[LocalServer] FATAL: Authorization list is empty after fetching from Gateway.") # English Hardcode
        print("[LocalServer] This is a critical security step. Shutting down server.") # English Hardcode
        print("[LocalServer] Please ensure the Gateway is running, the engine token in .env is correct,") # English Hardcode
        print("[LocalServer] and the FLOWORK_ENGINE_ID in .env matches the ID from the GUI.") # English Hardcode
        sys.exit(1)
    print("[LocalServer] Initial authorization list successfully loaded.") # English Hardcode
    try:
        event_bus = kernel.get_service("event_bus")
        if not event_bus:
             print("[LocalServer] FATAL: EventBus service not found. Cannot start WebSocket server.") # English Hardcode
             sys.exit(1)
    except Exception as e:
        print(f"[LocalServer] FATAL: Error getting EventBus service: {e}") # English Hardcode
        sys.exit(1)
    host = "0.0.0.0"
    port = 12345
    print(f"[LocalServer] Attempting to start secure WebSocket server at ws://{host}:{port} for Engine ID {MY_ENGINE_ID}...") # English Hardcode
    try:
        async with websockets.serve(handler, host, port, ping_interval=20, ping_timeout=20):
            print(f"[LocalServer] Secure WebSocket server started successfully at ws://{host}:{port}") # English Hardcode
            await asyncio.Future() # Keep running indefinitely
    except OSError as e:
        if "address already in use" in str(e).lower(): # English Hardcode
            print(f"[LocalServer] FATAL: Port {port} is already in use. Another instance might be running or the port is blocked.") # English Hardcode
        else:
            print(f"[LocalServer] FATAL: Failed to start WebSocket server due to OS error: {e}") # English Hardcode
        sys.exit(1)
    except Exception as e:
         print(f"[LocalServer] FATAL: Unexpected error during WebSocket server startup: {e}") # English Hardcode
         print(traceback.format_exc())
         sys.exit(1)
if __name__ == "__main__":
    print("[LocalServer] Running in standalone mode for testing. Kernel might not be fully initialized.") # English Hardcode
    asyncio.run(main())
