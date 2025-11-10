########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\ui_state_routes.py total lines 132 
########################################################################

from .base_api_route import BaseApiRoute
import threading
class UIStateRoutes(BaseApiRoute):
    """
    (REMASTERED FOR AIOHTTP & CLASS-BASED STRUCTURE)
    Manages API routes for all UI state, including dashboard layouts, tab sessions,
    and generic key-value state persistence for both global and user-specific contexts.
    """
    def register_routes(self):
        return {
            "GET /api/v1/uistate/dashboards/{tab_id}": self.get_dashboard_state,
            "POST /api/v1/uistate/dashboards/{tab_id}": self.set_dashboard_state,
            "GET /api/v1/uistate/session/tabs": self.get_session_tabs,
            "POST /api/v1/uistate/session/tabs": self.set_session_tabs,
            "GET /api/v1/uistate/generic/{key:.*}": self.get_generic_state,
            "POST /api/v1/uistate/generic/{key:.*}": self.set_generic_state,
            "DELETE /api/v1/uistate/generic/{key:.*}": self.delete_generic_state,
        }
    async def get_dashboard_state(self, request):
        tab_id = request.match_info["tab_id"]
        state_manager = self.kernel.get_service("state_manager", is_system_call=True)
        user_id = request.get("user_context", {}).get("user_id")
        if not state_manager:
            return self._json_response(
                {"error": "State manager not available"}, status=500
            )
        state = state_manager.get(f"dashboard_layout::{tab_id}", user_id=user_id)
        return self._json_response(state or {})
    async def set_dashboard_state(self, request):
        tab_id = request.match_info["tab_id"]
        state_manager = self.kernel.get_service("state_manager", is_system_call=True)
        user_id = request.get("user_context", {}).get("user_id")
        if not state_manager:
            return self._json_response(
                {"error": "State manager not available"}, status=500
            )
        data = await request.json()
        state_manager.set(f"dashboard_layout::{tab_id}", data, user_id=user_id)
        return self._json_response({"status": "success"})
    async def get_session_tabs(self, request):
        state_manager = self.kernel.get_service("state_manager", is_system_call=True)
        user_id = request.get("user_context", {}).get("user_id")
        if not state_manager:
            return self._json_response(
                {"error": "State manager not available"}, status=500
            )
        tabs = state_manager.get("open_tabs", user_id=user_id, default=[])
        return self._json_response(tabs)
    async def set_session_tabs(self, request):
        state_manager = self.kernel.get_service("state_manager", is_system_call=True)
        user_id = request.get("user_context", {}).get("user_id")
        if not state_manager:
            return self._json_response(
                {"error": "State manager not available"}, status=500
            )
        tabs = await request.json()
        state_manager.set("open_tabs", tabs, user_id=user_id)
        return self._json_response({"status": "success"})
    async def get_generic_state(self, request):
        key = request.match_info["key"]
        state_manager = self.kernel.get_service("state_manager", is_system_call=True)
        user_id = request.get("user_context", {}).get("user_id")
        if not state_manager:
            return self._json_response(
                {"error": "State manager not available"}, status=500
            )
        value = state_manager.get(key, user_id=user_id)
        return self._json_response(value if value is not None else {})
    async def set_generic_state(self, request):
        key = request.match_info["key"]
        state_manager = self.kernel.get_service("state_manager", is_system_call=True)
        user_id = request.get("user_context", {}).get("user_id")
        if not state_manager:
            return self._json_response(
                {"error": "State manager not available"}, status=500
            )
        data = await request.json()
        if key == "current_user_data":
            self.logger(
                "Received user data from Gateway, updating Kernel state...",
                "INFO",
                source="ApiServer",
            )
            self.kernel.current_user = data
            state_manager.set("gateway_injected_user_data", data, user_id=user_id)
            self.logger(
                "Saved user data to persistent state for recovery after restart.",
                "DEBUG",
                "ApiServer",
            )
            self._update_permissions_synchronous(data)
        state_manager.set(key, data, user_id=user_id)
        return self._json_response({"status": "success"})
    def _update_permissions_synchronous(self, user_data):
        license_manager = self.kernel.get_service(
            "license_manager_service", is_system_call=True
        )
        if license_manager:
            self.logger(
                "User data updated, re-verifying license and permissions synchronously...",
                "INFO",
                source="ApiServer",
            )
            license_manager.verify_license_on_startup()
            permission_manager = self.kernel.get_service(
                "permission_manager_service", is_system_call=True
            )
            if permission_manager:
                permission_manager.load_rules_from_source(
                    license_manager.remote_permission_rules
                )
                self.logger(
                    "Permissions successfully re-synced.",
                    "SUCCESS",
                    source="ApiServer",
                )
    async def delete_generic_state(self, request):
        key = request.match_info["key"]
        state_manager = self.kernel.get_service("state_manager", is_system_call=True)
        user_id = request.get("user_context", {}).get("user_id")
        if not state_manager:
            return self._json_response(
                {"error": "State manager not available"}, status=500
            )
        state_manager.delete(key, user_id=user_id)
        return self._json_response({"status": "success"})
