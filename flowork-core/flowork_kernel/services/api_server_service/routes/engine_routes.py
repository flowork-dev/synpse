########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\engine_routes.py total lines 220 
########################################################################

import datetime
import time
from .base_api_route import BaseApiRoute
from flowork_kernel.exceptions import PermissionDeniedError
from collections import Counter, defaultdict
class EngineRoutes(BaseApiRoute):
    """
    Manages API routes for direct engine actions like scheduling.
    """
    def __init__(self, service_instance):
        super().__init__(service_instance)
        self._os_scheduler_service = None
    @property
    def os_scheduler(self):
        if self._os_scheduler_service is None:
            self._os_scheduler_service = self.kernel.get_service(
                "os_scheduler_service", is_system_call=True
            )
        return self._os_scheduler_service
    def register_routes(self):
        return {
            "POST /api/v1/engine/actions/schedule": self.handle_schedule_action,
            "POST /api/v1/engine/actions/cancel-schedule": self.handle_cancel_schedule,
            "GET /api/v1/engine/live-stats": self.handle_get_live_stats,
        }
    async def handle_get_live_stats(self, request):
        """
        (PERBAIKAN) Provides live, non-historical, AND historical data for consumption by the Gateway.
        This includes active jobs, system overview, and 24h stats.
        """
        user_id_from_header = request.headers.get("X-Flowork-User-ID")
        self.logger(f"[Core Engine API] Received /live-stats request for User-ID: {user_id_from_header}", "INFO", "ApiServer") # English Log
        active_jobs = []
        twenty_four_hours_ago = time.time() - (24 * 60 * 60)
        execution_stats_24h = {"success": 0, "failed": 0} # English Hardcode
        top_failing_presets = Counter()
        slowest_presets_list = []
        if self.service_instance.job_statuses:
            with self.service_instance.job_statuses_lock:
                all_jobs_copy = list(self.service_instance.job_statuses.items())
            for job_id, job_data in all_jobs_copy:
                job_user_context = job_data.get("user_context")
                job_owner_id = job_user_context.get("id") if isinstance(job_user_context, dict) else None
                if user_id_from_header and job_owner_id and job_owner_id.lower() != user_id_from_header.lower():
                    continue
                job_status = job_data.get("status")
                if job_status == "RUNNING": # English Hardcode
                    start_time = job_data.get("start_time", 0)
                    duration = time.time() - start_time
                    active_jobs.append(
                        {
                            "id": job_id,
                            "preset": job_data.get("preset_name", "N/A"), # English Hardcode
                            "duration_seconds": round(duration, 2),
                        }
                    )
                end_time = job_data.get("end_time")
                if end_time and end_time >= twenty_four_hours_ago:
                    preset_name = job_data.get("preset_name", "Unknown Preset") # English Hardcode
                    if job_status == "SUCCEEDED": # English Hardcode
                        execution_stats_24h["success"] += 1
                    elif job_status == "FAILED": # English Hardcode
                        execution_stats_24h["failed"] += 1
                        top_failing_presets[preset_name] += 1
                    start_time = job_data.get("start_time")
                    if start_time:
                        duration_ms = (end_time - start_time) * 1000
                        slowest_presets_list.append({
                            "name": preset_name,
                            "avg_duration_ms": duration_ms
                        })
        self.logger(f"[Core Engine API] Found {len(active_jobs)} active jobs relevant to user {user_id_from_header}", "DEBUG", "ApiServer") # English Log
        preset_count = 0
        if self.service_instance.preset_manager and user_id_from_header:
            try:
                preset_list = self.service_instance.preset_manager.get_preset_list(user_id=user_id_from_header)
                preset_count = len(preset_list)
            except Exception as e:
                 self.logger(f"[Core Engine API] Error getting preset count for user {user_id_from_header}: {e}", "WARN", "ApiServer") # English Log
                 preset_count = 0 # Fallback jika gagal
        system_overview = {
            "kernel_version": self.kernel.APP_VERSION,
            "license_tier": self.kernel.license_tier.capitalize(),
            "modules": (
                len(self.service_instance.module_manager_service.loaded_modules)
                if self.service_instance.module_manager_service
                else 0
            ),
            "plugins": (
                len(self.service_instance.plugin_manager_service.loaded_plugins)
                if self.service_instance.plugin_manager_service
                else 0
            ),
            "widgets": (
                len(self.service_instance.widget_manager_service.loaded_widgets)
                if self.service_instance.widget_manager_service
                else 0
            ),
            "triggers": (
                len(self.service_instance.trigger_manager_service.loaded_triggers)
                if self.service_instance.trigger_manager_service
                else 0
            ),
            "presets": preset_count,
        }
        top_failing_list = [{"name": name, "count": count} for name, count in top_failing_presets.most_common(5)]
        avg_slowest = defaultdict(lambda: {'total_time': 0, 'count': 0})
        for item in slowest_presets_list:
            avg_slowest[item['name']]['total_time'] += item['avg_duration_ms']
            avg_slowest[item['name']]['count'] += 1
        avg_slowest_list = []
        for name, data in avg_slowest.items():
            avg_slowest_list.append({
                "name": name,
                "avg_duration_ms": data['total_time'] / data['count']
            })
        final_slowest_list = sorted(avg_slowest_list, key=lambda x: x['avg_duration_ms'], reverse=True)[:5]
        live_data = {
            "active_jobs": active_jobs,
            "system_overview": system_overview,
            "execution_stats_24h": execution_stats_24h, # Data untuk chart "Executions (24h)"
            "top_failing_presets": top_failing_list, # Data untuk "Performance Hotspots"
            "top_slowest_presets": final_slowest_list, # Data untuk "Performance Hotspots"
            "recent_activity": list(self.service_instance.recent_events), # Kirim juga event terbaru
            "usage_stats": {"used": execution_stats_24h["success"] + execution_stats_24h["failed"]} # Data kuota (total eksekusi)
        }
        return self._json_response(live_data)
    async def handle_schedule_action(self, request):
        """
        Receives a request to schedule a system action (restart/shutdown).
        """
        try:
            permission_manager = self.kernel.get_service(
                "permission_manager_service", is_system_call=True
            )
            if permission_manager:
                permission_manager.check_permission("engine_management") # English Hardcode
            body = await request.json()
            action_type = body.get("action_type")
            timestamp_str = body.get("timestamp")
            task_name = body.get("task_name")
            if not all([action_type, timestamp_str, task_name]):
                return self._json_response(
                    {"error": "Missing action_type, timestamp, or task_name"}, # English Hardcode
                    status=400,
                )
            scheduled_dt = datetime.datetime.fromisoformat(timestamp_str)
            if not self.os_scheduler:
                return self._json_response(
                    {"error": "OsSchedulerService is not available."}, status=503 # English Hardcode
                )
            success = self.os_scheduler.schedule_action(
                action_type, scheduled_dt, task_name
            )
            if success:
                return self._json_response(
                    {
                        "status": "success", # English Hardcode
                        "message": f"Action '{action_type}' scheduled successfully.", # English Hardcode
                    },
                    status=202,
                )
            else:
                return self._json_response(
                    {"error": "Failed to schedule action via OS scheduler."}, status=500 # English Hardcode
                )
        except PermissionDeniedError as e:
            return self._json_response({"error": str(e)}, status=403)
        except Exception as e:
            self.logger(f"Error handling schedule action: {e}", "CRITICAL") # English Hardcode
            return self._json_response(
                {"error": f"Internal Server Error: {e}"}, status=500 # English Hardcode
            )
    async def handle_cancel_schedule(self, request):
        """
        Receives a request to cancel a scheduled system action.
        """
        try:
            permission_manager = self.kernel.get_service(
                "permission_manager_service", is_system_call=True
            )
            if permission_manager:
                permission_manager.check_permission("engine_management") # English Hardcode
            body = await request.json()
            task_name = body.get("task_name")
            if not task_name:
                return self._json_response({"error": "Missing task_name"}, status=400) # English Hardcode
            if not self.os_scheduler:
                return self._json_response(
                    {"error": "OsSchedulerService is not available."}, status=503 # English Hardcode
                )
            success = self.os_scheduler.cancel_task(task_name)
            if success:
                return self._json_response(
                    {
                        "status": "success", # English Hardcode
                        "message": f"Task '{task_name}' cancelled successfully.", # English Hardcode
                    },
                    status=200,
                )
            else:
                return self._json_response(
                    {
                        "error": f"Failed to cancel task '{task_name}'. It may have already run or does not exist." # English Hardcode
                    },
                    status=404,
                )
        except PermissionDeniedError as e:
            return self._json_response({"error": str(e)}, status=403)
        except Exception as e:
            self.logger(f"Error handling cancel schedule action: {e}", "CRITICAL") # English Hardcode
            return self._json_response(
                {"error": f"Internal Server Error: {e}"}, status=500 # English Hardcode
            )
