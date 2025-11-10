########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\security\guards.py total lines 50 
########################################################################

import os
from functools import wraps
from flask import request, jsonify, current_app, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt
def gateway_token_required(f):
    """
    Decorator ensuring the request has a valid 'X-Gateway-Secret' header.
    Used for internal service-to-service calls (e.g., Core -> Gateway).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        secret_token = request.headers.get('X-Gateway-Secret')
        if not secret_token:
             secret_token = request.headers.get('X-API-Key')
        expected_token = current_app.config.get('GATEWAY_SECRET_TOKEN') or os.environ.get('GATEWAY_SECRET_TOKEN')
        if not expected_token:
            current_app.logger.error("[Auth Guard] GATEWAY_SECRET_TOKEN not configured on server.")
            return jsonify({"error": "Internal server configuration error"}), 500
        if not secret_token or secret_token != expected_token:
            current_app.logger.warning(f"[Auth Guard] Invalid or missing gateway token from {request.remote_addr}")
            return jsonify({"error": "Forbidden: Invalid Gateway Token"}), 403
        return f(*args, **kwargs)
    return decorated_function
def admin_token_required(f):
    """
    Decorator ensuring the request has a valid Admin JWT with 'is_admin': True.
    Used for sensitive admin-only endpoints.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("is_admin") is True:
                g.admin_claims = claims
                return f(*args, **kwargs)
            else:
                current_app.logger.warning(f"[Auth Guard] JWT present but 'is_admin' is False from {request.remote_addr}")
                return jsonify({"error": "Forbidden: Administrator access required"}), 403
        except Exception as e:
            current_app.logger.warning(f"[Auth Guard] Admin token verification failed: {e}")
            return jsonify({"error": "Unauthorized: Invalid or expired admin token"}), 401
    return decorated_function
internal_auth_required = gateway_token_required
