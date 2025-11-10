########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\component_routes.py total lines 266 
########################################################################

from .base_api_route import BaseApiRoute
import os
import json
import mimetypes
from aiohttp import web
class ComponentRoutes(BaseApiRoute):
    """
    (REMASTERED FOR ASYNC) Manages all component-related API routes using a single,
    unified handler that detects the component type from the request path.
    """
    def register_routes(self):
        base_routes = [
            "GET /api/v1/{resource_type}",
            "GET /api/v1/{resource_type}/{item_id}",
            "POST /api/v1/{resource_type}/install",
            "PATCH /api/v1/{resource_type}/{item_id}/state",
            "DELETE /api/v1/{resource_type}/{item_id}",
        ]
        routes = {}
        component_types = [
            "modules",
            "plugins",
            "tools",
            "widgets",
            "triggers",
            "ai_providers",
        ]
        for route_pattern in base_routes:
            for comp_type in component_types:
                concrete_route = route_pattern.replace("{resource_type}", comp_type)
                method, pattern = concrete_route.split(" ", 1)
                if "install" in pattern:
                    routes[concrete_route] = self.handle_install_components
                elif "state" in pattern:
                    routes[concrete_route] = self.handle_patch_component_state
                elif method == "DELETE":
                    routes[concrete_route] = self.handle_delete_components
                else:  # GET list or detail
                    routes[concrete_route] = self.handle_get_components
        routes["GET /api/v1/ai_providers/services"] = (
            self.handle_get_ai_provider_services
        )
        routes["GET /api/v1/components/{comp_type}/{item_id}/icon"] = (
            self.handle_get_component_icon
        )
        return routes
    async def _serve_image_file(self, request, image_path):
        try:
            import aiofiles
            async with aiofiles.open(image_path, "rb") as f:
                image_data = await f.read()
            content_type, _ = mimetypes.guess_type(image_path)
            if not content_type:
                content_type = "application/octet-stream"
            return web.Response(body=image_data, content_type=content_type)
        except Exception as e:
            self.logger(
                f"Error serving icon file '{os.path.basename(image_path)}': {e}",
                "ERROR",
            )
            return self._json_response(
                {"error": "Internal Server Error while serving icon."}, status=500
            )
    async def handle_get_component_icon(self, request):
        comp_type = request.match_info.get("comp_type")
        item_id = request.match_info.get("item_id")
        manager, error = self._get_manager_for_type(comp_type.rstrip("s") + "s")

        true_root_path = os.path.abspath(os.path.join(self.kernel.project_root_path, ".."))


        assets_path = os.path.join(true_root_path, "assets")

        default_icon_path = os.path.join(assets_path, "default_module.png")
        if comp_type.startswith("module"):
            default_icon_path = os.path.join(assets_path, "default_module.png")
        elif comp_type.startswith("plugin"):
            default_icon_path = os.path.join(assets_path, "default_plugin.png")
        elif comp_type.startswith("tool"):
            default_icon_path = os.path.join(assets_path, "default_tool.png")
        elif comp_type.startswith("trigger"):
            default_icon_path = os.path.join(assets_path, "default_trigger.png")

        if error:
            return await self._serve_image_file(request, default_icon_path)

        items_attr_map = {
            "module_manager_service": "loaded_modules",
            "plugin_manager_service": "loaded_plugins",
            "tools_manager_service": "loaded_tools",
            "widget_manager_service": "loaded_widgets",
            "trigger_manager_service": "loaded_triggers",
            "ai_provider_manager_service": "loaded_providers",
        }
        items_attr_name = items_attr_map.get(manager.service_id)
        if not items_attr_name:
            return await self._serve_image_file(request, default_icon_path)

        items = getattr(manager, items_attr_name, {})
        component_data = items.get(item_id)
        if not component_data:
            return await self._serve_image_file(request, default_icon_path)

        manifest = component_data.get("manifest", {})
        icon_filename = manifest.get("icon_file")
        component_path = component_data.get("path")

        if icon_filename and component_path:
            icon_path = os.path.join(component_path, icon_filename)
            if os.path.isfile(icon_path):
                return await self._serve_image_file(request, icon_path)

        return await self._serve_image_file(request, default_icon_path)
    async def handle_get_ai_provider_services(self, request):
        manager, error = self._get_manager_for_type("ai_providers")
        if error:
            return self._json_response({"error": error}, status=503)
        providers_info = manager.get_loaded_providers_info()
        return self._json_response(providers_info)
    def _get_manager_for_type(self, resource_type):
        manager_map = {
            "modules": "module_manager_service",
            "plugins": "plugin_manager_service",
            "tools": "tools_manager_service",
            "widgets": "widget_manager_service",
            "triggers": "trigger_manager_service",
            "ai_providers": "ai_provider_manager_service",
        }
        manager_name = manager_map.get(resource_type)
        if not manager_name:
            return None, f"Resource type '{resource_type}' is invalid."
        manager = self.service_instance.kernel.get_service(manager_name)
        if not manager:
            return (
                None,
                f"{manager_name} service is unavailable, possibly due to license restrictions.",
            )
        return manager, None
    async def handle_get_components(self, request):
        resource_type = (
            request.match_info.get("resource_type") or request.path.split("/")[3]
        )
        item_id = request.match_info.get("item_id", None)
        manager, error = self._get_manager_for_type(resource_type)
        if error:
            return self._json_response([], status=200)
        core_files = await self.service_instance._load_protected_component_ids()
        items_attr_map = {
            "module_manager_service": "loaded_modules",
            "plugin_manager_service": "loaded_plugins",
            "tools_manager_service": "loaded_tools",
            "widget_manager_service": "loaded_widgets",
            "trigger_manager_service": "loaded_triggers",
            "ai_provider_manager_service": "loaded_providers",
        }
        items_attr_name = items_attr_map.get(manager.service_id)
        if not items_attr_name:
            return self._json_response(
                {"error": f"Internal mapping error for service '{manager.service_id}'"},
                status=500,
            )
        items = getattr(manager, items_attr_name, {})
        if item_id:
            if item_id in items:
                item_data = items[item_id]
                manifest = item_data.get("manifest", {})
                response_item = {
                    "id": item_id,
                    "name": manifest.get("name", item_id),
                    "version": manifest.get("version", "N/A"),
                    "is_paused": item_data.get("is_paused", False),
                    "description": manifest.get("description", ""),
                    "manifest": manifest,
                    "path": item_data.get("path"),
                }
                return self._json_response(response_item)
            else:
                return self._json_response(
                    {"error": f"Component '{item_id}' not found in '{resource_type}'."},
                    status=404,
                )
        else:
            response_data = []
            for item_id_loop, item_data in items.items():
                manifest = item_data.get("manifest", {})
                response_data.append(
                    {
                        "id": item_id_loop,
                        "name": manifest.get("name", item_id_loop),
                        "version": manifest.get("version", "N/A"),
                        "is_paused": item_data.get("is_paused", False),
                        "description": manifest.get("description", ""),
                        "is_core": item_id_loop in core_files,
                        "tier": manifest.get("tier", "free"),
                        "manifest": manifest,
                    }
                )
            query_params = request.query
            try:
                limit = int(query_params.get("limit", 50))
                offset = int(query_params.get("offset", 0))
            except (ValueError, IndexError):
                limit = 50
                offset = 0
            sorted_data = sorted(response_data, key=lambda x: x["name"])
            paginated_data = sorted_data[offset : offset + limit]
            return self._json_response(paginated_data)
    async def handle_install_components(self, request):
        return self._json_response(
            {"error": "Install via API is not implemented yet."}, status=501
        )
    async def handle_delete_components(self, request):
        return self._json_response(
            {"error": "Delete via API is not implemented yet."}, status=501
        )
    async def handle_patch_component_state(self, request):
        resource_type = (
            request.match_info.get("resource_type") or request.path.split("/")[3]
        )
        item_id = request.match_info.get("item_id")
        core_files = await self.service_instance._load_protected_component_ids()
        if item_id in core_files:
            error_msg = self.service_instance.loc.get(
                "api_core_component_disable_error",
                fallback="Core components cannot be disabled.",
            )
            return self._json_response({"error": error_msg}, status=403)
        body = await request.json()
        if "paused" not in body or not isinstance(body["paused"], bool):
            return self._json_response(
                {"error": "Request body must contain a boolean 'paused' key."},
                status=400,
            )
        is_paused = body["paused"]
        manager, error = self._get_manager_for_type(resource_type)
        if error:
            return self._json_response({"error": error}, status=503)
        pause_method_name = f"set_{resource_type.rstrip('s')}_paused"
        pause_method = getattr(manager, pause_method_name, None)
        if not pause_method:
            return self._json_response(
                {
                    "error": f"State management method not found on {type(manager).__name__} for '{resource_type}'."
                },
                status=500,
            )
        success = pause_method(item_id, is_paused)
        if success:
            action = "paused" if is_paused else "resumed"
            return self._json_response(
                {
                    "status": "success",
                    "message": f"{resource_type.capitalize()[:-1]} '{item_id}' has been {action}.",
                }
            )
        else:
            return self._json_response(
                {"error": f"{resource_type.capitalize()[:-1]} '{item_id}' not found."},
                status=404,
            )
