########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\agent_routes.py total lines 132 
########################################################################

from .base_api_route import BaseApiRoute
class AgentRoutes(BaseApiRoute):
    """
    Manages API routes for Agent CRUD, execution, and status checks.
    """
    def register_routes(self):
        return {
            "GET /api/v1/agents": self.handle_get_agents,
            "GET /api/v1/agents/{agent_id}": self.handle_get_agent,  # (PERBAIKAN) Dipisah agar lebih jelas
            "POST /api/v1/agents": self.handle_post_agents,
            "DELETE /api/v1/agents/{agent_id}": self.handle_delete_agent,
            "POST /api/v1/agents/{agent_id}/run": self.handle_run_agent,
            "GET /api/v1/agents/run/{run_id}": self.handle_get_agent_run_status,
            "POST /api/v1/agents/run/{run_id}/stop": self.handle_stop_agent_run,
        }
    async def handle_get_agents(self, request):  # (PERBAIKAN) Diubah jadi async
        agent_manager = self.service_instance.agent_manager
        if not agent_manager:
            return self._json_response(
                {
                    "error": "AgentManagerService is not available due to license restrictions."
                },
                status=503,
            )
        agents = agent_manager.get_all_agents()
        return self._json_response(agents)
    async def handle_get_agent(
        self, request
    ):  # (PERBAIKAN) Handler baru untuk satu agent
        agent_id = request.match_info.get("agent_id")
        agent_manager = self.service_instance.agent_manager
        if not agent_manager:
            return self._json_response(
                {
                    "error": "AgentManagerService is not available due to license restrictions."
                },
                status=503,
            )
        agent = agent_manager.get_agent(agent_id)
        if agent:
            return self._json_response(agent)
        else:
            return self._json_response(
                {"error": f"Agent with ID '{agent_id}' not found."}, status=404
            )
    async def handle_post_agents(self, request):  # (PERBAIKAN) Diubah jadi async
        agent_manager = self.service_instance.agent_manager
        if not agent_manager:
            return self._json_response(
                {
                    "error": "AgentManagerService is not available due to license restrictions."
                },
                status=503,
            )
        body = await request.json()
        result = agent_manager.save_agent(body)
        if "error" in result:
            return self._json_response(result, status=400)
        else:
            return self._json_response(result, status=201)
    async def handle_delete_agent(self, request):  # (PERBAIKAN) Diubah jadi async
        agent_id = request.match_info.get("agent_id")
        agent_manager = self.service_instance.agent_manager
        if not agent_manager:
            return self._json_response(
                {
                    "error": "AgentManagerService is not available due to license restrictions."
                },
                status=503,
            )
        if agent_manager.delete_agent(agent_id):
            return self._json_response(None, status=204)
        else:
            return self._json_response({"error": "Agent not found."}, status=404)
    async def handle_run_agent(self, request):  # (PERBAIKAN) Diubah jadi async
        agent_id = request.match_info.get("agent_id")
        agent_executor = self.service_instance.agent_executor
        if not agent_executor:
            return self._json_response(
                {
                    "error": "AgentExecutorService is not available due to license restrictions."
                },
                status=503,
            )
        body = await request.json()
        if "objective" not in body:
            return self._json_response(
                {"error": "Request must contain an 'objective'."}, status=400
            )
        result = agent_executor.run_agent(agent_id, body["objective"])
        if "error" in result:
            return self._json_response(result, status=409)
        else:
            return self._json_response(result, status=202)
    async def handle_get_agent_run_status(
        self, request
    ):  # (PERBAIKAN) Diubah jadi async
        run_id = request.match_info.get("run_id")
        agent_executor = self.service_instance.agent_executor
        if not agent_executor:
            return self._json_response(
                {
                    "error": "AgentExecutorService is not available due to license restrictions."
                },
                status=503,
            )
        status = agent_executor.get_run_status(run_id)
        if "error" in status:
            return self._json_response(status, status=404)
        else:
            return self._json_response(status)
    async def handle_stop_agent_run(self, request):  # (PERBAIKAN) Diubah jadi async
        run_id = request.match_info.get("run_id")
        agent_executor = self.service_instance.agent_executor
        if not agent_executor:
            return self._json_response(
                {
                    "error": "AgentExecutorService is not available due to license restrictions."
                },
                status=503,
            )
        result = agent_executor.stop_agent_run(run_id)
        if "error" in result:
            return self._json_response(result, status=404)
        else:
            return self._json_response(result)
