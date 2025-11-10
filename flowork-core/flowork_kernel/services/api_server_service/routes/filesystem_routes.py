########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\filesystem_routes.py total lines 136 
########################################################################

import os
import sys
import json
from urllib.parse import urlparse, parse_qs
from .base_api_route import BaseApiRoute
from aiohttp import web  # (PENAMBAHAN KODE) Import web dari aiohttp
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
class FilesystemRoutes(BaseApiRoute):
    """
    Manages API routes for browsing the local filesystem in a secure manner.
    (UPGRADED V8 - Hybrid Discovery) Displays a combined list of auto-discovered
    paths and user-defined paths from the whitelist config.
    """
    def register_routes(self):
        return {
            "GET /api/v1/filesystem/drives": self.handle_list_drives,
            "GET /api/v1/filesystem/list": self.handle_list_directory,
        }
    def _get_safe_roots(self):
        """
        (PERBAIKAN KUNCI)
        Menggabungkan semua path yang aman: dari config, folder user, dan drive.
        Ini akan menjadi sumber untuk tampilan 'My Computer'.
        """
        roots = [os.path.abspath(self.kernel.project_root_path)]
        browseable_paths_config = os.path.join(
            self.kernel.data_path, "browseable_paths.json"
        )
        try:
            if os.path.exists(browseable_paths_config):
                with open(browseable_paths_config, "r", encoding="utf-8") as f:
                    user_defined_paths = json.load(f)
                    if isinstance(user_defined_paths, list):
                        for path in user_defined_paths:
                            if os.path.isdir(path):
                                roots.append(os.path.abspath(path))
        except Exception as e:
            self.logger(f"Could not load or parse 'browseable_paths.json': {e}", "WARN")
        user_home = os.path.expanduser("~")
        common_dirs = [
            "Desktop",
            "Documents",
            "Downloads",
            "Pictures",
            "Music",
            "Videos",
        ]
        for d in common_dirs:
            path = os.path.join(user_home, d)
            if os.path.isdir(path):
                roots.append(os.path.abspath(path))
        if PSUTIL_AVAILABLE:
            for partition in psutil.disk_partitions():
                roots.append(os.path.abspath(partition.mountpoint))
        else:  # Fallback untuk Windows jika psutil tidak ada
            if sys.platform == "win32":
                import string
                for letter in string.ascii_uppercase:
                    drive = f"{letter}:\\"
                    if os.path.isdir(drive):
                        roots.append(drive)
        return sorted(list(set(roots)))
    async def handle_list_drives(
        self, request
    ):  # (PERBAIKAN KUNCI) Diubah menjadi async
        """Endpoint ini sekarang berfungsi sebagai 'get root folders'."""
        try:
            safe_roots = self._get_safe_roots()
            drives_info = []
            for path in safe_roots:
                name = path
                user_home = os.path.expanduser("~")
                if path.startswith(user_home):
                    relative_part = os.path.relpath(path, user_home)
                    if relative_part == ".":
                        name = "User Home"
                    else:
                        name = f"My {relative_part}"
                drives_info.append({"name": name, "path": path.replace(os.sep, "/")})
            return self._json_response(drives_info)  # (PERBAIKAN KUNCI)
        except Exception as e:
            return self._json_response(
                {"error": f"Could not list drives: {str(e)}"}, status=500
            )  # (PERBAIKAN KUNCI)
    async def handle_list_directory(
        self, request
    ):  # (PERBAIKAN KUNCI) Diubah menjadi async
        safe_roots = self._get_safe_roots()
        req_path = request.query.get("path", "")  # (PERBAIKAN KUNCI)
        if not req_path:
            target_path = os.path.abspath(self.kernel.project_root_path)
        else:
            target_path = os.path.abspath(req_path)
        target_path = os.path.normpath(target_path)
        is_safe = any(
            target_path.startswith(os.path.normpath(root)) for root in safe_roots
        )
        if not is_safe:
            self.logger(f"Forbidden path access attempt: {target_path}", "CRITICAL")
            return self._json_response(
                {"error": "Access to the requested path is forbidden."},
                status=403,  # (PERBAIKAN KUNCI)
            )
        try:
            if not os.path.isdir(target_path):
                return self._json_response(
                    {"error": f"Path is not a valid directory: {target_path}"},
                    status=400,  # (PERBAIKAN KUNCI)
                )
            items = []
            for item_name in sorted(os.listdir(target_path), key=lambda s: s.lower()):
                item_path = os.path.join(target_path, item_name)
                is_dir = os.path.isdir(item_path)
                items.append(
                    {
                        "name": item_name,
                        "type": "directory" if is_dir else "file",
                        "path": os.path.abspath(item_path).replace(os.sep, "/"),
                    }
                )
            return self._json_response(items)  # (PERBAIKAN KUNCI)
        except Exception as e:
            self.logger(f"Error listing directory '{target_path}': {str(e)}", "ERROR")
            return self._json_response(
                {"error": str(e)}, status=500
            )  # (PERBAIKAN KUNCI)
