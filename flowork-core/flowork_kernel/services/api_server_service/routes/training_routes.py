########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\training_routes.py total lines 66 
########################################################################

from .base_api_route import BaseApiRoute
class TrainingRoutes(BaseApiRoute):
    """
    Manages API routes for starting and monitoring AI fine-tuning jobs.
    """
    def register_routes(self):
        return {
            "POST /api/v1/training/start": self.handle_start_training_job,
            "GET /api/v1/training/status/{job_id}": self.handle_get_training_job_status,
        }
    async def handle_start_training_job(self, request):  # (PERBAIKAN KUNCI)
        training_service = self.service_instance.training_service
        if not training_service:
            return self._json_response(
                {
                    "error": "AITrainingService is not available due to license restrictions."
                },
                status=503,
            )
        body = await request.json()
        if not body:
            return self._json_response(
                {"error": "Request body is required."}, status=400
            )
        required_keys = [
            "base_model_id",
            "dataset_name",
            "new_model_name",
            "training_args",
        ]
        if not all(key in body for key in required_keys):
            return self._json_response(
                {"error": f"Request body must contain: {', '.join(required_keys)}"},
                status=400,
            )
        result = training_service.start_fine_tuning_job(
            body["base_model_id"],
            body["dataset_name"],
            body["new_model_name"],
            body["training_args"],
        )
        if "error" in result:
            return self._json_response(result, status=409)
        else:
            return self._json_response(result, status=202)
    async def handle_get_training_job_status(self, request):  # (PERBAIKAN KUNCI)
        job_id = request.match_info.get("job_id")
        training_service = self.service_instance.training_service
        if not training_service:
            return self._json_response(
                {
                    "error": "AITrainingService is not available due to license restrictions."
                },
                status=503,
            )
        status = training_service.get_job_status(job_id)
        if "error" in status:
            return self._json_response(status, status=404)
        else:
            return self._json_response(status)
