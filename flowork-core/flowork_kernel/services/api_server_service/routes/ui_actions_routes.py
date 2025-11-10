########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\ui_actions_routes.py total lines 56 
########################################################################

from .base_api_route import BaseApiRoute
class UIActionsRoutes(BaseApiRoute):
    """
    Manages API routes for actions initiated by the user interface,
    such as creating new tabs.
    """
    def register_routes(self):
        """
        Registers all UI action endpoints.
        """
        return {
            "POST /api/v1/ui/actions/open_managed_tab": self.handle_open_managed_tab,
        }
    async def handle_add_new_workflow_tab(self, request):  # (PERBAIKAN KUNCI)
        """
        Handles the request from the GUI to create a new workflow tab.
        """
        return self._json_response(
            {"error": "Not Implemented: Tab creation is a client-side responsibility."},
            status=501,
        )
    async def handle_open_managed_tab(self, request):  # (PERBAIKAN KUNCI)
        """
        Handles a request to open a specific, managed tab (e.g., Marketplace).
        It publishes an event that the active UI provider can listen to.
        """
        body = await request.json()
        if not body or "tab_key" not in body:
            return self._json_response(
                {"error": "Request must contain a 'tab_key'."}, status=400
            )
        event_bus = self.service_instance.event_bus
        if not event_bus:
            return self._json_response(
                {"error": "EventBus service is not available."}, status=503
            )
        tab_key = body["tab_key"]
        event_bus.publish(
            "OPEN_MANAGED_TAB_REQUEST", {"tab_key": tab_key}, publisher_id="ApiServer"
        )
        self.logger(
            f"Published OPEN_MANAGED_TAB_REQUEST event for tab_key: '{tab_key}'", "INFO"
        )
        return self._json_response(
            {
                "status": "accepted",
                "message": f"Request to open tab '{tab_key}' has been broadcasted.",
            },
            status=202,
        )
