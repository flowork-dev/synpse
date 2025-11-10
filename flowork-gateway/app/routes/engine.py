########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\engine.py total lines 99 
########################################################################

from flask import Blueprint, request, jsonify, g, current_app
import uuid
import os
from app.extensions import db
from app.models import User, RegisteredEngine, EngineShare
from app.helpers import crypto_auth_required, get_db_session
from werkzeug.security import check_password_hash
engine_bp = Blueprint('engine_bp', __name__)
@engine_bp.route('/register', methods=['POST'])
@crypto_auth_required
def register_engine():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    engine_id = data.get('engine_id')
    name = data.get('name')
    description = data.get('description')
    if not engine_id or not name:
        return jsonify({"error": "engine_id and name are required"}), 400
    user = g.user
    existing_engine = RegisteredEngine.query.filter_by(id=engine_id).first()
    if existing_engine:
        if existing_engine.user_id == user.id:
            existing_engine.name = name
            existing_engine.description = description
            db.session.commit()
            current_app.logger.info(f"Engine {engine_id} re-registered/updated by owner {user.public_address}")
            return jsonify({
                "message": "Engine re-registered successfully",
                "token": existing_engine.token
            }), 200
        else:
            current_app.logger.warning(f"Engine ID {engine_id} already registered by another user.")
            return jsonify({"error": "Engine ID already in use by another user"}), 409
    new_engine = RegisteredEngine(
        id=engine_id,
        name=name,
        description=description,
        user_id=user.id
    )
    from werkzeug.security import generate_password_hash
    import secrets
    raw_token = f"eng_{secrets.token_hex(32)}"
    new_engine.engine_token_hash = generate_password_hash(raw_token)
    db.session.add(new_engine)
    db.session.commit()
    current_app.logger.info(f"New engine {engine_id} registered for user {user.public_address}")
    return jsonify({
        "message": "Engine registered successfully",
        "token": raw_token # Kembalikan raw token sekali saja
    }), 201
def engine_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session = get_db_session()
        token = request.headers.get('X-Engine-Token')
        if not token:
            current_app.logger.warning("[Engine Auth] Decorator failed: Missing X-Engine-Token header.") # English Hardcode
            return jsonify({"message": "Missing X-Engine-Token"}), 401 # English Hardcode
        all_engines = session.query(RegisteredEngine).all()
        engine = None
        for e in all_engines:
            if check_password_hash(e.engine_token_hash, token):
                engine = e
                break
        if not engine:
            current_app.logger.warning("[Engine Auth] Decorator failed: Invalid token received.") # English Hardcode
            return jsonify({"message": "Engine not found or invalid token"}), 401 # English Hardcode
        if engine.is_deleted:
             current_app.logger.warning(f"[Engine Auth] Decorator failed: Engine {engine.id} is marked as deleted.") # English Hardcode
             return jsonify({"message": "Engine is deleted"}), 401 # English Hardcode
        g.engine = engine
        current_app.logger.debug(f"[Engine Auth] Engine {engine.id} authenticated successfully.") # English Hardcode
        return f(*args, **kwargs)
    return decorated_function
@engine_bp.route('/get-auth-whitelist', methods=['GET'])
@engine_auth_required
def get_auth_whitelist():
    engine = g.engine
    if not engine:
        current_app.logger.error(f"[AuthZ] Whitelist endpoint reached but g.engine is not set.")
        return jsonify({"error": "Engine not found in context"}), 500
    try:
        owner_address = engine.owner.public_address
        guest_shares = engine.shares # (FIXED) Use 'shares' relationship from model
        guest_addresses = [share.user.public_address for share in guest_shares if share.user]
        whitelist = [owner_address] + guest_addresses
        final_whitelist = list(set(addr.lower() for addr in whitelist if addr))
        current_app.logger.info(f"Delivering auth whitelist for engine {engine.id}: {len(final_whitelist)} users")
        return jsonify({"whitelist": final_whitelist}), 200
    except Exception as e:
        current_app.logger.error(f"Error generating whitelist for engine {engine.id}: {e}", exc_info=True)
        return jsonify({"error": "Error generating whitelist"}), 500
