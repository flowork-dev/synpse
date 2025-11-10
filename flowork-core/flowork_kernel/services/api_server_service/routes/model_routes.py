########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\model_routes.py total lines 117 
########################################################################

from .base_api_route import BaseApiRoute
import os
class ModelRoutes(BaseApiRoute):
    """
    Manages API routes for model conversion, uploading, and listing.
    """
    def register_routes(self):
        return {
            "POST /api/v1/models/convert": self.handle_post_model_conversion,
            "GET /api/v1/models/convert/status/{job_id}": self.handle_get_conversion_status,
            "POST /api/v1/models/upload": self.handle_model_upload,
            "GET /api/v1/ai_models": self.handle_get_local_ai_models,
            "POST /api/v1/models/requantize": self.handle_post_model_requantize,
        }
    async def handle_post_model_requantize(self, request):
        converter_service = self.service_instance.converter_service
        if not converter_service:
            return self._json_response(
                {
                    "error": "ModelConverterService is not available due to license restrictions."
                },
                status=503,
            )
        body = await request.json()
        required_keys = ["source_gguf_path", "output_gguf_name"]
        if not all(key in body for key in required_keys):
            return self._json_response(
                {"error": f"Request body must contain: {', '.join(required_keys)}"},
                status=400,
            )
        result = converter_service.start_requantize_job(
            body["source_gguf_path"],
            body["output_gguf_name"],
            body.get("quantize_method", "Q4_K_M"),
        )
        if "error" in result:
            return self._json_response(result, status=409)
        else:
            return self._json_response(result, status=202)
    async def handle_post_model_conversion(self, request):
        converter_service = self.service_instance.converter_service
        if not converter_service:
            return self._json_response(
                {
                    "error": "ModelConverterService is not available due to license restrictions."
                },
                status=503,
            )
        body = await request.json()
        required_keys = ["source_model_folder", "output_gguf_name"]
        if not all(key in body for key in required_keys):
            return self._json_response(
                {"error": f"Request body must contain: {', '.join(required_keys)}"},
                status=400,
            )
        result = converter_service.start_conversion_job(
            body["source_model_folder"],
            body["output_gguf_name"],
            body.get("quantize_method", "Q4_K_M"),
        )
        if "error" in result:
            return self._json_response(result, status=409)
        else:
            return self._json_response(result, status=202)
    async def handle_get_conversion_status(self, request):
        job_id = request.match_info.get("job_id")
        converter_service = self.service_instance.converter_service
        if not converter_service:
            return self._json_response(
                {
                    "error": "ModelConverterService is not available due to license restrictions."
                },
                status=503,
            )
        status = converter_service.get_job_status(job_id)
        if "error" in status:
            return self._json_response(status, status=404)
        else:
            return self._json_response(status)
    async def handle_model_upload(self, request):
        return self._json_response(
            {"error": "Not implemented for aiohttp yet."}, status=501
        )
    async def handle_get_local_ai_models(self, request):
        ai_manager = self.service_instance.ai_provider_manager_service
        if not ai_manager:
            return self._json_response(
                {"error": "AIProviderManagerService is not available."}, status=503
            )
        try:
            local_models = ai_manager.local_models
            model_type_filter = request.query.get("type", "text")
            response_data = []
            for model_id, model_data in local_models.items():
                if model_data.get("category") == model_type_filter:
                    clean_name = model_data.get("name", "Unknown Model")
                    response_data.append(
                        {
                            "id": clean_name,
                            "name": clean_name,
                            "version": "N/A",
                            "description": f"Local {model_data.get('type', 'model').upper()} model.",
                            "tier": "pro",
                        }
                    )
            return self._json_response(sorted(response_data, key=lambda x: x["name"]))
        except Exception as e:
            self.logger(f"Error listing local AI models: {e}", "ERROR")
            return self._json_response(
                {"error": f"Could not list local AI models: {e}"}, status=500
            )
