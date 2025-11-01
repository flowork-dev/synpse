````markdown
# Core Engine WebSocket API

The Core Engine WebSocket is the primary communication channel between the Flowork GUI (running in your browser) and your local Core Engine (running in Docker). It handles all real-time operations, such as executing workflows, managing presets, and browsing files.

This API is exposed via the Cloudflare Tunnel and is defined in `flowork-core/local_server.py`.

## Connection

The GUI connects to the WebSocket URL defined in its environment variables (`VITE_LOCAL_ENGINE_WS_URL`), which typically points to the Cloudflare Tunnel endpoint.

### Query Parameter

A connection **must** include the target Engine's ID as a query parameter.

* **URL Format:** `wss://socket.flowork.cloud?engineId=YOUR_ENGINE_ID`

If the `engineId` is missing or does not match the `FLOWORK_ENGINE_ID` of the running engine, the connection will be rejected.

## Authentication & Message Format

This API **does not use JWT**. Every message sent from the client (GUI) to the server (Engine) must be wrapped in a specific JSON structure containing a cryptographic signature.

This proves that the user initiating the action is the owner of the Private Key associated with their account.

### Wrapper Structure

```json
{
  "auth": {
    "address": "0xYourPublicAddress",
    "message": "A signed message string",
    "signature": "0xYourSignature"
  },
  "payload": {
    "type": "message_type_here",
    "job_id": "optional_job_id_uuid",
    "...": "other_payload_data"
  }
}
````

  * `auth`: An object containing the user's public address, the message they signed, and the resulting signature. The server (Engine) verifies this signature before processing the payload.
  * `payload`: The actual command and data being sent to the engine.

-----

## Client to Server Events (GUI → Engine)

These are the `type` values the GUI sends in the `payload` object.

| Event (`type`) | Payload Data | Description |
| :--- | :--- | :--- |
| **`execute_workflow`** | `job_id`, `workflow_data`, `initial_payload`, `preset_name`, `mode` | Triggers a workflow execution (`EXECUTE` or `SIMULATE`). |
| **`request_drives`** | *(none)* | Asks the engine for a list of browsable root drives/folders. |
| **`request_directory_list`** | `path` | Asks the engine for the contents of a specific directory path. |
| **`stop_workflow`** | `job_id` | (Deprecated) Sends a signal to stop the currently running workflow. |
| **`pause_workflow`** | *(none)* | Sends a signal to pause the currently running workflow. |
| **`resume_workflow`** | *(none)* | Sends a signal to resume a paused workflow. |
| **`request_components_list`** | `component_type` ('modules', 'plugins', etc.) | Requests the list of all available components of a specific type. |
| **`request_presets_list`** | *(none)* | Requests the list of all presets saved by the authenticated user. |
| **`load_preset`** | `name`, `owner_id` (optional) | Requests the JSON data for a specific preset. `owner_id` is used to load shared presets. |
| **`save_preset`** | `name`, `workflow_data`, `signature` | Saves the current workflow. `signature` is a hash of the `workflow_data` signed by the user. |
| **`delete_preset`** | `name` | Deletes a preset owned by the user. |
| **`request_settings`** | *(none)* | Fetches the user-specific settings (`settings.json`) from the engine. |
| **`save_settings`** | `settings` (object) | Saves the modified user settings object back to the engine. |
| **`request_variables`** | *(none)* | Fetches the user's secret/global variables from the engine. |
| **`update_variable`** | `name`, `data` (object) | Creates or updates a variable. |
| **`delete_variable`** | `name` | Deletes a variable. |
| **`request_connection_history`** | `job_id`, `connection_id` | Fetches the data payload that passed through a specific connection during a past job. |

-----

## Server to Client Events (Engine → GUI)

These are the `type` values the Engine sends back to the GUI.

| Event (`type`) | Payload Data | Description |
| :--- | :--- | :--- |
| **`engine_status_update`** | `engineId`, `isBusy`, `cpuPercent`, `memoryPercent` | Periodically sent by the engine to show its current resource load. |
| **`drives_list_response`** | `drives` (array) or `error` | Response to `request_drives`. |
| **`directory_list_response`** | `path`, `items` (array) or `error` | Response to `request_directory_list`. |
| **`components_list_response`** | `component_type`, `components` (array) | Response to `request_components_list`. |
| **`presets_list_response`** | `presets` (array) | Response to `request_presets_list`. |
| **`load_preset_response`** | `name`, `workflow_data` (object) | Response to `load_preset`, contains the workflow JSON. |
| **`settings_response`** | `settings` (object) | Response to `request_settings`. |
| **`variables_response`** | `variables` (array) | Response to `request_variables`. |
| **`connection_history_response`**| `job_id`, `connection_id`, `history` (array) | Response to `request_connection_history`. |
| **`log`** | `level`, `source`, `message`, `timestamp` | A log entry generated during workflow execution. |
| **`workflow_status_update`** | `job_id`, `status_data` (object) | Sent when the overall job status changes (e.g., `RUNNING`, `SUCCEEDED`, `FAILED`). |
| **`NODE_EXECUTION_METRIC`** | `node_id`, `status`, `timestamp`, etc. | Sent when a specific node starts (`RUNNING`) or finishes (`SUCCESS`, `ERROR`). |
| **`CONNECTION_STATUS_UPDATE`** | `connection_id`, `status` ('ACTIVE') | Sent when data flows through a connection, used for animation. |
| **`SHOW_DEBUG_POPUP`** | `title`, `content` (object/string) | Sent by a `Debug Popup` node to show data in the GUI. |
| **`MANUAL_APPROVAL_REQUESTED`**| `module_id`, `message` | Sent by a `Manual Approval` node to request user input. |

```
```