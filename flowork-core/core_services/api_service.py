########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\core_services\api_service.py total lines 57 
########################################################################

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
import logging
from ..models.database_service import DatabaseService
import multiprocessing
logger = logging.getLogger(__name__)
class CoreAPIService:
    def __init__(self, db_service: DatabaseService, job_queue: multiprocessing.Queue):
        logger.info("Initializing Core API Service...") # English Hardcode
        self.app = Flask(__name__)
        CORS(self.app)
        self.db_service = db_service
        self.job_queue = job_queue
        self.dashboard = self.setup_dashboard(self.app)
        self.register_routes()
    def register_routes(self):
        @self.app.route("/health", methods=["GET"])
        def health_check():
            """
            Endpoint health check dasar untuk Docker.
            """
            try:
                self.db_service.session.execute(self.db_service.text("SELECT 1"))
                db_status = "connected" # English Hardcode
            except Exception as e:
                logger.warning(f"[Health Check] Database check failed: {e}") # English Hardcode
                db_status = "disconnected" # English Hardcode
            return jsonify({"status": "healthy", "database": db_status}), 200 # English Hardcode
        logger.info("Core API routes registered.") # English Hardcode
    def setup_dashboard(self, flask_app):
        try:
            logger.info("Setting up Flask-MonitoringDashboard...") # English Hardcode
            import flask_monitoringdashboard as dashboard
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'dashboard.cfg')
            dashboard.config.init_from(file=config_path)
            dashboard.bind(flask_app)
            logger.info(f"Dashboard bound. Access at http://localhost:5001") # English Hardcode
            return dashboard
        except ImportError:
            logger.warning("flask_monitoringdashboard not installed. Dashboard will be disabled.") # English Hardcode
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Flask-MonitoringDashboard: {e}", exc_info=True) # English Hardcode
            return None
    def run(self, host: str, port: int):
        try:
            logger.info(f"Starting Core API Service on {host}:{port}") # English Hardcode
            self.app.run(host=host, port=port, use_reloader=False)
        except Exception as e:
            logger.critical(f"Core API Service failed to start: {e}", exc_info=True) # English Hardcode
