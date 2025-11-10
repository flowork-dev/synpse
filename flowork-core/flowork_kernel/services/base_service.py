########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\base_service.py total lines 44 
########################################################################

import logging # <-- START ADDED CODE (FIX) - Import standard logging
class BaseService:
    """
    The base class for all services in the Flowork ecosystem.
    (MODIFIED) Now uses a property for self.loc to prevent dependency load order issues.
    """
    def __init__(self, kernel, service_id: str):
        """
        Initializes the service.
        Args:
            kernel: The main Kernel instance, providing access to other services and core functions.
            service_id (str): The unique identifier for this service, as defined in services.json.
        """
        self.kernel = kernel
        self.service_id = service_id
        self.logger = logging.getLogger(f"{service_id}")
        self._loc_cache = None # [ADDED] Cache for the localization service.
    @property
    def loc(self):
        """
        [ADDED] Lazy-loads the localization manager service.
        This prevents startup order issues by only fetching the service the first time it's actually used.
        """
        if self._loc_cache is None:
            self._loc_cache = self.kernel.get_service('localization_manager')
        return self._loc_cache
    def start(self):
        """
        Optional method to start any background tasks or long-running processes.
        Called by the Kernel during the startup sequence.
        """
        pass
    def stop(self):
        """
        Optional method to gracefully stop any background tasks before the application closes.
        Called by the Kernel during the shutdown sequence.
        """
        pass
