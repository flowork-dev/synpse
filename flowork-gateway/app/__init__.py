#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\__init__.py JUMLAH BARIS 186 
#######################################################################

import os
import threading
import logging
import json
import re # <-- PERBAIKAN DITAMBAHKAN DI SINI
from flask import Flask, jsonify, request, current_app
from dotenv import load_dotenv
from app.config import Config
from app.extensions import db, migrate, socketio, compress, metrics, cors
from app.globals import load_servers, perform_health_checks
from app.sockets import register_socket_handlers
from app.models import (
    User,
    RegisteredEngine,
    Plan,
    Capability,
    PlanPrice,
    Subscription,
    UserBackup,
    GloballyDisabledComponent,
    AdminUser,
    Role,
    Permission,
    AuditLog,
    Preset,
    PresetVersion,
    Workflow,
    WorkflowShare,
    Variable,
    State, # Pastikan State diimpor
    ScheduledTask,
    ExecutionMetric,
    MarketplaceSubmission,
    FeatureFlag,
    EngineShare
)
class JsonFormatter(logging.Formatter):
    """Formats log records as JSON strings.""" # English Hardcode
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt), # English Hardcode
            "level": record.levelname, # English Hardcode
            "message": record.getMessage(), # English Hardcode
            "source": "flowork-gateway", # English Hardcode
        }
        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info) # English Hardcode
        if hasattr(record, 'pathname'): # Add source file info if available
            log_record['pathname'] = record.pathname # English Hardcode
            log_record['lineno'] = record.lineno # English Hardcode
        return json.dumps(log_record)
def ensure_sqlite_db_path_exists(app_config):
    """
    Ensures the directory for the SQLite database file exists.
    Handles various path formats correctly.
    """ # English Hardcode
    db_uri = app_config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite:///"): # English Hardcode
        db_path_str = None
        if re.match(r"sqlite:///[a-zA-Z]:[/\\]", db_uri, re.IGNORECASE): # English Hardcode
            db_path_str = db_uri[10:].replace('/', os.sep) # English Hardcode
        elif db_uri.startswith("sqlite:////"): # English Hardcode
            db_path_str = db_uri[9:] # Keep the leading / for absolute path # English Hardcode
        else:
             db_path_str = db_uri[10:] # English Hardcode
             basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) # English Hardcode
             db_path_str = os.path.join(basedir, db_path_str) # English Hardcode
        if db_path_str:
            db_dir = os.path.dirname(os.path.abspath(db_path_str))
            if db_dir and not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                    print(f"[Gateway Init] Created missing database directory: {db_dir}") # English Hardcode
                except Exception as e:
                    print(f"[Gateway Init] CRITICAL: Failed to create database directory {db_dir}: {e}") # English Hardcode
        else:
            print(f"[Gateway Init] WARNING: Could not determine database directory from URI: {db_uri}") # English Hardcode
def create_app(config_class=Config):
    """Creates and configures the Flask application.""" # English Hardcode
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(APP_DIR, "..", ".env") # English Hardcode
    load_dotenv(dotenv_path)
    app = Flask(__name__)
    app.config.from_object(config_class)
    ensure_sqlite_db_path_exists(app.config) # English Hardcode
    if app.logger.hasHandlers():
        app.logger.handlers.clear()
    json_handler = logging.StreamHandler() # Log to stdout/stderr # English Hardcode
    json_handler.setFormatter(JsonFormatter())
    app.logger.addHandler(json_handler)
    app.logger.setLevel(logging.INFO) # Set default level to INFO # English Hardcode
    logging.getLogger("werkzeug").setLevel(logging.ERROR) # English Hardcode
    logging.getLogger("socketio").setLevel(logging.ERROR) # English Hardcode
    logging.getLogger("engineio").setLevel(logging.ERROR) # English Hardcode
    app.logger.info("Structured JSON logging is now active for the Gateway.") # English Hardcode
    db.init_app(app)
    if "sqlite" in app.config.get("SQLALCHEMY_DATABASE_URI", ""): # English Hardcode
        with app.app_context(): # (COMMENT) Need app context to access db.engine
            try:
                with db.engine.connect() as connection:
                    connection.execute(db.text("PRAGMA journal_mode=WAL;")) # English Hardcode
                    connection.commit()
                app.logger.info("[Gateway Init] SQLite journal_mode successfully set to WAL.") # English Hardcode
            except Exception as e:
                app.logger.error(f"[Gateway Init] Failed to set SQLite journal_mode to WAL: {e}") # English Hardcode
    migrate.init_app(app, db) # Migrations for SQLite # English Hardcode
    socketio.init_app(app, async_mode="eventlet", cors_allowed_origins="*") # English Hardcode
    compress.init_app(app)
    allowed_origins = [
        "https://flowork.cloud",       # GUI Utama # English Hardcode
        "https://momod.flowork.cloud", # GUI Momod # English Hardcode
        "http://localhost:5173",       # Vue GUI dev (local) # English Hardcode
        "http://localhost:8002",       # Momod GUI dev (local) # English Hardcode
        "http://127.0.0.1:5173",       # Alternative local GUI host # English Hardcode
        "http://127.0.0.1:8002",       # Alternative local Momod host # English Hardcode
    ]
    gateway_api_origin = os.getenv("GATEWAY_API_URL") # English Hardcode
    if gateway_api_origin:
        try:
             from urllib.parse import urlparse
             parsed_origin = urlparse(gateway_api_origin)
             origin_str = f"{parsed_origin.scheme}://{parsed_origin.netloc}" # English Hardcode
             if origin_str not in allowed_origins:
                 allowed_origins.append(origin_str)
        except Exception:
             app.logger.warning(f"Could not parse GATEWAY_API_URL for CORS: {gateway_api_origin}") # English Hardcode
    cors.init_app(
        app,
        resources={
            r"/api/*": {"origins": allowed_origins}, # English Hardcode (Kode Asli)
            r"/api/v1/*": {"origins": allowed_origins} # English Hardcode (PENAMBAHAN KODE)
        },
        supports_credentials=True # Allow cookies/auth headers # English Hardcode
    )
    app.logger.info(f"CORS configured to allow origins: {', '.join(allowed_origins)}") # English Hardcode
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug: # English Hardcode
        metrics.init_app(app)
    with app.app_context():
        from app.routes.auth import auth_bp
        from app.routes.user import user_bp
        from app.routes.engine import engine_bp
        from app.routes.dashboard import dashboard_bp
        from app.routes.system import system_bp
        from app.routes.shares import shares_bp
        from app.routes.workflow_shares import workflow_shares_bp
        from app.routes.user_state import user_state_bp
        app.register_blueprint(auth_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(engine_bp)
        app.register_blueprint(dashboard_bp)
        app.register_blueprint(system_bp)
        app.register_blueprint(shares_bp)
        app.register_blueprint(workflow_shares_bp)
        app.register_blueprint(user_state_bp)
        from app.routes.proxy import proxy_bp
        app.register_blueprint(proxy_bp)
        register_socket_handlers(app)
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug: # English Hardcode
            if not hasattr(app, 'health_check_thread_started'): # English Hardcode
                 health_thread = threading.Thread(
                     target=perform_health_checks, args=(app,), daemon=True
                 )
                 health_thread.start()
                 app.health_check_thread_started = True # English Hardcode
                 app.logger.info("Background health check thread started.") # English Hardcode
            else:
                 app.logger.info("Background health check thread already running.") # English Hardcode
        @app.route("/")
        def index():
            return jsonify(message="Flowork Gateway API is operational."), 200 # English Hardcode
        @app.errorhandler(404)
        def not_found(e):
            app.logger.warning(f"404 Not Found: {request.path}") # English Hardcode
            return jsonify(error="Resource not found"), 404 # English Hardcode
        @app.errorhandler(500)
        def internal_error(e):
             app.logger.error(f"500 Internal Server Error: {e} for path {request.path}", exc_info=True) # English Hardcode
             return jsonify(error="Internal server error"), 500 # English Hardcode
    return app
