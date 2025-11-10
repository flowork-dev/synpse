########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\prompt_routes.py total lines 105 
########################################################################

from .base_api_route import BaseApiRoute
class PromptRoutes(BaseApiRoute):
    """
    (REFACTORED) Manages API routes for Prompt Templates.
    This class is now a thin layer that delegates all logic to the PromptManagerService.
    (HARDENED) Added checks to handle cases where the service might fail to load and return None.
    """
    def register_routes(self):
        return {
            "GET /api/v1/prompts": self.get_all_prompts,
            "POST /api/v1/prompts": self.create_prompt,
            "GET /api/v1/prompts/{prompt_id}": self.get_prompt_by_id,
            "PUT /api/v1/prompts/{prompt_id}": self.update_prompt,
            "DELETE /api/v1/prompts/{prompt_id}": self.delete_prompt,
        }
    async def get_all_prompts(self, request):  # (PERBAIKAN KUNCI)
        prompt_manager = self.service_instance.prompt_manager_service
        if not prompt_manager:
            return self._json_response(
                {"error": "PromptManagerService is not available."}, status=503
            )
        result = prompt_manager.get_all_prompts()
        if result is not None:
            return self._json_response(result)
        else:
            return self._json_response(
                {"error": "Service call to get all prompts failed."}, status=500
            )
    async def get_prompt_by_id(self, request):  # (PERBAIKAN KUNCI)
        prompt_id = request.match_info.get("prompt_id")
        prompt_manager = self.service_instance.prompt_manager_service
        if not prompt_manager:
            return self._json_response(
                {"error": "PromptManagerService is not available."}, status=503
            )
        result = prompt_manager.get_prompt(prompt_id)
        if result:
            return self._json_response(result)
        else:
            return self._json_response(
                {"error": "Prompt not found or service call failed."}, status=404
            )
    async def create_prompt(self, request):  # (PERBAIKAN KUNCI)
        prompt_manager = self.service_instance.prompt_manager_service
        if not prompt_manager:
            return self._json_response(
                {"error": "PromptManagerService is not available."}, status=503
            )
        body = await request.json()
        if not body:
            return self._json_response(
                {"error": "Request body is required."}, status=400
            )
        result = prompt_manager.create_prompt(body)
        if result and "error" in result:
            return self._json_response(result, status=400)
        elif result:
            return self._json_response(result, status=201)
        else:
            return self._json_response(
                {"error": "Service call to create prompt failed."}, status=500
            )
    async def update_prompt(self, request):  # (PERBAIKAN KUNCI)
        prompt_id = request.match_info.get("prompt_id")
        prompt_manager = self.service_instance.prompt_manager_service
        if not prompt_manager:
            return self._json_response(
                {"error": "PromptManagerService is not available."}, status=503
            )
        body = await request.json()
        if not body:
            return self._json_response(
                {"error": "Request body is required."}, status=400
            )
        result = prompt_manager.update_prompt(prompt_id, body)
        if result and "error" in result:
            return self._json_response(result, status=400)
        elif result:
            return self._json_response(result)
        else:
            return self._json_response(
                {"error": "Service call to update prompt failed."}, status=500
            )
    async def delete_prompt(self, request):  # (PERBAIKAN KUNCI)
        prompt_id = request.match_info.get("prompt_id")
        prompt_manager = self.service_instance.prompt_manager_service
        if not prompt_manager:
            return self._json_response(
                {"error": "PromptManagerService is not available."}, status=503
            )
        result = prompt_manager.delete_prompt(prompt_id)
        if result and "error" in result:
            return self._json_response(result, status=404)
        elif result:
            return self._json_response(result, status=204)  # 204 No Content
        else:
            return self._json_response(
                {"error": "Service call to delete prompt failed."}, status=500
            )
