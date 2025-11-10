########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\__init__.py total lines 176 
########################################################################

"""
(Roadmap 1.C, 1.E, 2.2, 3.1, 4.1, 4.5, 3.3)
Gateway Application Factory (create_app).
"""
import logging
from logging.handlers import RotatingFileHandler
import os
from flask import Flask, jsonify
from flask import Flask, jsonify, request, g # <-- START MODIFIED CODE (BUG FIX 'g')
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS # (English Hardcode) Import the main CORS library
_CONFIG = None
try:
    from config import Config as _RootConfig  # type: ignore
    _CONFIG = _RootConfig
except ModuleNotFoundError:
    try:
        from .config import Config as _PkgConfig  # type: ignore
        _CONFIG = _PkgConfig
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "[Flowork Gateway] FATAL: Unable to import 'Config'. "
            "Expected either '/app/config.py' or 'app/config.py'. "
            "Check your volume mounts and repository layout."
        ) from e
Config = _CONFIG
from .extensions import db, migrate, socketio
from .extensions import db as gateway_db
from .metrics import register_metrics
from . import sockets # (MODIFIKASI)
from .rl.limiter import RateLimiter
from .db.router import db_router # Import the instance
from .ops.drain import drain_bp, init_drain_state # (FIXED) Import correct names
from .db.pragma import init_pragma # (FIXED) This import will work now
from app.etl.exporter import start_exporter_thread  # Uses absolute app.* for clarity
from .ops.health import bp as health_bp # (English Hardcode) Import health blueprint
limiter = RateLimiter()
def _configure_logging():
    """
    Configure rotating file + console logger.
    This logger is shared by the entire Gateway so logs are centralized.
    """
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    log_dir = os.environ.get("GATEWAY_LOG_DIR", "/app/data/logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "gateway.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    ))
    file_handler.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s"
    ))
    console_handler.setLevel(log_level)
    root_logger = logging.getLogger()
    existing = {type(h) for h in root_logger.handlers}
    if not root_logger.hasHandlers():
        root_logger.setLevel(log_level)
    if RotatingFileHandler not in existing:
        root_logger.addHandler(file_handler)
    if logging.StreamHandler not in existing:
        root_logger.addHandler(console_handler)
    root_logger.info(
        f"--- Flowork Gateway Starting (Log Level: {log_level_str}) ---"
    )
    return root_logger
def create_app(config_class: type = Config):
    """
    Main application factory for Flowork Gateway.
    """
    root_logger = _configure_logging()
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.logger = root_logger
    app.logger.info("[Startup] Initializing core services...")
    CORS(app, origins=["https://flowork.cloud", "http://localhost:5173"], supports_credentials=True)
    gateway_db.init_app(app)
    migrate.init_app(app, gateway_db)
    with app.app_context():
        init_pragma(app, gateway_db)
    register_metrics(app)
    limiter.init_app(app)
    db_router.init_app(app)
    init_drain_state(app) # (FIXED) Call correct function
    socketio.init_app(
        app,
        async_mode='gevent', # <-- (ADDED) Use gevent to match requirements
        cors_allowed_origins="*", # <-- INI KUNCI untuk WebSocket
        path='/api/socket.io'
    )
    from .routes.auth import auth_bp
    from .routes.system import system_bp
    from .routes.cluster import cluster_bp
    from .routes.dispatch import dispatch_bp
    from .ops.chaos import chaos_bp
    from .engine.heartbeat_api import engine_hb_bp
    from .routes.proxy import proxy_bp
    from .routes.user import user_bp
    from .routes.user_state import user_state_bp
    from .routes.presets import presets_bp
    from .routes.workflow_shares import workflow_shares_bp
    from .routes.dashboard import dashboard_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(cluster_bp)
    app.register_blueprint(dispatch_bp)
    app.register_blueprint(chaos_bp)
    app.register_blueprint(drain_bp)
    app.register_blueprint(health_bp) # (English Hardcode) Register the health blueprint
    app.register_blueprint(engine_hb_bp)
    app.register_blueprint(proxy_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(user_state_bp)
    app.register_blueprint(presets_bp)
    app.register_blueprint(workflow_shares_bp)
    app.register_blueprint(dashboard_bp)
    app.logger.info("[Startup] Flowork Gateway blueprints registered.")
    app.logger.info("[Startup] Initializing ETL Exporter thread.")
    start_exporter_thread(app)


    @app.teardown_appcontext
    def remove_db_session(exception=None):
        """(English Hardcode) Close DB session at the end of the request."""
        gateway_db.session.remove()

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "Not Found"}), 404
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("Internal server error")
        return jsonify({"error": "Internal Server Error"}), 500
    from app.rl.limiter import init_rl_schema, allow as rl_allow
    with app.app_context():
        app.logger.info("[Startup] Initializing Rate Limiter schema (Roadmap 2.2)...")
        init_rl_schema()
    USER_RATE = float(os.getenv("USER_RATE", "5"))
    USER_BURST = float(os.getenv("USER_BURST", "20"))
    ENGINE_RATE = float(os.getenv("ENGINE_RATE", "20"))
    ENGINE_BURST = float(os.getenv("ENGINE_BURST", "100"))
    @app.before_request
    def _apply_rl():
        if request.path.startswith("/health") or request.path.startswith("/metrics"):
            return
        if "enqueue" in request.path:
            body = (request.get_json(silent=True) or {})
            if body:
                uid = body.get("user_id","anon")
                eid = body.get("engine_id","default")
                ok1, ra1 = rl_allow(f"user:{uid}", USER_RATE, USER_BURST)
                ok2, ra2 = rl_allow(f"engine:{eid}", ENGINE_RATE, ENGINE_BURST)
                if not (ok1 and ok2):
                    retry_after = max(ra1, ra2, 1)
                    resp = jsonify({"error":"rate_limited","retry_after": retry_after})
                    resp.status_code = 429
                    resp.headers["Retry-After"] = str(retry_after)
                    app.logger.warning(f"[RateLimit] 429 for user:{uid} or engine:{eid} on path {request.path}")
                    return resp
    app.logger.info("[Startup] Flowork Gateway initialized successfully.")
    return app
