########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\auth_routes.py total lines 70 
########################################################################

from .base_api_route import BaseApiRoute
from flowork_kernel.api_client import ApiClient
import re
class AuthRoutes(BaseApiRoute):
    """
    Manages API routes for user authentication (login, register, logout, profile).
    Acts as a secure bridge between the client and the Supabase backend.
    """
    def __init__(self, service_instance):
        super().__init__(service_instance)
        pass
    def register_routes(self):
        return {
            "POST /api/v1/auth/register": self.handle_register,
            "POST /api/v1/auth/login": self.handle_login,
            "POST /api/v1/auth/logout": self.handle_logout,
            "GET /api/v1/auth/profile": self.handle_get_profile,
        }
    def _extract_token_from_header(self, request):  # (PERBAIKAN) Menerima request
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.split(" ")[1]
        return self.service_instance.state_manager.get("user_session_token")
    async def handle_register(self, request):  # (PERBAIKAN) Diubah jadi async
        return self._json_response(
            {"error": "Not Implemented: Registration is handled by the Gateway."},
            status=501,
        )
    async def handle_login(self, request):  # (PERBAIKAN) Diubah jadi async
        return self._json_response(
            {"error": "Not Implemented: Login is handled by the Gateway."}, status=501
        )
    async def handle_logout(self, request):  # (PERBAIKAN) Diubah jadi async
        self.service_instance.state_manager.delete("user_session_token")
        self.kernel.current_user = None
        return self._json_response(
            {"message": "Logged out successfully from Core cache."}
        )
    async def handle_get_profile(self, request):  # (PERBAIKAN) Diubah jadi async
        """
        [MODIFIKASI FINAL] Core TIDAK VALIDASI TOKEN. Core hanya merespons status lisensi lokal.
        Validasi user/token sudah dilakukan oleh Gateway (Flask-JWT).
        """
        if not self.kernel.current_user:
            self.kernel.write_to_log(
                "GET /auth/profile denied: User data missing in Kernel state.", "WARN"
            )
            return self._json_response(
                {"error": "User data not found in Core cache. Session invalid."},
                status=401,
            )
        response_data = self.kernel.current_user.copy()
        license_manager = self.kernel.get_service("license_manager_service")
        response_data["tier"] = self.kernel.license_tier
        response_data["license_expires_at"] = (
            license_manager.license_data.get("expiry_date")
            if license_manager and license_manager.license_data
            else None
        )
        response_data["message"] = "Profile status retrieved from Core cache."
        self.kernel.write_to_log(
            "GET /auth/profile successful (Internal Cache).", "INFO"
        )
        return self._json_response(response_data)
