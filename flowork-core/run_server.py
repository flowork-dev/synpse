#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\run_server.py JUMLAH BARIS 92 
#######################################################################

import sys
import os
import time
import importlib.util
from dotenv import load_dotenv
import asyncio
import subprocess
import local_server
import traceback
def display_banner():
    """Displays the official startup banner for the FLOWORK Core Server."""
    print("=" * 70)
    print(
        r"""
 _____ _     ____  _      ____  ____  _  __
/    // \   /  _ \/ \  /|/  _ \/  __\/ |/ /
|  __\| |   | / \|| |  ||| / \||  \/||   /
| |   | |_/\| \_/|| |/\||| \_/||    /|   \
\_/   \____/\____/\_/  \|\____/\_/\_\\_|\_\
    """
    )
    print(" CORE SERVER ENGINE BY FLOWORK")
    print("=" * 70)
def ensure_packages_exist():
    """Handles creation of dynamic package __init__.py files."""
    project_root = os.path.abspath(os.path.dirname(__file__))
    packages_to_check = ["generated_services"]
    for package in packages_to_check:
        package_path = os.path.join(project_root, package)
        init_file = os.path.join(package_path, "__init__.py")
        os.makedirs(package_path, exist_ok=True)
        if not os.path.exists(init_file):
            try:
                with open(init_file, "w") as f:
                    pass
                print(
                    f"[INFO] Created missing package file: {os.path.relpath(init_file)}"
                )
            except Exception as e:
                print(f"[WARN] Could not create __init__.py for {package}: {e}")
async def main_async():
    """
    (REMASTERED - FASE 1) Main entry point untuk standalone FLOWORK Core Server.
    Sekarang juga menjalankan Secure WebSocket Server.
    """
    load_dotenv()
    display_banner()
    core_path = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(core_path)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if core_path not in sys.path:
        sys.path.insert(0, core_path)
    print("[INFO] Starting FLOWORK Core Server...")
    ensure_packages_exist()
    from flowork_kernel.kernel import Kernel
    from dashboard_server import run_dashboard_server
    project_root_path = os.path.abspath(os.path.dirname(__file__))
    kernel = Kernel(project_root_path)
    dashboard_port = int(os.getenv("DASHBOARD_PORT", 5001))
    run_dashboard_server(kernel, port=dashboard_port)
    startup_task = asyncio.create_task(kernel.start_all_services())
    local_ws_server_task = asyncio.create_task(local_server.main())
    await startup_task
    print(f"--- FLOWORK Core Server is running ---")
    print(f"--- FLOWORK Local Secure Server is running on ws://localhost:12345 ---")
    print("--- Waiting for jobs from the GUI... Press Ctrl+C to stop. ---")
    await asyncio.gather(
        local_ws_server_task,
        asyncio.Event().wait() # Ini akan jalan terus sampai dihentikan
    )
def main():
    try:
        asyncio.run(main_async())
    except ImportError as e:
        print(f"[FATAL] Failed to import core logic: {e}")
    except KeyboardInterrupt:
        print("\n[INFO] Shutdown signal received. Stopping Core Server...")
    except Exception as e:
        print(f"[FATAL] A critical error occurred: {e}")
        traceback.print_exc()
    finally:
        print("[SUCCESS] Core Server stopped gracefully.")
if __name__ == "__main__":
    main()
