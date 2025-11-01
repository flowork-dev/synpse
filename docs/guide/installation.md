````markdown
# Installation

Flowork uses a hybrid architecture. The GUI runs in your browser, while the **Core Engine** runs on your own hardware using Docker. This ensures your data and workflows remain private.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Docker Desktop:** This is essential for running the Flowork Core Engine and Gateway. [Download Docker Desktop](https://www.docker.com/products/docker-desktop/).
2.  **Git (Optional but Recommended):** For cloning the project repository.
3.  **A Text Editor:** (e.g., VS Code) for editing configuration files.

## 1. Get the Flowork Engine

You can get the engine by cloning the official repository:

```bash
git clone [https://github.com/flowork-dev/flowork-platform.git](https://github.com/flowork-dev/flowork-platform.git)
cd flowork-platform/C%3A/FLOWORK
````

Or by downloading the ZIP file from the [GitHub repository](https://github.com/flowork-dev/flowork-platform) and extracting it. We will refer to the extracted folder as your `C:\FLOWORK` directory.

## 2\. Configure Your Engine

The entire stack is configured using a single `.env` file located in the `C:\FLOWORK` directory.

When you first get the code, the `.env` file will have placeholder values:

```env
# C:\FLOWORK\.env (Example)

JWT_SECRET_KEY=...
FLOWORK_MASTER_PRIVATE_KEY="..."
GATEWAY_SECRET_TOKEN=...
CLOUDFLARED_TOKEN=...

# --- THESE MUST BE REPLACED ---
FLOWORK_ENGINE_ID=PLEASE_REPLACE_ME_WITH_ID_FROM_GUI
FLOWORK_ENGINE_TOKEN=PLEASE_REPLACE_ME_WITH_TOKEN_FROM_GUI
```

**You do not need to edit this file manually.** The easiest way to generate a unique, secure configuration is by running the force rebuild script.

### Run the Force Rebuild Script

This script automatically generates a new **Engine ID** and **Engine Token** and writes them to your `.env` file.

1.  Navigate to your `C:\FLOWORK` directory.
2.  Double-click `0-FORCE_REBUILD.bat`.
3.  A console window will appear, generate new keys, and build your Docker images.

This script does the following:

  * Generates a new unique `FLOWORK_ENGINE_ID`.
  * Generates a new secure `FLOWORK_ENGINE_TOKEN`.
  * Saves these new values into `C:\FLOWORK\.env`.
  * Saves the token into `C:\FLOWORK\flowork-core-data\docker-engine.conf`.
  * Stops and removes any old containers/volumes.
  * Builds fresh Docker images.
  * Starts all services (`gateway`, `core`, `cloudflared`).

## 3\. Run the Engine

After the `0-FORCE_REBUILD.bat` script is finished, your engine is running.

For future use, you can start your engine without rebuilding everything by using:

  * **`3-RUN_DOCKER.bat`**: Starts all services.
  * **`2-STOP_DOCKER_(SAFE).bat`**: Stops services without deleting your data (presets, variables).

<!-- end list -->

```
```