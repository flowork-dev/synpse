# API Introduction# API Introduction

Flowork operates on a hybrid, microservice architecture. This means there are distinct API surfaces for different tasks, each with its own authentication method.

Understanding which API to use is key to developing on the platform.

## 1. API Endpoints

There are three primary API/Socket endpoints you will interact with.

### A. The Gateway (REST API)

This is the main public-facing API for management and authentication.

* **Base URL:** `https://api.flowork.cloud/api/v1/`
* **Purpose:** User identity (login/profile), engine registration (CRUD), engine sharing, and billing.
* **Authentication:** [Cryptographic Signature](#gui-to-gateway-engine-auth) (for user-facing routes) or [Engine Token](#engine-to-gateway-auth) (for engine-facing routes).

### B. The Gateway (WebSocket)

This is a **Socket.IO** server used by the GUI and Engine to exchange high-level status updates.

* **GUI Namespace:** `wss://api.flowork.cloud/gui-socket`
* **Engine Namespace:** `wss://api.flowork.cloud/engine-socket`
* **Purpose:** Relays engine status (online/offline, vitals) to the GUI, forwards job requests *from* the GUI *to* the correct engine, and handles general notifications.

### C. The Core Engine (WebSocket)

This is a **direct WebSocket** connection to your self-hosted engine, exposed via Cloudflare Tunnel.

* **Base URL:** `wss://socket.flowork.cloud/` (This points to your `cloudflared` tunnel)
* **Purpose:** This is the high-performance channel for *all* real-time workflow operations:
    * Executing/Simulating workflows.
    * Requesting component/preset lists.
    * Receiving real-time execution logs.
    * Managing local variables and settings.
* **Authentication:** [Cryptographic Signature](#gui-to-core-engine-auth).

## 2. Authentication Methods

Flowork uses three distinct methods for security.

### A. GUI to Core Engine (Crypto Signature)

This is the primary method for the GUI to command your local engine. Every message sent over the Core Engine WebSocket is wrapped in a security envelope.

* **How it works:** Your browser uses your **Private Key** to sign a message. The engine verifies this signature with your **Public Address**.
* **Headers/Payload:**
    * `auth.address`: Your public address (e.g., `0x...`).
    * `auth.message`: A unique message (e.g., a timestamp).
    * `auth.signature`: The resulting signature of the message.
    * `payload`: The actual command (e.g., `{ "type": "execute_workflow", ... }`).

### B. Engine to Gateway (Engine Token)

This is how your local Core Engine authenticates itself to the Gateway.

* **How it works:** Your engine sends its unique `FLOWORK_ENGINE_TOKEN` (from your `.env` file) to the Gateway when it connects to the `/engine-socket`.
* **Header (for REST):** `X-Engine-Token: dev_engine_...`
* **Payload (for WebSocket):** `{ "token": "dev_engine_..." }`
* **Used for:**
    * Connecting to the Gateway WebSocket.
    * Fetching its authorization list (`/api/v1/engine/get-engine-auth-info`).

### C. Internal Service-to-Service (Gateway Secret)

This is for internal communication within your Docker stack (e.g., Gateway container calling the Core container's API).

* **How it works:** Both services share a secret token (`GATEWAY_SECRET_TOKEN` from `.env`).
* **Header:** `X-API-Key: flork_sec_...`
* **Used for:**
    * Gateway proxying requests to the Core (e.g., health checks).