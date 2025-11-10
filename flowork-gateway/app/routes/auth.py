########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\auth.py total lines 95 
########################################################################

import jwt
import datetime
import threading
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import User, Subscription
from ..extensions import db
from ..helpers import (
    get_request_data, # (FIXED) This will now be imported from File 87
    crypto_auth_required,
    get_user_permissions, # (FIXED) Was 'calculate_effective_permissions'
    inject_user_data_to_core, # (FIXED) Was '_inject_user_data_to_core'
)
auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    (REMASTERED) Stubbed endpoint. Registration is handled locally/cryptographically by the client.
    """
    return jsonify({"error": "Not Implemented: Registration is handled by the client identity generation."}), 501 # English Hardcode
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    (REMASTERED) Stubbed endpoint. Login is handled via cryptographic challenge (see /api/v1/auth/profile).
    """
    return jsonify({"error": "Not Implemented: Login is handled via cryptographic challenge."}), 501 # English Hardcode
@auth_bp.route("/logout", methods=["POST"])
@crypto_auth_required # Sebaiknya di-autentikasi juga
def handle_logout():
    current_user = g.user # Get user from Flask's global context
    """
    Handles a logout request. In a stateless crypto-auth system,
    this mainly serves to acknowledge the client's session termination.
    """
    current_app.logger.info(f"[Gateway Auth] Received logout request from user {current_user.public_address[:10]}...") # English log
    return jsonify(
        {"message": "Logout acknowledged by Gateway."} # English Hardcode
    )
@auth_bp.route("/profile", methods=["GET"])
@crypto_auth_required # Ini adalah endpoint "login"
def get_profile():
    current_user = g.user # Get user from Flask's global context
    """
    (REMASTERED) Mengembalikan profil user berdasarkan verifikasi tanda tangan kripto.
    Ini adalah endpoint "login" yang sebenarnya.
    """
    if not current_user:
        current_app.logger.warning("[Gateway Auth Profile] Access denied: User object not found after crypto auth.") # English log
        return jsonify({"error": "Authentication failed or user not found."}), 401 # English Hardcode
    try:
        db.session.refresh(current_user)
        if hasattr(current_user, 'subscriptions') and current_user.subscriptions: # Check list
            if current_user.subscriptions and current_user.subscriptions[0].expires_at:
                db.session.refresh(current_user.subscriptions[0]) # Refresh the specific subscription
    except Exception as e:
        current_app.logger.error(f"[Gateway Auth Profile] Failed to refresh user/subscription data: {e}") # English log
        db.session.rollback()
    permissions_data = get_user_permissions(current_user)
    user_tier = permissions_data.get("tier")
    effective_permissions = permissions_data.get("capabilities")
    expires_at = None
    if hasattr(current_user, 'subscriptions') and current_user.subscriptions: # Check list
        if current_user.subscriptions and current_user.subscriptions[0] and current_user.subscriptions[0].expires_at:
            expires_at = current_user.subscriptions[0].expires_at
    effective_username = current_user.username
    if effective_username.startswith("0x") and '@' in effective_username: # (English Hardcode) Fix for placeholder email showing as username
        effective_username = f"{current_user.public_address[:6]}...{current_user.public_address[-4:]}"
    elif effective_username.startswith("user_") and effective_username.endswith("..."):
        effective_username = current_user.public_address
    elif '@' in effective_username: # Jika username lama adalah email
        effective_username = current_user.public_address
    user_data_response = {
        "user_id": current_user.public_address, # ID utama adalah public address
        "email": current_user.email,
        "username": effective_username, # (PERBAIKAN) Gunakan username yang sudah divalidasi
        "public_address": current_user.public_address,
        "tier": user_tier,
        "permissions": effective_permissions,
        "license_expires_at": expires_at,
    }
    def inject_with_context(app, user_object):
        with app.app_context():
            inject_user_data_to_core(user_object) # (FIXED) Was '_inject_user_data_to_core'
    app_context = current_app._get_current_object()
    threading.Thread(
        target=inject_with_context, args=(app_context, current_user)
    ).start()
    current_app.logger.info(f"[Gateway Auth Profile] Profile data sent for user {current_user.public_address[:10]}...") # English log
    return jsonify(user_data_response)
