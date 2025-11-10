########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\localization_routes.py total lines 32 
########################################################################

from .base_api_route import BaseApiRoute
class LocalizationRoutes(BaseApiRoute):
    """
    Menyediakan rute API untuk mengambil data kamus bahasa yang sudah digabung.
    """
    def register_routes(self):
        return {
            "GET /api/v1/localization/{lang_code}": self.handle_get_dictionary,
        }
    async def handle_get_dictionary(self, request):
        lang_code = request.match_info.get("lang_code")
        loc = self.service_instance.loc
        if not loc:
            self.logger(
                "Gracefully handling missing LocalizationManager service.", "INFO"
            )
            return self._json_response({})
        dictionary = loc.languages.get(lang_code)
        if dictionary:
            return self._json_response(dictionary)
        else:
            en_dictionary = loc.languages.get("en")
            if en_dictionary:
                return self._json_response(en_dictionary)
            else:
                return self._json_response({})
