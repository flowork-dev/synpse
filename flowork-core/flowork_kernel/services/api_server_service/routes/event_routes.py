########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\event_routes.py total lines 40 
########################################################################

from .base_api_route import BaseApiRoute
class EventRoutes(BaseApiRoute):
    """
    Manages API routes for publishing events to the internal Event Bus.
    This allows the GUI to trigger backend events without direct kernel access.
    """
    def register_routes(self):
        """
        Registers all event-related endpoints.
        """
        return {
            "POST /api/v1/events/publish": self.handle_publish_event,
        }
    async def handle_publish_event(self, request):
        """
        Handles a request from a client to publish an event.
        """
        body = await request.json()
        if "event_name" not in body or "event_data" not in body:
            return self._json_response(
                {"error": "Request body must contain 'event_name' and 'event_data'."},
                status=400,
            )  # ENGLISH HARDCODE
        event_bus = self.kernel.get_service("event_bus")
        if not event_bus:
            return self._json_response(
                {"error": "EventBus service is not available."}, status=503
            )  # ENGLISH HARDCODE
        event_bus.publish(
            body["event_name"], body["event_data"], publisher_id="ApiClient_GUI"
        )
        return self._json_response(
            {"status": "event_published", "event_name": body["event_name"]}, status=202
        )  # ENGLISH HARDCODE
