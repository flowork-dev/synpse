########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\ai_providers\text\gemini_provider\provider.py total lines 45 
########################################################################

from flowork_kernel.api_contract import BaseAIProvider
from .core.GeminiConnection import GeminiConnection
import google.generativeai as genai
import google.generativeai.types as model_types
class GeminiProvider(BaseAIProvider):
    TIER = "basic"
    """
    Provides a connection to Google's Gemini AI models.
    """
    def __init__(self, kernel, manifest: dict):
        super().__init__(kernel, manifest)
        self.connection = GeminiConnection(self.kernel)
        self.chat_sessions = {}
    def get_provider_name(self) -> str:
        return self.loc.get("gemini_provider_name", fallback="Google Gemini")
    def is_ready(self) -> tuple[bool, str]:
        """Checks if the Gemini API key is configured."""
        if self.connection.configure():
            return (True, "")
        else:
            return (
                False,
                self.loc.get(
                    "gemini_provider_err_not_configured",
                    fallback="Gemini Provider is not configured. Check for a valid GEMINI_API_KEY in Settings.",
                ),
            )
    def generate_response(self, prompt: str) -> dict:
        is_ready, message = self.is_ready()
        if not is_ready:
            return {"type": "text", "data": f"ERROR: {message}"}
        response_type = "text"
        try:
            model = genai.GenerativeModel("gemini-1.5-flash-latest")
            generation_prompt = prompt
            response = model.generate_content(generation_prompt)
            return {"type": response_type, "data": response.text} # (English Hardcode) response_type is now always 'text'
        except Exception as e:
            return {"type": "text", "data": f"GEMINI_API_ERROR: {e}"}
