########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\preset_routes.py total lines 230 
########################################################################

from .base_api_route import BaseApiRoute
class PresetRoutes(BaseApiRoute):
    """
    Manages API routes for preset CRUD and versioning.
    """
    def register_routes(self):
        return {
            "GET /api/v1/presets": self.handle_get_presets,
            "GET /api/v1/presets/{preset_name}": self.handle_get_preset_detail,
            "POST /api/v1/presets": self.handle_post_presets,
            "DELETE /api/v1/presets/{preset_name}": self.handle_delete_preset,
            "GET /api/v1/presets/{preset_name}/versions": self.handle_get_preset_versions,
            "GET /api/v1/presets/{preset_name}/versions/{version_filename}": self.handle_get_specific_preset_version,
            "DELETE /api/v1/presets/{preset_name}/versions/{version_filename}": self.handle_delete_preset_version,
            "GET /api/v1/presets/{preset_name}/exists": self.handle_check_preset_exists,
        }
    async def handle_get_presets(self, request):
        preset_manager = self.service_instance.preset_manager
        if not preset_manager:
            self.logger("Gracefully handling missing PresetManager service.", "INFO") # English Log
            return self._json_response([])
        user_context = request.get("user_context", {})
        user_id = user_context.get("user_id")
        if not user_id:
            return self._json_response(
                {"error": "User context is missing, cannot fetch user-specific data."}, # English Hardcode
                status=401,
            )
        preset_list = preset_manager.get_preset_list(user_id=user_id)
        loc = self.service_instance.loc
        core_files = self.service_instance.core_component_ids
        response_data = []
        for item in preset_list:
            name = item.get("name")
            response_data.append(
                {
                    "id": name,
                    "name": name.replace("_", " ").replace("-", " "),
                    "version": "N/A", # English Hardcode
                    "is_paused": False,
                    "description": (
                        loc.get(
                            "marketplace_preset_desc", fallback="Workflow Preset File" # English Hardcode
                        )
                        if loc
                        else "Workflow Preset File" # English Hardcode
                    ),
                    "is_core": name in core_files,
                    "tier": "N/A", # English Hardcode
                }
            )
        return self._json_response(sorted(response_data, key=lambda x: x["name"]))
    async def handle_get_preset_detail(self, request):
        preset_name = request.match_info.get("preset_name")
        preset_manager = self.service_instance.preset_manager
        if not preset_manager:
            return self._json_response([])
        user_context = request.get("user_context", {})
        user_id = user_context.get("user_id")
        if not user_id:
            return self._json_response(
                {"error": "User context is missing."}, status=401 # English Hardcode
            )
        preset_data = preset_manager.get_preset_data(preset_name, user_id=user_id)
        if preset_data:
            return self._json_response(preset_data)
        else:
            return self._json_response(
                {"error": f"Preset '{preset_name}' not found."}, status=404 # English Hardcode
            )
    async def handle_post_presets(self, request):
        preset_manager = self.service_instance.preset_manager
        if not preset_manager:
            return self._json_response(
                {"error": "PresetManager service is unavailable."}, status=503 # English Hardcode
            )
        body = await request.json()
        preset_name = body.get("name")
        workflow_data = body.get("workflow_data")
        signature = body.get("signature")
        if not preset_name or not workflow_data or not signature:
            return self._json_response(
                {"error": "Request body must contain 'name', 'workflow_data', and 'signature'."}, # English Hardcode
                status=400,
            )
        user_context = request.get("user_context", {})
        user_id = user_context.get("user_id")
        if not user_id:
            return self._json_response(
                {"error": "User context is missing, cannot save preset."}, status=401 # English Hardcode
            )
        save_success = preset_manager.save_preset(
            preset_name,
            workflow_data,
            user_id=user_id,
            signature=signature
        )
        if save_success:
            return self._json_response(
                {
                    "status": "success", # English Hardcode
                    "message": f"Preset '{preset_name}' created/updated.", # English Hardcode
                },
                status=201,
            )
        else:
            return self._json_response(
                {"error": f"Failed to save preset '{preset_name}'."}, status=500 # English Hardcode
            )
    async def handle_delete_preset(self, request):
        preset_name = request.match_info.get("preset_name")
        preset_manager = self.service_instance.preset_manager
        if not preset_manager:
            return self._json_response(
                {"error": "PresetManager service is unavailable."}, status=503 # English Hardcode
            )
        user_context = request.get("user_context", {})
        user_id = user_context.get("user_id")
        if not user_id:
            return self._json_response(
                {"error": "User context is missing, cannot delete preset."}, status=401 # English Hardcode
            )
        success = preset_manager.delete_preset(preset_name, user_id=user_id)
        if success:
            return self._json_response(None, status=204)
        else:
            return self._json_response(
                {"error": f"Preset '{preset_name}' not found or could not be deleted."}, # English Hardcode
                status=404,
            )
    async def handle_get_preset_versions(self, request):
        preset_name = request.match_info.get("preset_name")
        preset_manager = self.service_instance.preset_manager
        if not preset_manager:
            return self._json_response(
                {"error": "PresetManager service is unavailable."}, status=503 # English Hardcode
            )
        user_context = request.get("user_context", {})
        user_id = user_context.get("user_id")
        if not user_id:
            return self._json_response(
                {"error": "User context is missing."}, status=401 # English Hardcode
            )
        versions_list = preset_manager.get_preset_versions(preset_name, user_id=user_id)
        return self._json_response(versions_list)
    async def handle_get_specific_preset_version(self, request):
        preset_name = request.match_info.get("preset_name")
        version_filename = request.match_info.get("version_filename")
        preset_manager = self.service_instance.preset_manager
        if not preset_manager:
            return self._json_response(
                {"error": "PresetManager service is unavailable."}, status=503 # English Hardcode
            )
        user_context = request.get("user_context", {})
        user_id = user_context.get("user_id")
        if not user_id:
            return self._json_response(
                {"error": "User context is missing."}, status=401 # English Hardcode
            )
        version_data = preset_manager.load_preset_version(
            preset_name, version_filename, user_id=user_id
        )
        if version_data:
            return self._json_response(version_data)
        else:
            return self._json_response(
                {
                    "error": f"Version '{version_filename}' for preset '{preset_name}' not found." # English Hardcode
                },
                status=404,
            )
    async def handle_delete_preset_version(self, request):
        preset_name = request.match_info.get("preset_name")
        version_filename = request.match_info.get("version_filename")
        preset_manager = self.service_instance.preset_manager
        if not preset_manager:
            return self._json_response(
                {"error": "PresetManager service is unavailable."}, status=503 # English Hardcode
            )
        user_context = request.get("user_context", {})
        user_id = user_context.get("user_id")
        if not user_id:
            return self._json_response(
                {"error": "User context is missing."}, status=401 # English Hardcode
            )
        success = preset_manager.delete_preset_version(
            preset_name, version_filename, user_id=user_id
        )
        if success:
            return self._json_response(
                {
                    "status": "success", # English Hardcode
                    "message": f"Version '{version_filename}' deleted.", # English Hardcode
                }
            )
        else:
            return self._json_response(
                {"error": f"Could not delete version '{version_filename}'."}, status=404 # English Hardcode
            )
    async def handle_check_preset_exists(self, request):
        """
        Checks if a preset exists locally for the given user.
        Called by the Gateway before share operations.
        """
        preset_name = request.match_info.get("preset_name")
        user_context = request.get("user_context", {})
        user_id = user_context.get("user_id") # Ambil user_id dari header yang di-inject middleware
        if not preset_name or not user_id:
            return self._json_response(
                {"error": "Preset name and user context are required."}, # English Hardcode
                status=400
            )
        preset_manager = self.service_instance.preset_manager # Akses PresetManagerService via service_instance
        if not preset_manager:
            self.logger("PresetRoutes: PresetManagerService not available.", "ERROR") # English Log
            return self._json_response({"error": "Preset manager service unavailable."}, status=503) # English Hardcode
        self.logger(f"PresetRoutes: Checking existence of preset '{preset_name}' for user '{user_id[:8]}...'", "DEBUG") # English Log
        preset_data = preset_manager.get_preset_data(preset_name, user_id=user_id)
        if preset_data:
            self.logger(f"PresetRoutes: Preset '{preset_name}' found for user '{user_id[:8]}...'", "INFO") # English Log
            return self._json_response({"exists": True}) # English Hardcode
        else:
            self.logger(f"PresetRoutes: Preset '{preset_name}' NOT found for user '{user_id[:8]}...'", "WARN") # English Log
            return self._json_response({"exists": False}, status=404) # English Hardcode
