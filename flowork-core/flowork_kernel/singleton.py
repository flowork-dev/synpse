########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\singleton.py total lines 38 
########################################################################

import threading
class Singleton(type):
    """
    A standard Singleton metaclass to ensure only one instance of a service
    exists within the main process (like the DB service or the Job Queue).
    """
    _instances = {}
    _lock = threading.Lock()
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
    @classmethod
    def set_instance(mcs, instance_class, instance):
        """
        Note (English): Manually registers an instance with the Singleton registry.
        This is used by run_server.py to store the Job Queue and DB Service.
        'mcs' is the convention for 'metaclass' (like 'cls' for class).
        """
        with mcs._lock:
            if instance_class not in mcs._instances:
                mcs._instances[instance_class] = instance
    @classmethod
    def get_instance(mcs, instance_class):
        """
        Note (English): Retrieves a manually registered instance.
        Used by workers and services to get the shared Job Queue/DB Service.
        """
        with mcs._lock:
            return mcs._instances.get(instance_class)
