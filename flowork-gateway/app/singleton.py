########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\singleton.py total lines 58 
########################################################################

import threading
import typing as t
class SingletonMeta(type):
    """
    Thread-safe singleton metaclass.
    When a class uses this metaclass, only one instance of that class
    will be created per process.
    """
    _instances: t.Dict[t.Type, t.Any] = {}
    _lock = threading.Lock()
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super(SingletonMeta, cls).__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]
    @classmethod
    def set_instance(mcs, instance_class, instance):
        """
        Manually registers an instance with the singleton registry.
        WARNING: UNUSED for now; kept to respect 'only add, not remove'.
        """
        with mcs._lock:
            if instance_class not in mcs._instances:
                mcs._instances[instance_class] = instance
    @classmethod
    def get_instance(mcs, instance_class):
        """
        Retrieves a manually registered instance.
        WARNING: UNUSED for now; kept to respect 'only add, not remove'.
        """
        with mcs._lock:
            return mcs._instances.get(instance_class)
class _GlobalHandle(metaclass=SingletonMeta):
    """
    Process-wide global handle. Provides registry helpers so that code
    using Singleton() can share a simple global, if needed.
    """
    def set_instance(self, instance_class, instance):
        SingletonMeta.set_instance(instance_class, instance)
    def get_instance(self, instance_class):
        return SingletonMeta.get_instance(instance_class)
class Singleton:  # facade class (callable)
    """
    Backward-compatible facade. Instantiating this returns the same
    global handle every time. This is NOT a metaclass.
    """
    _handle = _GlobalHandle()
    def __new__(cls, *args, **kwargs):
        return cls._handle
__all__ = ["SingletonMeta", "Singleton"]
