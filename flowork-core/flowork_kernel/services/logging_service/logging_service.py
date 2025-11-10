########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\logging_service\logging_service.py total lines 48 
########################################################################

import logging
import os
import sys
import threading
CORE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LOGS_DIR = os.path.join(CORE_ROOT, "logs")
try:
    os.makedirs(LOGS_DIR, exist_ok=True)
except Exception as e:
    sys.stderr.write(f"[CRITICAL] Failed to create log directory at {LOGS_DIR}: {e}\n")
_loggers = {}
_lock = threading.Lock()
def setup_logging(name, filename):
    """
    Sets up a logger for a specific module/process.
    Ensures logs go to both the console and a dedicated file.
    Is safe to call multiple times (idempotent).
    """
    with _lock:
        if name in _loggers:
            return _loggers[name]
        logger = logging.getLogger(name)
        if logger.hasHandlers():
             logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.propagate = False # (PENTING) Mencegah log duplikat ke root logger
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [PID %(process)d] - [%(name)s] - %(message)s'
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        try:
            file_path = os.path.join(LOGS_DIR, filename)
            file_handler = logging.FileHandler(file_path, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
             sys.stderr.write(f"Failed to attach file handler for {filename}: {e}\n")
        _loggers[name] = logger
        logger.info(f"Logging configured for '{name}'. Outputting to console and {filename}.")
        return logger
