########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\engine\heartbeat_api.py total lines 75 
########################################################################

print("DEBUG: --- LOADING PATCHED HEARTBEAT_API V43 (IF YOU SEE THIS, IT WORKED) ---")
from flask import Blueprint, request, jsonify, current_app
import os
from app.extensions import db
from app.models import RegisteredEngine as Engine
engine_hb_bp = Blueprint('engine_heartbeat', __name__, url_prefix='/internal/engine')
@engine_hb_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    """
    Called by a Core Engine to report it is alive.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    engine_id = data.get('engine_id')
    if not engine_id:
        return jsonify({"error": "engine_id is required"}), 400
    try:
        engine = Engine.query.filter_by(id=engine_id).first()
        if engine:
            engine.status = 'online'
            from datetime import datetime, timezone
            engine.last_seen = datetime.now(timezone.utc)
            db.session.commit()
        else:
            current_app.logger.warning(f"Heartbeat received for unknown engine: {engine_id}")
        return jsonify({"status": "acknowledged"}), 200
    except Exception as e:
        current_app.logger.error(f"Heartbeat failed for engine {engine_id}: {e}", exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500
@engine_hb_bp.route('/cleanup_stale', methods=['POST'])
def cleanup_stale_engines():
    """
    Marks engines that haven't sent a heartbeat recently as 'offline'.
    """
    auth = request.headers.get("X-Internal-Auth")
    if auth != os.getenv("GATEWAY_SECRET_TOKEN"):
         return jsonify({"error": "Unauthorized"}), 401
    ttl_seconds = int(os.getenv("ENGINE_HB_TTL", "60"))
    try:
        if db.engine.dialect.name == 'sqlite':
            sql = f"""
            UPDATE registered_engines
            SET status = 'offline'
            WHERE status = 'online' AND STRFTIME('%s', 'now') - STRFTIME('%s', last_seen) > {ttl_seconds};
            """
            db.session.execute(db.text(sql))
            db.session.commit()
        elif db.engine.dialect.name == 'postgresql':
            sql = f"""
            UPDATE registered_engines
            SET status = 'offline'
            WHERE status = 'online' AND last_seen < NOW() - INTERVAL '{ttl_seconds} seconds';
            """
            db.session.execute(db.text(sql))
            db.session.commit()
        current_app.logger.info(f"Engine cleanup job run successfully.")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        current_app.logger.error(f"Engine cleanup job failed: {e}", exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500
