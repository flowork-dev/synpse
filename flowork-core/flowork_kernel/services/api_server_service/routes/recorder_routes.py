########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\recorder_routes.py total lines 71 
########################################################################

from .base_api_route import BaseApiRoute
from flowork_kernel.exceptions import PermissionDeniedError
class RecorderRoutes(BaseApiRoute):
    """
    Manages API routes for the screen recorder service.
    """
    def register_routes(self):
        return {
            "POST /api/v1/recorder/start": self.handle_start_recording,
            "POST /api/v1/recorder/stop": self.handle_stop_recording,
        }
    async def handle_start_recording(self, request):  # (PERBAIKAN KUNCI)
        try:
            recorder_service = self.kernel.get_service("screen_recorder_service")
            if not recorder_service:
                return self._json_response(
                    {"error": "ScreenRecorderService is not available."}, status=503
                )
            success = recorder_service.start_recording()
            if success:
                return self._json_response(
                    {"status": "success", "message": "Screen recording started."}
                )
            else:
                return self._json_response(
                    {
                        "error": "Failed to start screen recording. Check logs for details."
                    },
                    status=500,
                )
        except PermissionDeniedError as e:
            return self._json_response({"error": str(e)}, status=403)
        except Exception as e:
            self.logger(f"API Error starting recording: {e}", "CRITICAL")
            return self._json_response(
                {"error": f"Internal server error: {e}"}, status=500
            )
    async def handle_stop_recording(self, request):  # (PERBAIKAN KUNCI)
        try:
            recorder_service = self.kernel.get_service("screen_recorder_service")
            if not recorder_service:
                return self._json_response(
                    {"error": "ScreenRecorderService is not available."}, status=503
                )
            file_path = recorder_service.stop_recording()
            if file_path:
                return self._json_response(
                    {
                        "status": "success",
                        "message": "Screen recording stopped.",
                        "file_path": file_path,
                    }
                )
            else:
                return self._json_response(
                    {"error": "Failed to stop screen recording or save the file."},
                    status=500,
                )
        except PermissionDeniedError as e:
            return self._json_response({"error": str(e)}, status=403)
        except Exception as e:
            self.logger(f"API Error stopping recording: {e}", "CRITICAL")
            return self._json_response(
                {"error": f"Internal server error: {e}"}, status=500
            )
