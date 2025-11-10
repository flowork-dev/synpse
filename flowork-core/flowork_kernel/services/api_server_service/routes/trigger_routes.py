########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\trigger_routes.py total lines 149 
########################################################################

from .base_api_route import BaseApiRoute
import uuid
class TriggerRoutes(BaseApiRoute):
    """
    Manages API routes for Trigger definitions and rules.
    """
    def register_routes(self):
        return {
            "GET /api/v1/triggers/definitions": self.handle_get_trigger_definitions,
            "GET /api/v1/triggers/rules": self.handle_get_trigger_rules,
            "GET /api/v1/triggers/rules/{rule_id}": self.handle_get_trigger_rule_by_id,  # (PERBAIKAN KUNCI) Nama fungsi diganti agar unik
            "POST /api/v1/triggers/rules": self.handle_post_trigger_rule,
            "PUT /api/v1/triggers/rules/{rule_id}": self.handle_put_trigger_rule,
            "DELETE /api/v1/triggers/rules/{rule_id}": self.handle_delete_trigger_rule,
            "POST /api/v1/triggers/actions/reload": self.handle_reload_triggers,
        }
    async def handle_get_trigger_definitions(self, request):  # (PERBAIKAN KUNCI)
        trigger_manager = self.service_instance.trigger_manager
        if not trigger_manager:
            return self._json_response(
                {"error": "TriggerManager service is unavailable."}, status=503
            )
        definitions = [
            tdata["manifest"] for tid, tdata in trigger_manager.loaded_triggers.items()
        ]
        return self._json_response(sorted(definitions, key=lambda x: x.get("name", "")))
    async def handle_get_trigger_rules(self, request):  # (PERBAIKAN KUNCI)
        state_manager = self.service_instance.state_manager
        if not state_manager:
            return self._json_response(
                {"error": "StateManager service is unavailable."}, status=503
            )
        all_rules = state_manager.get("trigger_rules", default={})
        trigger_manager = self.service_instance.trigger_manager
        scheduler_manager = self.service_instance.scheduler_manager
        enriched_rules = []
        for rid, rdata in all_rules.items():
            enriched_data = rdata.copy()
            enriched_data["id"] = rid
            trigger_id = rdata.get("trigger_id")
            enriched_data["trigger_name"] = (
                trigger_manager.loaded_triggers.get(trigger_id, {})
                .get("manifest", {})
                .get("name", trigger_id)
                if trigger_manager
                else trigger_id
            )
            next_run = None
            if (
                scheduler_manager
                and trigger_id == "cron_trigger"
                and rdata.get("is_enabled")
            ):
                try:
                    next_run_time = scheduler_manager.get_next_run_time(rid)
                    if next_run_time:
                        next_run = next_run_time.isoformat()
                except Exception as e:
                    self.logger(
                        f"A non-critical error occurred while fetching next_run_time for job '{rid}'. The UI will show '-'. Error: {e}",
                        "WARN",
                    )
                    next_run = None
            enriched_data["next_run_time"] = next_run
            enriched_rules.append(enriched_data)
        return self._json_response(enriched_rules)
    async def handle_get_trigger_rule_by_id(self, request):  # (PERBAIKAN KUNCI)
        rule_id = request.match_info.get("rule_id")
        state_manager = self.service_instance.state_manager
        if not state_manager:
            return self._json_response(
                {"error": "StateManager service is unavailable."}, status=503
            )
        all_rules = state_manager.get("trigger_rules", default={})
        rule_data = all_rules.get(rule_id)
        if rule_data:
            return self._json_response(rule_data)
        else:
            return self._json_response(
                {"error": f"Rule with ID '{rule_id}' not found."}, status=404
            )
    async def handle_post_trigger_rule(self, request):  # (PERBAIKAN KUNCI)
        state_manager = self.service_instance.state_manager
        if not state_manager:
            return self._json_response(
                {"error": "StateManager service is unavailable."}, status=503
            )
        body = await request.json()
        if body is None:
            return self._json_response(
                {"error": "Request body is required."}, status=400
            )
        new_rule_id = str(uuid.uuid4())
        all_rules = state_manager.get("trigger_rules", default={})
        all_rules[new_rule_id] = body
        state_manager.set("trigger_rules", all_rules)
        return self._json_response({"status": "success", "id": new_rule_id}, status=201)
    async def handle_put_trigger_rule(self, request):  # (PERBAIKAN KUNCI)
        rule_id = request.match_info.get("rule_id")
        state_manager = self.service_instance.state_manager
        if not state_manager:
            return self._json_response(
                {"error": "StateManager service is unavailable."}, status=503
            )
        body = await request.json()
        if body is None:
            return self._json_response(
                {"error": "Request body is required."}, status=400
            )
        all_rules = state_manager.get("trigger_rules", default={})
        if rule_id not in all_rules:
            return self._json_response(
                {"error": f"Rule with ID '{rule_id}' not found."}, status=404
            )
        all_rules[rule_id] = body
        state_manager.set("trigger_rules", all_rules)
        return self._json_response({"status": "success", "id": rule_id})
    async def handle_delete_trigger_rule(self, request):  # (PERBAIKAN KUNCI)
        rule_id = request.match_info.get("rule_id")
        state_manager = self.service_instance.state_manager
        if not state_manager:
            return self._json_response(
                {"error": "StateManager service is unavailable."}, status=503
            )
        all_rules = state_manager.get("trigger_rules", default={})
        if rule_id in all_rules:
            del all_rules[rule_id]
            state_manager.set("trigger_rules", all_rules)
            return self._json_response(None, status=204)
        else:
            return self._json_response(
                {"error": f"Rule with ID '{rule_id}' not found."}, status=404
            )
    async def handle_reload_triggers(self, request):  # (PERBAIKAN KUNCI)
        trigger_manager = self.service_instance.trigger_manager
        if not trigger_manager:
            return self._json_response(
                {"error": "TriggerManager service is unavailable."}, status=503
            )
        trigger_manager.start_all_listeners()
        return self._json_response(
            {"status": "success", "message": "Trigger reload process initiated."}
        )
