########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\settings_routes.py total lines 40 
########################################################################

from .base_api_route import BaseApiRoute
class SettingsRoutes(BaseApiRoute):
    """
    Manages API routes for application settings.
    """
    def register_routes(self):
        return {
            "GET /api/v1/settings": self.handle_get_settings,
            "PATCH /api/v1/settings": self.handle_patch_settings,
        }
    async def handle_get_settings(
        self, request
    ):  # (PERBAIKAN) Jadi async dan terima request
        loc = self.service_instance.loc
        if not loc:
            return self._json_response(
                {"error": "LocalizationManager service is unavailable."}, status=503
            )
        return self._json_response(loc._settings_cache)
    async def handle_patch_settings(
        self, request
    ):  # (PERBAIKAN) Jadi async dan terima request
        loc = self.service_instance.loc
        if not loc:
            return self._json_response(
                {"error": "LocalizationManager service is unavailable."}, status=503
            )
        body = await request.json()  # (PERBAIKAN) Ambil body secara async
        current_settings = loc._settings_cache.copy()
        current_settings.update(body)
        loc._save_settings(current_settings)
        return self._json_response(
            {"status": "success", "message": "Settings updated."}
        )
