########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\execution_routes.py total lines 247 
########################################################################

from .base_api_route import BaseApiRoute
import time
import uuid
class ExecutionRoutes(BaseApiRoute):
    """
    Manages API routes for starting workflows/scans and checking job statuses.
    """
    def register_routes(self):
        return {
            "POST /api/v1/workflow/execute/{preset_name}": self.handle_workflow_execution,
            "POST /api/v1/workflow/execute_raw": self.handle_raw_workflow_execution,
            "POST /api/v1/diagnostics/execute": self.handle_scan_execution,
            "POST /api/v1/diagnostics/execute/{scanner_id}": self.handle_scan_execution,
            "GET /api/v1/workflow/status/{job_id}": self.handle_get_job_status,
            "GET /api/v1/workflow/history/{context_id}/{connection_id}": self.handle_get_connection_history,
            "GET /api/v1/diagnostics/status/{job_id}": self.handle_get_job_status,
            "POST /api/v1/workflow/stop/{job_id}": self.handle_stop_workflow,
            "POST /api/v1/workflow/pause/{job_id}": self.handle_pause_workflow,
            "POST /api/v1/workflow/resume/{job_id}": self.handle_resume_workflow,
        }
    async def handle_get_connection_history(self, request):  # (PERBAIKAN)
        context_id = request.match_info.get("context_id")  # (PERBAIKAN)
        connection_id = request.match_info.get("connection_id")  # (PERBAIKAN)
        executor = self.service_instance.workflow_executor
        if not executor:
            return self._json_response(
                {"error": "WorkflowExecutorService is not available."}, status=503
            )
        history = executor.get_connection_history(context_id)
        connection_data = [
            step
            for step in history.get("steps", [])
            if step.get("connection_id") == connection_id
        ]
        if connection_data:
            return self._json_response(connection_data[-1])  # (PERBAIKAN)
        else:
            return self._json_response(
                {
                    "error": f"No history found for connection '{connection_id}' in context '{context_id}'."
                },
                status=404,
            )
    async def handle_raw_workflow_execution(self, request):  # (PERBAIKAN)
        """
        Receives a raw workflow structure (nodes, connections) and queues it for execution.
        """
        try:
            body = await request.json()  # (PERBAIKAN)
            nodes = body.get("nodes")
            connections = body.get("connections")
            initial_payload = body.get(
                "initial_payload", {"triggered_by": "raw_api_call"}
            )
            start_node_id = body.get("start_node_id")
            mode = body.get("mode", "EXECUTE")
            if nodes is None or connections is None:
                return self._json_response(
                    {"error": "Request body must contain 'nodes' and 'connections'."},
                    status=400,
                )
            self.logger(
                f"API call received to execute raw workflow in '{mode}' mode.", "INFO"
            )
            user_context = request.get("user_context", None)  # (PERBAIKAN)
            job_id = self.service_instance.trigger_workflow_by_api(
                preset_name="raw_execution_from_canvas",
                initial_payload=initial_payload,
                raw_workflow_data={"nodes": nodes, "connections": connections},
                start_node_id=start_node_id,
                mode=mode,
                user_context=user_context,
            )
            if job_id:
                return self._json_response(
                    {
                        "status": "accepted",
                        "message": "Raw workflow has been queued for execution.",
                        "job_id": job_id,
                    },
                    status=202,
                )
            else:
                return self._json_response(
                    {"status": "error", "message": "Failed to queue the raw workflow."},
                    status=500,
                )
        except Exception as e:
            self.logger(f"Error handling raw workflow execution: {e}", "CRITICAL")
            return self._json_response(
                {"error": f"Internal Server Error: {e}"}, status=500
            )
    async def handle_workflow_execution(self, request):  # (PERBAIKAN)
        preset_name = request.match_info.get("preset_name")  # (PERBAIKAN)
        if not preset_name:
            return self._json_response(
                {"error": "Preset name is required for execution."}, status=400
            )
        if not self.kernel.is_tier_sufficient("basic"):
            COOLDOWN_SECONDS = 300
            state_manager = self.service_instance.state_manager
            if state_manager:
                user_context = request.get("user_context", None)  # (PERBAIKAN)
                user_id = user_context.get("user_id") if user_context else "public"
                last_call_timestamp = state_manager.get(
                    "api_last_call_timestamp_free_tier", user_id=user_id, default=0
                )
                current_time = time.time()
                if (current_time - last_call_timestamp) < COOLDOWN_SECONDS:
                    remaining_time = int(
                        COOLDOWN_SECONDS - (current_time - last_call_timestamp)
                    )
                    error_message = f"API call limit for Free tier. Please wait {remaining_time} seconds."
                    self.logger(error_message, "WARN")
                    return self._json_response(
                        {"status": "error", "message": error_message}, status=429
                    )
        try:
            body = await request.json()  # (PERBAIKAN)
            initial_payload = body if body is not None else {"triggered_by": "api"}
            self.logger(f"API call received to execute preset '{preset_name}'.", "INFO")
            user_context = request.get("user_context", None)  # (PERBAIKAN)
            if not self.kernel.is_tier_sufficient("basic"):
                state_manager = self.service_instance.state_manager
                if state_manager:
                    user_id = user_context.get("user_id") if user_context else "public"
                    state_manager.set(
                        "api_last_call_timestamp_free_tier",
                        time.time(),
                        user_id=user_id,
                    )
            job_id = self.service_instance.trigger_workflow_by_api(
                preset_name,
                initial_payload,
                user_context=user_context,
            )
            if job_id:
                return self._json_response(
                    {
                        "status": "accepted",
                        "message": f"Workflow for preset '{preset_name}' has been queued.",
                        "job_id": job_id,
                    },
                    status=202,
                )
            else:
                return self._json_response(
                    {
                        "status": "error",
                        "message": f"Preset '{preset_name}' not found.",
                    },
                    status=404,
                )
        except Exception as e:
            self.logger(
                f"Error handling API execution for '{preset_name}': {e}", "ERROR"
            )
            return self._json_response(
                {"error": f"Internal Server Error: {e}"}, status=500
            )
    async def handle_scan_execution(self, request):  # (PERBAIKAN)
        scanner_id = request.match_info.get("scanner_id")  # (PERBAIKAN)
        try:
            log_target = "ALL" if not scanner_id else scanner_id
            self.logger(
                f"API call received to execute diagnostics scan for: {log_target}.",
                "INFO",
            )
            job_id = self.service_instance.trigger_scan_by_api(scanner_id)
            if job_id:
                return self._json_response(
                    {
                        "status": "accepted",
                        "message": f"System diagnostics scan for '{log_target}' has been queued.",
                        "job_id": job_id,
                    },
                    status=202,
                )
            else:
                return self._json_response(
                    {"status": "error", "message": "Failed to start diagnostics scan."},
                    status=500,
                )
        except Exception as e:
            self.logger(f"Error handling API scan execution: {e}", "ERROR")
            return self._json_response(
                {"error": f"Internal Server Error: {e}"}, status=500
            )
    async def handle_get_job_status(self, request):  # (PERBAIKAN)
        job_id = request.match_info.get("job_id")  # (PERBAIKAN)
        if not job_id:
            return self._json_response({"error": "Job ID is required."}, status=400)
        status_data = self.service_instance.get_job_status(job_id)
        if status_data:
            return self._json_response(status_data)
        else:
            return self._json_response(
                {"error": f"Job with ID '{job_id}' not found."}, status=404
            )
    async def handle_stop_workflow(self, request):  # (PERBAIKAN)
        job_id = request.match_info.get("job_id")  # (PERBAIKAN)
        executor = self.service_instance.workflow_executor
        if not executor:
            return self._json_response(
                {"error": "WorkflowExecutorService is not available."}, status=503
            )
        executor.stop_execution()
        return self._json_response(
            {
                "status": "success",
                "message": f"Stop signal sent to the current workflow.",
            }
        )
    async def handle_pause_workflow(self, request):  # (PERBAIKAN)
        job_id = request.match_info.get("job_id")  # (PERBAIKAN)
        executor = self.service_instance.workflow_executor
        if not executor:
            return self._json_response(
                {"error": "WorkflowExecutorService is not available."}, status=503
            )
        executor.pause_execution()
        return self._json_response(
            {
                "status": "success",
                "message": f"Pause signal sent to the current workflow.",
            }
        )
    async def handle_resume_workflow(self, request):  # (PERBAIKAN)
        job_id = request.match_info.get("job_id")  # (PERBAIKAN)
        executor = self.service_instance.workflow_executor
        if not executor:
            return self._json_response(
                {"error": "WorkflowExecutorService is not available."}, status=503
            )
        executor.resume_execution()
        return self._json_response(
            {
                "status": "success",
                "message": f"Resume signal sent to the current workflow.",
            }
        )
