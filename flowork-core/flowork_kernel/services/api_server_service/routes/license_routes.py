########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\license_routes.py total lines 79 
########################################################################

from .base_api_route import BaseApiRoute
class LicenseRoutes(BaseApiRoute):
    """
    Manages API routes for license-related actions like activation.
    """
    def register_routes(self):
        return {
            "POST /api/v1/license/activate": self.handle_activate_license,
            "POST /api/v1/license/deactivate": self.handle_deactivate_license,
            "POST /api/v1/license/validate": self.handle_validate_license,
        }
    async def handle_activate_license(self, request):
        """
        Handles the license activation request from the UI via ApiClient.
        """
        license_manager = self.service_instance.kernel.get_service(
            "license_manager_service"
        )
        if not license_manager:
            return self._json_response(
                {"error": "LicenseManager service is not available."}, status=503
            )
        body = await request.json()
        if "license_content" not in body:
            return self._json_response(
                {"error": "Request body must contain 'license_content'."}, status=400
            )
        license_content = body["license_content"]
        success, message = license_manager.activate_license_on_server(license_content)
        if success:
            return self._json_response({"status": "success", "message": message})
        else:
            return self._json_response({"error": message}, status=400)
    async def handle_deactivate_license(self, request):
        """
        Handles the license deactivation request from the UI via ApiClient.
        """
        license_manager = self.service_instance.kernel.get_service(
            "license_manager_service"
        )
        if not license_manager:
            return self._json_response(
                {"error": "LicenseManager service is not available."}, status=503
            )
        success, message = license_manager.deactivate_license_on_server()
        if success:
            return self._json_response({"status": "success", "message": message})
        else:
            return self._json_response({"error": message}, status=400)
    async def handle_validate_license(self, request):
        """
        Handles the validation of a local license file against the central server.
        """
        license_manager = self.service_instance.kernel.get_service(
            "license_manager_service"
        )
        if not license_manager:
            return self._json_response(
                {"error": "LicenseManager service is not available."}, status=503
            )
        body = await request.json()
        if "license_key" not in body or "machine_id" not in body:
            return self._json_response(
                {"error": "Request body must contain 'license_key' and 'machine_id'."},
                status=400,
            )
        success, message = license_manager.validate_local_license_online(
            body["license_key"], body["machine_id"]
        )
        if success:
            return self._json_response({"status": "success", "message": message})
        else:
            return self._json_response({"error": message}, status=403)
