########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\ops\health.py total lines 25 
########################################################################

"""
Provides the /health endpoint for Docker/Kubernetes health checks.
Crucially, this integrates with the drain service (Roadmap 4.5).
- If draining, return 503 Service Unavailable.
- If active, return 200 OK.
"""
from flask import Blueprint, jsonify
from .drain import is_draining
bp = Blueprint('health_bp', __name__)
@bp.route('/health', methods=['GET'])
def health_check():
    """
    Reports node health.
    - 200 OK: Node is active and accepting work.
    - 503 Service Unavailable: Node is draining and NOT accepting work.
    """
    if is_draining():
        return jsonify(status="draining"), 503
    return jsonify(status="active"), 200
