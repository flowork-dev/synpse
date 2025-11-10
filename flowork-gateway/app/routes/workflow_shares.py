########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\workflow_shares.py total lines 184 
########################################################################

from flask import Blueprint, jsonify, request, current_app, g
import secrets
import datetime
import requests
import os
from sqlalchemy.orm import joinedload
from ..extensions import db
from ..models import User, Workflow, WorkflowShare, Preset
from ..helpers import crypto_auth_required, get_request_data, find_active_engine_session
from ..globals import globals_instance
workflow_shares_bp = Blueprint("workflow_shares", __name__)
def _check_preset_exists_in_core(user_id, preset_name):
    """
    Helper untuk memeriksa keberadaan preset di Core Engine via API.
    Menggunakan user_id internal dari database Gateway.
    """
    app = current_app._get_current_object()
    core_user_id = None
    user = db.session.get(User, user_id) # (FIX) Ambil user dari session saat ini
    if user:
        core_user_id = user.public_address
    else:
        app.logger.warning(f"[_check_preset_exists_in_core] User ID {user_id} not found in Gateway DB.") # English Log
        return False
    if not core_user_id:
        app.logger.warning(f"[_check_preset_exists_in_core] User {user_id} has no public_address set.") # English Log
        return False
    active_session = find_active_engine_session(db.session, user_id)
    active_engine_id = active_session.engine.engine_id if active_session and active_session.engine else None
    core_server_url = globals_instance.engine_manager.engine_url_map.get(active_engine_id)
    if not core_server_url:
        app.logger.warning(f"[_check_preset_exists_in_core] No active Core Engine URL found for user {user_id}.") # English Log
        return False
    target_url = f"{core_server_url}/api/v1/presets/{preset_name}/exists"
    api_key = os.getenv("GATEWAY_SECRET_TOKEN")
    headers = {"X-API-Key": api_key} if api_key else {}
    headers["X-Flowork-User-ID"] = core_user_id
    headers["X-Flowork-Engine-ID"] = active_engine_id
    try:
        app.logger.info(f"[_check_preset_exists_in_core] Checking core at {target_url} for preset '{preset_name}' (User: {core_user_id[:8]}...)", "INFO") # English Log
        response = requests.get(target_url, headers=headers, timeout=5)
        exists = response.status_code == 200 and response.json().get("exists")
        app.logger.info(f"[_check_preset_exists_in_core] Core response: Status={response.status_code}, Exists={exists}", "INFO") # English Log
        return exists
    except requests.exceptions.RequestException as e:
        app.logger.error(f"[_check_preset_exists_in_core] Error contacting Core Engine: {e}", "ERROR") # English Log
        return False
@workflow_shares_bp.route("/api/v1/workflows/<string:workflow_name>/shares", methods=["GET"])
@crypto_auth_required
def get_workflow_shares(current_user, workflow_name):
    preset_exists_in_core = _check_preset_exists_in_core(current_user.id, workflow_name)
    if not preset_exists_in_core:
        current_app.logger.warning(f"User {current_user.id} tried to get shares for preset '{workflow_name}' which does not exist in Core.") # English Log
        return jsonify({"error": "Preset not found in the active engine."}), 404 # English Hardcode
    workflow = Workflow.query.filter_by(user_id=current_user.id, name=workflow_name).first() # (FIX) 'user_id' dan 'name'
    if not workflow:
        current_app.logger.info(f"Preset '{workflow_name}' exists in Core, but no Workflow entry in Gateway yet. Returning empty share list.") # English Log
        return jsonify([])
    shares = WorkflowShare.query.filter_by(workflow_id=workflow.id).order_by(WorkflowShare.created_at.desc()).all()
    share_list = [
        {
            "share_id": share.id, # (FIX) Gunakan 'id'
            "share_token": share.share_token,
            "share_url": f"https://flowork.cloud/shared/{share.share_token}",
            "permission_level": share.permissions, # (FIX) 'permissions'
            "link_name": share.link_name or f"Link {i+1}",
            "created_at": share.created_at.isoformat() if share.created_at else None
        } for i, share in enumerate(shares)
    ]
    return jsonify(share_list)
@workflow_shares_bp.route("/api/v1/workflows/<string:workflow_name>/shares", methods=["POST"])
@crypto_auth_required
def create_workflow_share(current_user, workflow_name):
    preset_exists_in_core = _check_preset_exists_in_core(current_user.id, workflow_name)
    if not preset_exists_in_core:
        current_app.logger.warning(f"User {current_user.id} tried to share preset '{workflow_name}' which does not exist in Core.") # English Log
        return jsonify({"error": "Preset not found in the active engine. Cannot create share link."}), 404 # English Hardcode
    workflow = Workflow.query.filter_by(user_id=current_user.id, name=workflow_name).first()
    if not workflow:
        current_app.logger.info(f"Creating new Workflow entry for preset '{workflow_name}' to enable sharing (verified in Core).") # English Log
        workflow = Workflow(
            user_id=current_user.id, # (FIX) 'user_id'
            name=workflow_name, # (FIX) 'name'
        )
        db.session.add(workflow)
        db.session.flush()
    data = get_request_data()
    permission_level = data.get("permission_level", "read") # (FIX) 'read'
    link_name = data.get("link_name")
    if permission_level not in ["read", "read_write"]: # (FIX) Sesuaikan dengan model
        return jsonify({"error": "Invalid permission level."}), 400 # English Hardcode
    try:
        share_token = secrets.token_urlsafe(16)
        new_share = WorkflowShare(
            workflow_id=workflow.id, # (FIX) 'workflow_id' (Integer)
            share_token=share_token,
            permissions=permission_level, # (FIX) 'permissions'
            link_name=link_name,
            owner_id=current_user.id, # (FIX) 'owner_id'
            user_id=current_user.id # (FIX) 'user_id' (sementara, ini salah)
        )
        db.session.add(new_share)
        db.session.commit()
        current_app.logger.info(f"User {current_user.id} created share link for workflow '{workflow_name}' (WF ID: {workflow.id})") # English Log
        return jsonify({
            "message": "Share link created successfully.", # English Hardcode
            "share_id": new_share.id,
            "share_token": new_share.share_token,
            "share_url": f"https://flowork.cloud/shared/{new_share.share_token}",
            "permission_level": new_share.permissions,
            "link_name": new_share.link_name,
            "created_at": new_share.created_at.isoformat() if new_share.created_at else None
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create share link for workflow '{workflow_name}': {e}", exc_info=True) # English Log
        return jsonify({"error": "Failed to create share link."}), 500 # English Hardcode
@workflow_shares_bp.route("/api/v1/workflow-shares/<string:share_id>", methods=["PUT"])
@crypto_auth_required
def update_workflow_share(current_user, share_id):
    share = db.session.query(WorkflowShare).join(Workflow, WorkflowShare.workflow_id == Workflow.id).filter(
        WorkflowShare.id == share_id,
        Workflow.user_id == current_user.id # (FIX) Cek 'user_id' di Workflow
    ).first()
    if not share:
        return jsonify({"error": "Share link not found or permission denied."}), 404 # English Hardcode
    data = get_request_data()
    new_permission = data.get("permission_level")
    if new_permission not in ["read", "read_write"]: # (FIX) Sesuaikan dengan model
        return jsonify({"error": "Invalid permission level."}), 400 # English Hardcode
    try:
        share.permissions = new_permission # (FIX) 'permissions'
        share.workflow.updated_at = db.func.now()
        db.session.commit()
        current_app.logger.info(f"User {current_user.id} updated permission for share {share_id} to '{new_permission}'") # English Log
        return jsonify({
            "message": "Permission updated successfully.", # English Hardcode
            "share_id": share.id,
            "permission_level": share.permissions
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update share permission for {share_id}: {e}") # English Log
        return jsonify({"error": "Failed to update permission."}), 500 # English Hardcode
@workflow_shares_bp.route("/api/v1/workflow-shares/<string:share_id>", methods=["DELETE"])
@crypto_auth_required
def delete_workflow_share(current_user, share_id):
    share = db.session.query(WorkflowShare).join(Workflow, WorkflowShare.workflow_id == Workflow.id).filter(
        WorkflowShare.id == share_id,
        Workflow.user_id == current_user.id # (FIX) Cek 'user_id' di Workflow
    ).first()
    if not share:
        return jsonify({"error": "Share link not found or permission denied."}), 404 # English Hardcode
    try:
        db.session.delete(share)
        db.session.commit()
        current_app.logger.info(f"User {current_user.id} deleted share link {share_id}") # English Log
        return jsonify({"status": "success", "message": "Share link deleted successfully."}), 200 # English Hardcode
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete share link {share_id}: {e}") # English Log
        return jsonify({"error": "Failed to delete share link."}), 500 # English Hardcode
@workflow_shares_bp.route("/api/v1/workflow-shares/resolve/<string:share_token>", methods=["GET"])
def resolve_share_token(share_token):
    share = db.session.query(WorkflowShare).options(
        joinedload(WorkflowShare.workflow).joinedload(Workflow.user) # (FIX) 'user'
    ).filter_by(share_token=share_token).first()
    if not share or not share.workflow or not share.workflow.user: # (FIX) 'user'
        return jsonify({"error": "Invalid or expired share token."}), 404 # English Hardcode
    preset_name = share.workflow.name # (FIX) 'name'
    owner_user_id = share.workflow.user_id # (FIX) 'user_id'
    return jsonify({
        "permission_level": share.permissions, # (FIX) 'permissions'
        "workflow_name": share.workflow.name, # (FIX) 'name'
        "owner_username": share.workflow.user.username, # (FIX) 'user'
        "owner_id": share.workflow.user.public_address, # (FIX) 'user'
        "preset_name": preset_name
    })
