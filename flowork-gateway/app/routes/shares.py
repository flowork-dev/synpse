########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\routes\shares.py total lines 149 
########################################################################

from flask import Blueprint, jsonify, g, request, current_app # <-- START ADDED CODE (ROADMAP 5)
import logging
import secrets # <-- START ADDED CODE (FIX) - Diperlukan untuk generate_password_hash
from app.extensions import db, socketio # Note (English): Import socketio for PUSH
from app.models import User, RegisteredEngine, EngineShare
from app.helpers import crypto_auth_required # Note (English): Use the *real* crypto_auth from helpers.py
from web3.auto import w3 # <-- START ADDED CODE (FIX) - Import w3 langsung, konsisten dengan helpers.py
from werkzeug.security import generate_password_hash # <-- START ADDED CODE (FIX) - Diperlukan untuk user baru
shares_bp = Blueprint('shares_bp', __name__)
@shares_bp.route('/create', methods=['POST'])
@crypto_auth_required # Note (English): Secured with our crypto auth decorator
def create_share():
    """
    Creates a new 'share' for an engine or updates an existing one.
    Only the ENGINE OWNER can perform this action.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400 # English Hardcode
    engine_id_str = data.get('engine_id') # The engine_id (UUID string) to share
    share_with_address = data.get('share_with_address') # The public address of the guest user
    role = data.get('role', 'viewer') # The role to grant ('viewer', 'editor')
    if not engine_id_str or not share_with_address:
        return jsonify({"error": "engine_id and share_with_address are required"}), 400 # English Hardcode
    if role not in ['viewer', 'editor', 'admin']: # English Hardcode
        return jsonify({"error": "Invalid role. Must be 'viewer', 'editor', or 'admin'"}), 400 # English Hardcode
    owner_user = g.user
    if not owner_user:
        current_app.logger.error(f"[Shares] No authenticated user (g.user) in context.") # English Hardcode
        return jsonify({"error": "Authentication context not found"}), 500 # English Hardcode
    engine = RegisteredEngine.query.filter_by(engine_id=engine_id_str).first()
    if not engine:
        return jsonify({"error": "Engine not found"}), 404 # English Hardcode
    if engine.user_id != owner_user.id:
        current_app.logger.warning(f"[AuthZ] DENIED: User {owner_user.public_address} tried to share engine {engine_id_str} which they do not own.") # English Hardcode
        return jsonify({"error": "You are not the owner of this engine"}), 403 # English Hardcode
    try:
        checked_guest_address = w3.to_checksum_address(share_with_address)
    except Exception:
        return jsonify({"error": "Invalid guest public address format"}), 400 # English Hardcode
    guest_user = User.query.filter(User.public_address.ilike(checked_guest_address)).first()
    if not guest_user:
        current_app.logger.info(f"[Shares] Creating new user record for guest: {checked_guest_address}") # English Hardcode
        placeholder_email = f"{checked_guest_address.lower()}@flowork.crypto" # Email placeholder unik
        email_exists = User.query.filter(User.public_address.ilike(checked_guest_address)).first()
        if email_exists:
            guest_user = email_exists # Use existing user
        else:
            guest_user = User(
                username=checked_guest_address, # USERNAME = PUBLIC ADDRESS
                email=placeholder_email,
                password_hash=generate_password_hash(secrets.token_urlsafe(32), method="pbkdf2:sha256"), # Placeholder password
                status="active", # English Hardcode
                public_address=checked_guest_address
            )
            db.session.add(guest_user)
            try:
                db.session.commit() # Commit new user to get guest_user.id
                from app.models import Subscription
                new_subscription = Subscription(user_id=guest_user.id, tier="architect") # Default ke architect
                db.session.add(new_subscription)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"[Shares] Failed to create new guest user {checked_guest_address}: {e}") # English Hardcode
                return jsonify({"error": "Failed to create guest user record"}), 500 # English Hardcode
    existing_share = EngineShare.query.filter_by(engine_id=engine.id, user_id=guest_user.id).first()
    try:
        if existing_share:
            current_app.logger.info(f"[Shares] Updating role for {checked_guest_address} on engine {engine_id_str} to '{role}'") # English Hardcode
            existing_share.role = role
            db.session.commit()
            socketio.emit(
                'force_refresh_auth_list',
                {'message': f'Share role updated for {checked_guest_address}'}, # English Hardcode
                room=engine.engine_id
            )
            current_app.logger.info(f"Sent 'force_refresh_auth_list' PUSH to room: {engine.engine_id}") # English Hardcode
            return jsonify({"message": "Share role updated successfully"}), 200 # English Hardcode
        else:
            current_app.logger.info(f"[Shares] Creating new share for {checked_guest_address} on engine {engine_id_str} with role '{role}'") # English Hardcode
            new_share = EngineShare(
                engine_id=engine.id,
                user_id=guest_user.id,
                role=role
            )
            db.session.add(new_share)
            db.session.commit()
            socketio.emit(
                'force_refresh_auth_list',
                {'message': f'User {checked_guest_address} added to shares'}, # English Hardcode
                room=engine.engine_id
            )
            current_app.logger.info(f"Sent 'force_refresh_auth_list' PUSH to room: {engine.engine_id}") # English Hardcode
            return jsonify({"message": "Engine shared successfully", "share_id": new_share.id}), 201 # English Hardcode
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[Shares] Error creating/updating share: {e}", exc_info=True) # English Hardcode
        return jsonify({"error": "Database error while saving share"}), 500 # English Hardcode
@shares_bp.route('/delete', methods=['POST'])
@crypto_auth_required
def delete_share():
    """
    Deletes a 'share' from an engine.
    Only the ENGINE OWNER can perform this action.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400 # English Hardcode
    share_id = data.get('share_id')
    if not share_id:
        return jsonify({"error": "share_id is required"}), 400 # English Hardcode
    owner_user = g.user
    if not owner_user:
        current_app.logger.error(f"[Shares] No authenticated user (g.user) in context for delete.") # English Hardcode
        return jsonify({"error": "Authentication context not found"}), 500 # English Hardcode
    share = EngineShare.query.get(share_id)
    if not share:
        return jsonify({"error": "Share record not found"}), 404 # English Hardcode
    engine = RegisteredEngine.query.get(share.engine_id)
    if not engine:
        current_app.logger.error(f"[Shares] Share {share_id} references non-existent engine {share.engine_id}") # English Hardcode
        return jsonify({"error": "Associated engine not found"}), 500 # English Hardcode
    if engine.user_id != owner_user.id:
        current_app.logger.warning(f"[AuthZ] DENIED: User {owner_user.public_address} tried to delete share {share_id} for engine {engine.engine_id} which they do not own.") # English Hardcode
        return jsonify({"error": "You are not the owner of this engine"}), 403 # English Hardcode
    try:
        engine_id_str = engine.engine_id # Save for notification
        user_address_revoked = share.user.public_address # Save for logging
        db.session.delete(share)
        db.session.commit()
        current_app.logger.info(f"[Shares] Share {share_id} (User: {user_address_revoked}) deleted from engine {engine_id_str} by owner.") # English Hardcode
        socketio.emit(
            'force_refresh_auth_list',
            {'message': f'User {user_address_revoked} was removed from shares'}, # English Hardcode
            room=engine_id_str
        )
        current_app.logger.info(f"Sent 'force_refresh_auth_list' PUSH to room: {engine_id_str}") # English Hardcode
        return jsonify({"message": "Share deleted successfully"}), 200 # English Hardcode
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[Shares] Error deleting share {share_id}: {e}", exc_info=True) # English Hardcode
        return jsonify({"error": "Database error while deleting share"}), 500 # English Hardcode
