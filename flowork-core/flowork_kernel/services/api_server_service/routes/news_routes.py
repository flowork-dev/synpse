########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\news_routes.py total lines 26 
########################################################################

from .base_api_route import BaseApiRoute
class NewsRoutes(BaseApiRoute):
    def register_routes(self):
        return {
            "GET /api/v1/news": self.handle_get_news,
        }
    async def handle_get_news(self, request):
        """
        Handles the request to get news articles.
        It calls the NewsFetcherService to get the data.
        """
        news_service = self.kernel.get_service("news_fetcher_service")
        if not news_service:
            return self._json_response(
                {"error": "News service is currently unavailable."}, status=503
            )
        news_data = news_service.get_news()
        if isinstance(news_data, dict) and "error" in news_data:
            return self._json_response(news_data, status=500)
        return self._json_response(news_data)
