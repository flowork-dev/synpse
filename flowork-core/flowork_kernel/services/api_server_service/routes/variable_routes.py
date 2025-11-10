########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\variable_routes.py total lines 103 
########################################################################

from .base_api_route import BaseApiRoute
class VariableRoutes(BaseApiRoute):
    """
    (REMASTERED FOR ASYNC) Manages API routes for variable CRUD operations.
    """
    def register_routes(self):
        return {
            "GET /api/v1/variables": self.handle_get_variables,
            "PUT /api/v1/variables/{variable_name}": self.handle_put_variable,
            "PATCH /api/v1/variables/{variable_name}/state": self.handle_patch_variable_state,
            "DELETE /api/v1/variables/{variable_name}": self.handle_delete_variable,
        }
    async def handle_get_variables(self, request):
        variable_manager = self.service_instance.variable_manager
        if not variable_manager:
            return self._json_response(
                {"error": "VariableManager service is unavailable."}, status=503
            )
        user_context = request.get("user_context", {})
        user_id = user_context.get("user_id")
        all_vars = variable_manager.get_all_variables_for_api(user_id=user_id)
        return self._json_response(all_vars)
    async def handle_put_variable(self, request):
        variable_name = request.match_info.get("variable_name")
        variable_manager = self.service_instance.variable_manager
        if not variable_manager:
            return self._json_response(
                {"error": "VariableManager service is unavailable."}, status=503
            )
        body = await request.json()
        value = body.get("value")
        is_secret = body.get("is_secret", False)
        is_enabled = body.get("is_enabled", True)
        mode = body.get("mode", "single")
        if value is None:
            return self._json_response(
                {"error": "Request body must contain 'value'."}, status=400
            )
        try:
            user_context = request.get("user_context", {})
            user_id = user_context.get("user_id")
            variable_manager.set_variable(
                variable_name, value, is_secret, is_enabled, mode=mode, user_id=user_id
            )
            return self._json_response(
                {"status": "success", "message": f"Variable '{variable_name}' saved."},
                status=200,
            )
        except ValueError as e:
            return self._json_response({"error": str(e)}, status=400)
    async def handle_patch_variable_state(self, request):
        variable_name = request.match_info.get("variable_name")
        variable_manager = self.service_instance.variable_manager
        if not variable_manager:
            return self._json_response(
                {"error": "VariableManager service is unavailable."}, status=503
            )
        body = await request.json()
        if "enabled" not in body or not isinstance(body["enabled"], bool):
            return self._json_response(
                {"error": "Request body must contain a boolean 'enabled' key."},
                status=400,
            )
        is_enabled = body["enabled"]
        user_context = request.get("user_context", {})
        user_id = user_context.get("user_id")
        success = variable_manager.set_variable_enabled_state(
            variable_name, is_enabled, user_id=user_id
        )
        if success:
            action = "enabled" if is_enabled else "disabled"
            return self._json_response(
                {
                    "status": "success",
                    "message": f"Variable '{variable_name}' has been {action}.",
                },
                status=200,
            )
        else:
            return self._json_response(
                {"error": f"Variable '{variable_name}' not found."}, status=404
            )
    async def handle_delete_variable(self, request):
        variable_name = request.match_info.get("variable_name")
        variable_manager = self.service_instance.variable_manager
        if not variable_manager:
            return self._json_response(
                {"error": "VariableManager service is unavailable."}, status=503
            )
        user_context = request.get("user_context", {})
        user_id = user_context.get("user_id")
        if variable_manager.delete_variable(variable_name, user_id=user_id):
            return self._json_response(None, status=204)  # No Content
        else:
            return self._json_response(
                {"error": f"Variable '{variable_name}' not found."}, status=404
            )
