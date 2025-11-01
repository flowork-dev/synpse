#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\helpers.py JUMLAH BARIS 284 
#######################################################################

import os
import jwt
import datetime
import requests
import json
import hashlib
import secrets # Ditambahkan untuk auto-register user
from functools import wraps
from flask import request, jsonify, current_app
import hmac
from .models import User, Capability, AdminUser, Role, Subscription, RegisteredEngine, EngineShare
from .extensions import db
from .globals import active_engine_sessions, engine_session_map, get_next_core_server, engine_url_map
from eth_account.messages import encode_defunct
from web3.auto import w3
from werkzeug.security import generate_password_hash
def engine_token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        expected_token = os.getenv("GATEWAY_SECRET_TOKEN")
        provided_token = request.headers.get("X-API-Key")
        if not expected_token:
            return f(*args, **kwargs)
        if not provided_token or not hmac.compare_digest(
            provided_token, expected_token
        ):
            current_app.logger.warning(f"Unauthorized internal API access attempt to {request.path}") # English Hardcode
            return (
                jsonify({"error": "Unauthorized: Invalid or missing engine token."}), # English Hardcode
                401,
            )
        return f(*args, **kwargs)
    return decorated
def get_active_engine_for_user(user_id):
    """
    (PERBAIKAN) Gets the engine_id for a given user_id.
    Prioritizes the user's own active engine session.
    If none is found, checks for active shared engines.
    Returns the first active engine_id found (owned or shared), or None.
    """
    if user_id in active_engine_sessions:
        user_sids = active_engine_sessions[user_id]
        if user_sids:
            for active_sid in user_sids:
                if active_sid in engine_session_map:
                     engine_info = engine_session_map[active_sid]
                     owned_engine_id = engine_info.get("engine_id")
                     if owned_engine_id and engine_info.get("user_id") == user_id:
                         current_app.logger.info(f"[Helper] Found active *owned* engine session for user {user_id}: engine {owned_engine_id}") # English Log
                         return owned_engine_id
    current_app.logger.warning(f"[Helper] No active *owned* engine session for user {user_id}. Checking shared engines...") # English Log
    try:
        shared_engine_records = EngineShare.query.filter_by(shared_with_user_id=user_id).all()
        shared_engine_ids = [s.engine_id for s in shared_engine_records]
        if shared_engine_ids:
            for shared_id in shared_engine_ids:
                if shared_id in engine_url_map:
                    current_app.logger.info(f"[Helper] Found active *shared* engine for user {user_id}: engine {shared_id}") # English Log
                    return shared_id # Kembalikan ID engine shared yang aktif pertama
    except Exception as e:
        current_app.logger.error(f"[Helper] Error querying shared engines for user {user_id}: {e}") # English Log
    current_app.logger.warning(f"[Helper] No active owned or shared engine found for user {user_id}.") # English Log
    return None # Tidak ada engine aktif (owned maupun shared) yang ditemukan
def get_request_data():
    """Parses JSON data from request body, form, or raw data."""
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    if not data:
        try:
            raw_data = request.get_data()
            if raw_data:
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
                    pass # Keep data as None or empty dict
        except Exception:
             pass # Ignore errors decoding raw data
    return data if data is not None else {}
def crypto_auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        signature = request.headers.get("X-Signature")
        public_address = request.headers.get("X-User-Address")
        message = request.headers.get("X-Signed-Message")
        if not all([signature, public_address, message]):
            return jsonify({"error": "Missing signature headers"}), 401 # English Hardcode
        try:
            encoded_message = encode_defunct(text=message)
            recovered_address = w3.eth.account.recover_message(
                encoded_message, signature=signature
            )
            if recovered_address.lower() != public_address.lower():
                current_app.logger.warning(f"[Crypto Auth] Invalid signature. Expected {public_address}, got {recovered_address}") # English Hardcode
                return jsonify({"error": "Invalid signature"}), 401 # English Hardcode
            current_user = User.query.filter(
                User.public_address.ilike(public_address)
            ).first()
            if not current_user:
                current_app.logger.info(f"[Auth] New public_address '{public_address}' detected. Auto-registering user.") # English Hardcode
                placeholder_password = generate_password_hash(secrets.token_urlsafe(32), method="pbkdf2:sha256")
                new_user = User(
                    username=public_address, # USERNAME = PUBLIC ADDRESS
                    email=f"{public_address.lower()}@flowork.crypto", # Email placeholder unik
                    password_hash=placeholder_password,
                    status="active", # English Hardcode
                    public_address=public_address
                )
                db.session.add(new_user)
                db.session.flush() # Ambil user.id
                new_subscription = Subscription(user_id=new_user.id, tier="architect") # Default ke architect
                db.session.add(new_subscription)
                db.session.commit()
                current_app.logger.info(f"[Auth] Auto-registration complete for user ID: {new_user.id}") # English Hardcode
                current_user = new_user
        except Exception as e:
            current_app.logger.error(f"Crypto auth failed: {e}") # English Hardcode
            db.session.rollback()
            return jsonify({"error": "Signature verification failed", "details": str(e)}), 401 # English Hardcode
        kwargs['current_user'] = current_user
        return f(*args, **kwargs)
    return decorated
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            try:
                token = request.headers["Authorization"].split(" ")[1]
            except IndexError:
                return jsonify({"error": "Malformed token header"}), 401 # English Hardcode
        if not token:
            return jsonify({"error": "Token is missing!"}), 401 # English Hardcode
        try:
            secret_key = current_app.config["SECRET_KEY"]
            if not secret_key:
                current_app.logger.critical(
                    "[Gateway FATAL] JWT_SECRET_KEY is not configured in .env! Authentication will fail." # English Hardcode
                )
                return jsonify({"error": "Server configuration error"}), 500 # English Hardcode
            data = jwt.decode(token, secret_key, algorithms=["HS256"])
            current_user = User.query.filter_by(id=data["user_id"]).first()
            if not current_user:
                return jsonify({"error": "User for token not found"}), 401 # English Hardcode
            kwargs['current_user'] = current_user
        except jwt.ExpiredSignatureError:
             return jsonify({"error": "Token has expired!"}), 401 # English Hardcode
        except jwt.InvalidTokenError as e:
            current_app.logger.warning(f"Invalid token received: {e}") # English Hardcode
            return jsonify({"error": "Token is invalid!", "details": str(e)}), 401 # English Hardcode
        except Exception as e:
            current_app.logger.error(f"Token validation error: {e}") # English Hardcode
            return (
                jsonify({"error": "Token validation failed!", "details": str(e)}), # English Hardcode
                401,
            )
        return f(*args, **kwargs) # Pass current_user via kwargs
    return decorated
def admin_token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            try:
                token = request.headers["Authorization"].split(" ")[1]
            except IndexError:
                return jsonify({"error": "Malformed token header"}), 401 # English Hardcode
        if not token:
            return jsonify({"error": "Token is missing!"}), 401 # English Hardcode
        try:
            secret_key = os.getenv("MOMOD_JWT_SECRET_KEY", current_app.config["SECRET_KEY"])
            data = jwt.decode(token, secret_key, algorithms=["HS256"])
            is_admin_claim = data.get("is_admin", False)
            admin_id = data.get("admin_id")
            if not is_admin_claim or not admin_id:
                return token_required(f)(*args, **kwargs)
            current_admin = AdminUser.query.filter_by(id=admin_id).first()
            if not current_admin:
                return jsonify({"error": "Admin user for token not found"}), 401 # English Hardcode
            kwargs['current_admin'] = current_admin
            kwargs['admin_permissions'] = data.get("permissions", [])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Admin token has expired!"}), 401 # English Hardcode
        except jwt.InvalidTokenError as e:
            current_app.logger.warning(f"Invalid admin token: {e}")
            try:
                return token_required(f)(*args, **kwargs)
            except Exception: # Jika user token check juga fails
                 return jsonify({"error": "Token is invalid (Admin or User)!"}), 401 # English Hardcode
        except Exception as e:
            current_app.logger.error(f"Admin token validation error: {e}")
            return jsonify({"error": "Admin token validation failed!"}), 401 # English Hardcode
        return f(*args, **kwargs)
    return decorated
def get_all_plans_with_capabilities():
    current_app.logger.debug("[Gateway] Open Core Mode: Bypassing plan capability cache/DB lookup.") # English Hardcode
    try:
        all_caps = db.session.query(Capability.id).all()
        all_cap_ids = [c[0] for c in all_caps]
        return {
            "free": all_cap_ids,
            "builder": all_cap_ids,
            "creator": all_cap_ids,
            "architect": all_cap_ids,
            "superadmin": all_cap_ids # Tier internal untuk momod
        }
    except Exception as e:
        current_app.logger.error(f"[Gateway] Failed to fetch capabilities for Open Core mode: {e}") # English Hardcode
        return {
            "architect": [
                "basic_execution", "core_services", "unlimited_api", "preset_versioning",
                "ai_provider_access", "ai_local_models", "ai_copilot", "time_travel_debugger",
                "ai_architect", "core_compiler", "engine_management", "cloud_sync"
            ]
        }
def calculate_effective_permissions(user):
    """
    (REMASTERED - OPEN CORE)
    Selalu mengembalikan tier 'architect' dan semua kapabilitas.
    """
    if not user:
        return "architect", [] # Default
    user_tier = "architect" # Selalu architect di Open Core
    try:
        all_caps = db.session.query(Capability.id).all()
        final_permissions = [c[0] for c in all_caps]
        current_app.logger.info(
            f"[Permissions - Open Core] User '{user.email}' granted '{user_tier}' tier with all capabilities: {final_permissions}" # English Hardcode
        )
        return user_tier, final_permissions
    except Exception as e:
        current_app.logger.error(
            f"Failed to fetch capabilities for user {user.id} in Open Core mode: {e}" # English Hardcode
        )
        fallback_permissions = [
            "basic_execution", "core_services", "unlimited_api", "preset_versioning",
            "ai_provider_access", "ai_local_models", "ai_copilot", "time_travel_debugger",
            "ai_architect", "core_compiler", "engine_management", "cloud_sync"
        ]
        return user_tier, fallback_permissions
def _inject_user_data_to_core(user_data):
    """
    (Helper internal) Mengirim data profil user ke Core Engine
    setelah login/autentikasi berhasil.
    """
    core_server_url = get_next_core_server() # Tries to find a healthy one
    if not core_server_url:
        current_app.logger.warning(
            "[Gateway] No healthy Core Servers available to inject user data." # English Hardcode
        )
        return
    payload_to_core = {
        "user_id": user_data.get("user_id"), # Ini akan berisi public_address
        "email": user_data.get("email"),
        "username": user_data.get("username"),
        "tier": user_data.get("tier"),
        "capabilities": user_data.get("permissions", []),
        "license_expires_at": user_data.get("license_expires_at"),
    }
    api_key = os.getenv("GATEWAY_SECRET_TOKEN")
    headers = {"X-API-Key": api_key} if api_key else {}
    target_url = f"{core_server_url}/api/v1/uistate/generic/current_user_data" # Endpoint di Core
    try:
        current_app.logger.info(
            f"[Gateway] Injecting user data for {user_data.get('email')} (Tier: {user_data.get('tier')}) to Core Engine at {core_server_url}" # English Hardcode
        )
        response = requests.post(
            target_url, json=payload_to_core, headers=headers, timeout=5
        )
        response.raise_for_status() # Error jika status 4xx atau 5xx
        current_app.logger.info(
            f"[Gateway] User data injection to Core Engine was successful." # English Hardcode
        )
    except requests.exceptions.RequestException as e:
        current_app.logger.error(
            f"[Gateway] Failed to inject user data to Core Engine: {e}" # English Hardcode
        )
