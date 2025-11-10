########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\config.py total lines 35 
########################################################################

"""
(English Hardcode)
Centralized configuration for Flowork Gateway.
- Provides DATABASE_URL with a safe default (SQLite in /app/data/gateway.db)
- Provides SQLALCHEMY_DATABASE_URI mirroring DATABASE_URL for extensions that expect it
- Reads common env vars but keeps sensible defaults for development
Add-only policy: we do not remove existing behavior; we just ensure the required keys exist.
"""
import os
from pathlib import Path
DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)  # ensure dir exists
_DEFAULT_DB_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{DATA_DIR / 'gateway.db'}"
class Config:
    SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev_dummy_secret_do_not_use_in_prod")
    DATABASE_URL = _DEFAULT_DB_URL
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
    JSON_SORT_KEYS = False
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
class DevelopmentConfig(Config):
    DEBUG = True
class ProductionConfig(Config):
    DEBUG = False
class TestingConfig(Config):
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
