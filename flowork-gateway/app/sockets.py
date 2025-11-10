########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\sockets.py total lines 802 
########################################################################

from flask import request, current_app
from sqlalchemy.orm import joinedload
from datetime import datetime
import logging
import json

from flask_socketio import join_room, leave_room
from werkzeug.security import check_password_hash

from .extensions import db, socketio as sio
from .models import User, RegisteredEngine, UserEngineSession, EngineShare
from .globals import globals_instance
from .helpers import (
    get_db_session,
    find_active_engine_session,
    verify_web3_signature
)

def _safe_get_session(sid: str, namespace: str):
    try:
        return sio.server.get_session(sid, namespace=namespace)
    except Exception:
        return None


@sio.on('connect', namespace='/engine-socket')
def on_engine_connect(auth):
    app = current_app._get_current_object()
    sid = request.sid
    remote_addr = request.environ.get('REMOTE_ADDR', 'N/A')

    if not auth or 'engine_id' not in auth or 'token' not in auth:
        app.logger.warning(f"[Gateway Engine Connect] Engine connection from {remote_addr} missing auth data. Disconnecting.")
        return False

    engine_id = auth.get('engine_id')
    token = auth.get('token')

    session = get_db_session()
    try:
        engine = session.query(RegisteredEngine).filter_by(id=engine_id).first()
        if not engine or not check_password_hash(engine.engine_token_hash, token):
            app.logger.warning(f"[Gateway Engine Connect] Engine auth failed for engine_id: {engine_id} from {remote_addr}. Disconnecting.")
            sio.emit('auth_failed', {'error': 'Invalid engine_id or token'}, room=sid, namespace='/engine-socket')
            return False

        sio.server.save_session(sid, {'engine_id': engine_id, 'user_id': engine.user_id}, namespace='/engine-socket')
        join_room(engine.user_id, sid, namespace='/engine-socket')

        if globals_instance.engine_manager.active_engine_sessions.get(engine_id) != sid:
            globals_instance.engine_manager.active_engine_sessions[engine_id] = sid
            app.logger.info(f"[Gateway Engine Connect] Pre-registered live SID for Engine {engine_id} -> {sid}")

        sio.emit('auth_success', {'user_id': engine.user_id}, room=sid, namespace='/engine-socket')
        return True

    except Exception as e:
        app.logger.error(f"[Gateway Engine Connect] Error during engine connect: {e}", exc_info=True)
        return False
    finally:
        session.close()


@sio.on('disconnect', namespace='/engine-socket')
def on_engine_disconnect():
    app = current_app._get_current_object()
    sid = request.sid
    session_data = _safe_get_session(sid, namespace='/engine-socket')

    if session_data is None:
        app.logger.warning(f"[Gateway Engine Disconnect] A disconnected engine SID {sid} had no session data.")
        return

    engine_id = session_data.get('engine_id')
    user_id = session_data.get('user_id')

    if not engine_id:
        app.logger.warning(f"[Gateway Engine Disconnect] SID {sid} missing engine_id.")
        return

    app.logger.info(f"[Gateway Engine Disconnect] Engine {engine_id} (User: {user_id}) disconnected. SID: {sid}")

    removed_sid = globals_instance.engine_manager.active_engine_sessions.pop(engine_id, None)
    if removed_sid:
        app.logger.info(f"[Gateway Engine Disconnect] Removed live SID {removed_sid} for Engine {engine_id} from active session map.")
    else:
        app.logger.warning(f"[Gateway Engine Disconnect] Engine {engine_id} disconnected, but it was not in the active session map.")

    session = get_db_session()
    try:
        existing_session = session.query(UserEngineSession).filter_by(engine_id=engine_id, is_active=True).first()
        if existing_session:
            existing_session.is_active = False
            existing_session.disconnected_at = datetime.utcnow()
            session.commit()
            globals_instance.engine_manager.engine_url_map.pop(engine_id, None)

            gui_room = str(user_id)
            sio.emit('engine_status_update', {
                'engine_id': engine_id,
                'status': 'offline',
                'vitals': None
            }, room=gui_room, namespace='/gui-socket')
    except Exception as e:
        app.logger.error(f"[Gateway Engine Disconnect] Error updating engine session for {engine_id}: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()


@sio.on('engine_ready', namespace='/engine-socket')
def handle_engine_ready(data):
    app = current_app._get_current_object()
    sid = request.sid
    session_data = _safe_get_session(sid, namespace='/engine-socket')

    if session_data is None:
        app.logger.warning(f"[Gateway Engine Ready] 'engine_ready' from SID {sid} with no session data. Ignoring.")
        return

    engine_id = session_data.get('engine_id')
    user_id = session_data.get('user_id')

    internal_api_url = None
    if isinstance(data, dict) and data.get('v') == 2:
        internal_api_url = (data.get('payload') or {}).get('internal_api_url')
    elif isinstance(data, dict):
        internal_api_url = data.get('internal_api_url')

    if not internal_api_url:
        app.logger.warning(f"[Gateway Engine Ready] Engine {engine_id} sent without internal_api_url.")
        return

    app.logger.info(f"[Gateway Engine Ready] Engine {engine_id} READY. Internal URL: {internal_api_url}")

    globals_instance.engine_manager.active_engine_sessions[engine_id] = sid
    globals_instance.engine_manager.engine_url_map[engine_id] = internal_api_url

    session = get_db_session()
    try:
        for stale in session.query(UserEngineSession).filter_by(engine_id=engine_id, is_active=True).all():
            stale.is_active = False
            stale.disconnected_at = datetime.utcnow()

        new_session = UserEngineSession(
            user_id=user_id,
            engine_id=engine_id,
            internal_url=internal_api_url,
            is_active=True,
            last_activated_at=int(datetime.utcnow().timestamp())
        )
        session.add(new_session)
        session.commit()

        sio.emit('engine_status_update', {
            'engine_id': engine_id,
            'status': 'online',
            'vitals': None
        }, room=str(user_id), namespace='/gui-socket')

    except Exception as e:
        app.logger.error(f"[Gateway Engine Ready] Failed to update session for engine {engine_id}: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()


@sio.on('engine_vitals_update', namespace='/engine-socket')
def handle_engine_vitals_update(data=None):
    """
    Tahan banting:
     - pakai session kalau ada
     - kalau TIDAK ada session, ambil engine_id & user_id dari payload (flat)
       untuk backfill map + DB → ini nutup race condition awal.
    """
    app = current_app._get_current_object()
    sid = request.sid
    sess = _safe_get_session(sid, namespace='/engine-socket')

    payload = {}
    if isinstance(data, dict) and data.get('v') == 2:
        payload = data.get('payload') or {}
    elif isinstance(data, dict):
        payload = data
    else:
        payload = {}

    engine_id = (sess or {}).get('engine_id') or payload.get('engine_id')
    user_id = (sess or {}).get('user_id') or payload.get('user_id')
    internal_url = payload.get('internal_api_url') or payload.get('internal_url')

    if not engine_id or not user_id:
        app.logger.warning(f"[Gateway Vitals] Missing engine_id/user_id (sid={sid}). Dropping vitals.")
        return

    current_sid = globals_instance.engine_manager.active_engine_sessions.get(engine_id)
    did_backfill = False
    if current_sid != sid:
        globals_instance.engine_manager.active_engine_sessions[engine_id] = sid
        did_backfill = True
        app.logger.info(f"[Gateway Vitals] Backfilled live SID map for Engine {engine_id} -> {sid}")

    if internal_url:
        globals_instance.engine_manager.engine_url_map[engine_id] = internal_url

    session = get_db_session()
    try:
        active_db = find_active_engine_session(session, user_id, engine_id)
        if not active_db:
            new_sess = UserEngineSession(
                user_id=user_id,
                engine_id=engine_id,
                internal_url=internal_url or globals_instance.engine_manager.engine_url_map.get(engine_id),
                is_active=True,
                last_activated_at=int(datetime.utcnow().timestamp())
            )
            session.add(new_sess)
            session.commit()
            did_backfill = True
            app.logger.info(f"[Gateway Vitals] Backfilled ACTIVE DB session for engine {engine_id}")
    except Exception as e:
        app.logger.error(f"[Gateway Vitals] Backfill DB session failed for engine {engine_id}: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()

    if did_backfill:
        sio.emit('engine_status_update', {
            'engine_id': engine_id,
            'status': 'online',
            'vitals': None
        }, room=str(user_id), namespace='/gui-socket')
        app.logger.info(f"[Gateway Vitals] Announced ONLINE status to GUI room {user_id} for engine {engine_id}")

    sio.emit('engine_vitals_update', {
        'engine_id': engine_id,
        'vitals': payload
    }, room=str(user_id), namespace='/gui-socket')


def _emit_to_gui(user_id: str, event_name: str, data):
    """Helper kecil buat kirim ke GUI room + log."""
    app = current_app._get_current_object()
    sio.emit(event_name, data, room=str(user_id), namespace='/gui-socket')
    app.logger.info(f"[Gateway] Fwd '{event_name}' to GUI room {user_id}")

@sio.on('response_component_list', namespace='/engine-socket')
def on_engine_response_component_list(data):
    sess = _safe_get_session(request.sid, namespace='/engine-socket')
    if not sess: return
    _emit_to_gui(sess.get('user_id'), 'response_component_list', data)

@sio.on('response_variables', namespace='/engine-socket')
def on_engine_response_variables(data):
    sess = _safe_get_session(request.sid, namespace='/engine-socket')
    if not sess: return
    _emit_to_gui(sess.get('user_id'), 'response_variables', data)

@sio.on('response_presets_list', namespace='/engine-socket')
def on_engine_response_presets_list(data):
    sess = _safe_get_session(request.sid, namespace='/engine-socket')
    if not sess: return
    _emit_to_gui(sess.get('user_id'), 'response_presets_list', data)

@sio.on('response_ai_status', namespace='/engine-socket')
def on_engine_response_ai_status(data):
    sess = _safe_get_session(request.sid, namespace='/engine-socket')
    if not sess: return
    _emit_to_gui(sess.get('user_id'), 'response_ai_status', data)

@sio.on('response_datasets_list', namespace='/engine-socket')
def on_engine_response_datasets_list(data):
    sess = _safe_get_session(request.sid, namespace='/engine-socket')
    if not sess: return
    _emit_to_gui(sess.get('user_id'), 'response_datasets_list', data)

@sio.on('response_local_models', namespace='/engine-socket')
def on_engine_response_local_models(data):
    sess = _safe_get_session(request.sid, namespace='/engine-socket')
    if not sess: return
    _emit_to_gui(sess.get('user_id'), 'response_local_models', data)

@sio.on('response_training_job_status', namespace='/engine-socket')
def on_engine_response_training_job_status(data):
    sess = _safe_get_session(request.sid, namespace='/engine-socket')
    if not sess: return
    _emit_to_gui(sess.get('user_id'), 'response_training_job_status', data)

@sio.on('component_install_status', namespace='/engine-socket')
def on_engine_component_install_status(data):
    sess = _safe_get_session(request.sid, namespace='/engine-socket')
    if not sess: return
    _emit_to_gui(sess.get('user_id'), 'component_install_status', data)


@sio.on('connect', namespace='/gui-socket')
def on_gui_connect(auth):
    app = current_app._get_current_object()
    sid = request.sid
    remote_addr = request.environ.get('REMOTE_ADDR', 'N/A')

    auth_dict = auth
    if isinstance(auth, str):
        try:
            auth_dict = json.loads(auth)
            app.logger.info(f"[Gateway GUI Connect] Parsed string-based auth from {remote_addr}.")
        except json.JSONDecodeError:
            app.logger.error(f"[Gateway GUI Connect] Failed to parse string-based auth from {remote_addr}.")
            return False
    elif not isinstance(auth, dict):
        app.logger.error(f"[Gateway GUI Connect] Auth object is not dict or string. Denied.")
        return False

    headers = auth_dict.get('headers') if auth_dict else None
    if not headers:
        app.logger.warning(f"[Gateway GUI] Missing signature headers from {remote_addr}. Denied.")
        return False

    address = headers.get('X-User-Address')
    message = headers.get('X-Signed-Message')
    signature = headers.get('X-Signature')
    payload_v = headers.get('X-Payload-Version')

    if not address or not message or not signature or not payload_v:
        app.logger.warning(f"[Gateway GUI] Incomplete auth headers from {remote_addr}. Denied.")
        return False

    try:
        ts_str = message.split('|')[-1]
        if not ts_str.isdigit():
            raise ValueError("Invalid message format")
        ts = int(ts_str)
        if abs(datetime.utcnow().timestamp() - ts) > 300:
            app.logger.warning(f"[Gateway GUI] Auth expired for {address} from {remote_addr}. Denied.")
            return False
        if not verify_web3_signature(address, message, signature):
            app.logger.warning(f"[Gateway GUI] Invalid signature for {address} from {remote_addr}. Denied.")
            return False
    except Exception as e:
        app.logger.error(f"[Gateway GUI] Error during signature validation: {e}", exc_info=True)
        return False

    session = get_db_session()
    try:
        user = session.query(User).filter(User.public_address.ilike(address)).first()
        if not user:
            app.logger.info(f"[Gateway GUI] First connect for {address}. Creating user.")
            user = User(public_address=address, username=f"User-{address[:6]}")
            session.add(user)
            session.commit()

        sio.server.save_session(sid, {'user_id': user.id, 'user_address': user.public_address, 'user_signature': signature}, namespace='/gui-socket')
        join_room(str(user.id), sid, namespace='/gui-socket')
        app.logger.info(f"[Gateway GUI] Auth success for {address} (User ID: {user.id}). SID {sid} joined room '{user.id}'.")

        owned = session.query(RegisteredEngine).filter_by(user_id=user.id).all()
        shared = session.query(EngineShare).filter_by(user_id=user.id).options(joinedload(EngineShare.engine)).all()
        all_engines = list(owned) + [s.engine for s in shared]

        statuses = []
        for eng in all_engines:
            active_db = find_active_engine_session(session, user.id, eng.id)

            live_sid = globals_instance.engine_manager.active_engine_sessions.get(str(eng.id))

            statuses.append({
                'engine_id': eng.id,
                'status': 'online' if (active_db and live_sid) else 'offline',
                'vitals': None
            })

        sio.emit('initial_engine_statuses', statuses, room=sid, namespace='/gui-socket')
        return True
    except Exception as e:
        app.logger.error(f"[Gateway GUI] DB error during auth/setup: {e}", exc_info=True)
        session.rollback()
        return False
    finally:
        session.close()


@sio.on('disconnect', namespace='/gui-socket')
def on_gui_disconnect():
    app = current_app._get_current_object()
    sid = request.sid
    sess = _safe_get_session(sid, namespace='/gui-socket')
    if sess is None:
        app.logger.warning(f"[Gateway GUI Disconnect] GUI SID {sid} disconnected with no session.")
        return
    user_id = sess.get('user_id')
    app.logger.info(f"[Gateway GUI Disconnect] GUI for User {user_id} disconnected. SID: {sid}")
    try:
        leave_room(str(user_id), sid, namespace='/gui-socket')
    except Exception:
        pass


def _resolve_target_engine_sid(session, user_id, target_engine_id):
    """
    Cari engine aktif di DB; kalau ada, balikin live SID dari map.
    """
    active_db = find_active_engine_session(session, user_id, target_engine_id)
    if not active_db:
        return None, None
    eng_id = active_db.engine_id

    eng_id_str = str(eng_id)
    eng_sid = globals_instance.engine_manager.active_engine_sessions.get(eng_id_str)

    return eng_id, eng_sid


@sio.on('request_presets_list', namespace='/gui-socket')
def on_request_presets_list(data):
    app = current_app._get_current_object()
    sid = request.sid
    gui_sess = _safe_get_session(sid, namespace='/gui-socket')
    if gui_sess is None:
        app.logger.warning(f"[Gateway] 'request_presets_list' from unauthenticated SID {sid}.")
        return

    user_id = gui_sess.get('user_id')
    user_addr = gui_sess.get('user_address')
    if not isinstance(data, dict) or data.get('v') != 2:
        app.logger.error(f"[Core] Non-versioned 'request_presets_list' from GUI {sid}.")
        return
    payload = data.get('payload', {})
    target_engine_id = payload.get('target_engine_id')  # boleh None → fallback ke engine aktif di DB

    session = get_db_session()
    try:
        eng_id, eng_sid = _resolve_target_engine_sid(session, user_id, target_engine_id)
        if not eng_id or not eng_sid:
            app.logger.warning(f"[Gateway] Cannot forward 'request_presets_list'. No LIVE SID for engine DB-active.")
            sio.emit('response_presets_list', {'error': f'Engine {target_engine_id or "active"} is not connected to the Gateway.'}, room=sid, namespace='/gui-socket')
            return

        payload['user_context'] = {'id': user_addr, 'tier': 'architect'}
        sio.emit('request_presets_list', {'v': 2, 'payload': payload}, room=eng_sid, namespace='/engine-socket')
        app.logger.info(f"[Gateway] Fwd 'request_presets_list' GUI {sid} -> EngineSID {eng_sid} (EngineID: {eng_id})")

    except Exception as e:
        app.logger.error(f"[Gateway] Error forwarding 'request_presets_list': {e}", exc_info=True)
    finally:
        session.close()


@sio.on('request_variables', namespace='/gui-socket')
def on_request_variables(data):
    app = current_app._get_current_object()
    sid = request.sid
    gui_sess = _safe_get_session(sid, namespace='/gui-socket')
    if gui_sess is None:
        app.logger.warning(f"[Gateway] 'request_variables' from unauthenticated SID {sid}.")
        return

    user_id = gui_sess.get('user_id')
    user_addr = gui_sess.get('user_address')
    if not isinstance(data, dict) or data.get('v') != 2:
        app.logger.error(f"[Core] Non-versioned 'request_variables' from GUI {sid}.")
        return
    payload = data.get('payload', {})
    target_engine_id = payload.get('target_engine_id')

    session = get_db_session()
    try:
        eng_id, eng_sid = _resolve_target_engine_sid(session, user_id, target_engine_id)
        if not eng_id or not eng_sid:
            app.logger.warning(f"[Gateway] Cannot forward 'request_variables'. No LIVE SID for engine DB-active.")
            sio.emit('response_variables', {'error': f'Engine {target_engine_id or "active"} is not connected to the Gateway.'}, room=sid, namespace='/gui-socket')
            return

        payload['user_context'] = {'id': user_addr, 'tier': 'architect'}
        sio.emit('request_variables', {'v': 2, 'payload': payload}, room=eng_sid, namespace='/engine-socket')
        app.logger.info(f"[Gateway] Fwd 'request_variables' GUI {sid} -> EngineSID {eng_sid} (EngineID: {eng_id})")

    except Exception as e:
        app.logger.error(f"[Gateway] Error forwarding 'request_variables': {e}", exc_info=True)
    finally:
        session.close()


@sio.on('request_components_list', namespace='/gui-socket')
def on_request_components_list(data):
    app = current_app._get_current_object()
    sid = request.sid
    gui_sess = _safe_get_session(sid, namespace='/gui-socket')
    if gui_sess is None:
        app.logger.warning(f"[Gateway] 'request_components_list' from unauthenticated SID {sid}.")
        return

    user_id = gui_sess.get('user_id')
    user_addr = gui_sess.get('user_address')
    if not isinstance(data, dict) or data.get('v') != 2:
        app.logger.error(f"[Core] Non-versioned 'request_components_list' from GUI {sid}.")
        return
    payload = data.get('payload', {})
    comp_type = payload.get('component_type', 'unknown')
    target_engine_id = payload.get('target_engine_id')

    session = get_db_session()
    try:
        eng_id, eng_sid = _resolve_target_engine_sid(session, user_id, target_engine_id)
        if not eng_id or not eng_sid:
            app.logger.warning(f"[Gateway] Cannot forward 'request_components_list' for '{comp_type}'. No LIVE SID for engine DB-active.")
            sio.emit('response_component_list', {
                'error': f'Engine {target_engine_id or "active"} is not connected to the Gateway.',
                'component_type': comp_type,
                'components': []
            }, room=sid, namespace='/gui-socket')
            return

        payload['user_context'] = {'id': user_addr, 'tier': 'architect'}

        sio.emit('request_components_list', {'v': 2, 'payload': payload}, room=eng_sid, namespace='/engine-socket')

        app.logger.info(f"[Gateway] Fwd 'request_components_list'({comp_type}) GUI {sid} -> EngineSID {eng_sid} (EngineID: {eng_id})")

    except Exception as e:
        app.logger.error(f"[Gateway] Error forwarding 'request_components_list': {e}", exc_info=True)
    finally:
        session.close()


@sio.on('request_ai_status', namespace='/gui-socket')
def on_request_ai_status(data):
    app = current_app._get_current_object()
    sid = request.sid
    gui_sess = _safe_get_session(sid, namespace='/gui-socket')
    if gui_sess is None: return
    user_id = gui_sess.get('user_id')
    user_addr = gui_sess.get('user_address')

    if not isinstance(data, dict) or data.get('v') != 2:
        app.logger.error(f"[Core] Non-versioned 'request_ai_status' from GUI {sid}.")
        return
    payload = data.get('payload', {})
    target_engine_id = payload.get('target_engine_id')

    session = get_db_session()
    try:
        eng_id, eng_sid = _resolve_target_engine_sid(session, user_id, target_engine_id)
        if not eng_id or not eng_sid:
            sio.emit('response_ai_status', {'error': f'Engine {target_engine_id or "active"} is not connected to the Gateway.'}, room=sid, namespace='/gui-socket')
            return
        payload['user_context'] = {'id': user_addr, 'tier': 'architect'}
        sio.emit('request_ai_status', {'v': 2, 'payload': payload}, room=eng_sid, namespace='/engine-socket')
        app.logger.info(f"[Gateway] Fwd 'request_ai_status' GUI {sid} -> EngineSID {eng_sid} (EngineID: {eng_id})")
    finally:
        session.close()


@sio.on('request_datasets_list', namespace='/gui-socket')
def on_request_datasets_list(data):
    app = current_app._get_current_object()
    sid = request.sid
    gui_sess = _safe_get_session(sid, namespace='/gui-socket')
    if gui_sess is None: return
    user_id = gui_sess.get('user_id')
    user_addr = gui_sess.get('user_address')

    if not isinstance(data, dict) or data.get('v') != 2:
        app.logger.error(f"[Core] Non-versioned 'request_datasets_list' from GUI {sid}.")
        return
    payload = data.get('payload', {})
    target_engine_id = payload.get('target_engine_id')

    session = get_db_session()
    try:
        eng_id, eng_sid = _resolve_target_engine_sid(session, user_id, target_engine_id)
        if not eng_id or not eng_sid:
            sio.emit('response_datasets_list', {'error': f'Engine {target_engine_id or "active"} is not connected to the Gateway.'}, room=sid, namespace='/gui-socket')
            return
        payload['user_context'] = {'id': user_addr, 'tier': 'architect'}
        sio.emit('request_datasets_list', {'v': 2, 'payload': payload}, room=eng_sid, namespace='/engine-socket')
        app.logger.info(f"[Gateway] Fwd 'request_datasets_list' GUI {sid} -> EngineSID {eng_sid} (EngineID: {eng_id})")
    finally:
        session.close()


@sio.on('request_local_models', namespace='/gui-socket')
def on_request_local_models(data):
    app = current_app._get_current_object()
    sid = request.sid
    gui_sess = _safe_get_session(sid, namespace='/gui-socket')
    if gui_sess is None: return
    user_id = gui_sess.get('user_id')
    user_addr = gui_sess.get('user_address')

    if not isinstance(data, dict) or data.get('v') != 2:
        app.logger.error(f"[Core] Non-versioned 'request_local_models' from GUI {sid}.")
        return
    payload = data.get('payload', {})
    target_engine_id = payload.get('target_engine_id')

    session = get_db_session()
    try:
        eng_id, eng_sid = _resolve_target_engine_sid(session, user_id, target_engine_id)
        if not eng_id or not eng_sid:
            sio.emit('response_local_models', {'error': f'Engine {target_engine_id or "active"} is not connected to the Gateway.'}, room=sid, namespace='/gui-socket')
            return
        payload['user_context'] = {'id': user_addr, 'tier': 'architect'}
        sio.emit('request_local_models', {'v': 2, 'payload': payload}, room=eng_sid, namespace='/engine-socket')
        app.logger.info(f"[Gateway] Fwd 'request_local_models' GUI {sid} -> EngineSID {eng_sid} (EngineID: {eng_id})")
    finally:
        session.close()


@sio.on('request_training_job_status', namespace='/gui-socket')
def on_request_training_job_status(data):
    app = current_app._get_current_object()
    sid = request.sid
    gui_sess = _safe_get_session(sid, namespace='/gui-socket')
    if gui_sess is None: return
    user_id = gui_sess.get('user_id')
    user_addr = gui_sess.get('user_address')

    if not isinstance(data, dict) or data.get('v') != 2:
        app.logger.error(f"[Core] Non-versioned 'request_training_job_status' from GUI {sid}.")
        return
    payload = data.get('payload', {})
    target_engine_id = payload.get('target_engine_id')

    session = get_db_session()
    try:
        eng_id, eng_sid = _resolve_target_engine_sid(session, user_id, target_engine_id)
        if not eng_id or not eng_sid:
            sio.emit('response_training_job_status', {'error': f'Engine {target_engine_id or "active"} is not connected to the Gateway.'}, room=sid, namespace='/gui-socket')
            return
        payload['user_context'] = {'id': user_addr, 'tier': 'architect'}
        sio.emit('request_training_job_status', {'v': 2, 'payload': payload}, room=eng_sid, namespace='/engine-socket')
        app.logger.info(f"[Gateway] Fwd 'request_training_job_status' GUI {sid} -> EngineSID {eng_sid} (EngineID: {eng_id})")
    finally:
        session.close()


@sio.on('execute_workflow', namespace='/gui-socket')
def on_execute_workflow(data):
    app = current_app._get_current_object()
    sid = request.sid
    gui_sess = _safe_get_session(sid, namespace='/gui-socket')
    if gui_sess is None:
        app.logger.warning(f"[Gateway] 'execute_workflow' from unauthenticated SID {sid}.")
        return

    user_id = gui_sess.get('user_id')
    user_addr = gui_sess.get('user_address')
    if not isinstance(data, dict) or data.get('v') != 2:
        app.logger.error(f"[Core] Non-versioned 'execute_workflow' from GUI {sid}.")
        return
    payload = data.get('payload', {})
    target_engine_id = payload.get('target_engine_id')

    session = get_db_session()
    try:
        eng_id, eng_sid = _resolve_target_engine_sid(session, user_id, target_engine_id)
        if not eng_id or not eng_sid:
            app.logger.warning(f"[Gateway] Cannot forward 'execute_workflow'. No LIVE SID for engine DB-active.")
            return

        payload['user_context'] = {'id': user_addr, 'tier': 'architect'}
        sio.emit('execute_workflow', {'v': 2, 'payload': payload}, room=eng_sid, namespace='/engine-socket')
        app.logger.info(f"[Gateway] Fwd 'execute_workflow' GUI {sid} -> EngineSID {eng_sid} (EngineID: {eng_id})")

    except Exception as e:
        app.logger.error(f"[Gateway] Error forwarding 'execute_workflow': {e}", exc_info=True)
    finally:
        session.close()


@sio.on('save_preset', namespace='/gui-socket')
def on_save_preset(data):
    app = current_app._get_current_object()
    sid = request.sid
    gui_sess = _safe_get_session(sid, namespace='/gui-socket')
    if gui_sess is None:
        app.logger.warning(f"[Gateway] 'save_preset' from unauthenticated SID {sid}.")
        return

    user_id = gui_sess.get('user_id')
    user_addr = gui_sess.get('user_address')
    signature = gui_sess.get('user_signature')
    if not isinstance(data, dict) or data.get('v') != 2:
        app.logger.error(f"[Core] Non-versioned 'save_preset' from GUI {sid}.")
        return
    payload = data.get('payload', {})
    target_engine_id = payload.get('target_engine_id')
    payload['signature'] = signature  # bawa signature GUI

    session = get_db_session()
    try:
        eng_id, eng_sid = _resolve_target_engine_sid(session, user_id, target_engine_id)
        if not eng_id or not eng_sid:
            app.logger.warning(f"[Gateway] Cannot forward 'save_preset'. No LIVE SID for engine DB-active.")
            return

        payload['user_context'] = {'id': user_addr, 'tier': 'architect'}
        sio.emit('save_preset', {'v': 2, 'payload': payload}, room=eng_sid, namespace='/engine-socket')
        app.logger.info(f"[Gateway] Fwd 'save_preset' GUI {sid} -> EngineSID {eng_sid} (EngineID: {eng_id})")

    except Exception as e:
        app.logger.error(f"[Gateway] Error forwarding 'save_preset': {e}", exc_info=True)
    finally:
        session.close()

@sio.on('install_component', namespace='/gui-socket')
def on_install_component(data):
    app = current_app._get_current_object()
    sid = request.sid
    gui_sess = _safe_get_session(sid, namespace='/gui-socket')
    if gui_sess is None:
        app.logger.warning(f"[Gateway] 'install_component' from unauthenticated SID {sid}.")
        return

    user_id = gui_sess.get('user_id')
    user_addr = gui_sess.get('user_address')

    if not isinstance(data, dict) or data.get('v') != 2:
        app.logger.error(f"[Core] Non-versioned 'install_component' from GUI {sid}.")
        return
    payload = data.get('payload', {})
    target_engine_id = payload.get('target_engine_id')

    session = get_db_session()
    try:
        eng_id, eng_sid = _resolve_target_engine_sid(session, user_id, target_engine_id)
        if not eng_id or not eng_sid:
            app.logger.warning(f"[Gateway] Cannot forward 'install_component'. No LIVE SID for engine DB-active.")
            sio.emit('component_install_status', {'v': 2, 'payload': {
                'error': f'Engine {target_engine_id or "active"} is not connected.',
                'success': False,
                'component_id': payload.get('component_id'),
                'component_type': payload.get('component_type'),
                'message': 'Engine is not connected to the Gateway.'
            }}, room=sid, namespace='/gui-socket')
            return
        payload['user_context'] = {'id': user_addr, 'tier': 'architect'}
        sio.emit('install_component', {'v': 2, 'payload': payload}, room=eng_sid, namespace='/engine-socket')
        app.logger.info(f"[Gateway] Fwd 'install_component' GUI {sid} -> EngineSID {eng_sid} (EngineID: {eng_id})")
    finally:
        session.close()

@sio.on('uninstall_component', namespace='/gui-socket')
def on_uninstall_component(data):
    app = current_app._get_current_object()
    sid = request.sid
    gui_sess = _safe_get_session(sid, namespace='/gui-socket')
    if gui_sess is None:
        app.logger.warning(f"[Gateway] 'uninstall_component' from unauthenticated SID {sid}.")
        return

    user_id = gui_sess.get('user_id')
    user_addr = gui_sess.get('user_address')

    if not isinstance(data, dict) or data.get('v') != 2:
        app.logger.error(f"[Core] Non-versioned 'uninstall_component' from GUI {sid}.")
        return
    payload = data.get('payload', {})
    target_engine_id = payload.get('target_engine_id')

    session = get_db_session()
    try:
        eng_id, eng_sid = _resolve_target_engine_sid(session, user_id, target_engine_id)
        if not eng_id or not eng_sid:
            app.logger.warning(f"[Gateway] Cannot forward 'uninstall_component'. No LIVE SID for engine DB-active.")
            sio.emit('component_install_status', {'v': 2, 'payload': {
                'error': f'Engine {target_engine_id or "active"} is not connected.',
                'success': False,
                'component_id': payload.get('component_id'),
                'component_type': payload.get('component_type'),
                'message': 'Engine is not connected to the Gateway.'
            }}, room=sid, namespace='/gui-socket')
            return
        payload['user_context'] = {'id': user_addr, 'tier': 'architect'}
        sio.emit('uninstall_component', {'v': 2, 'payload': payload}, room=eng_sid, namespace='/engine-socket')
        app.logger.info(f"[Gateway] Fwd 'uninstall_component' GUI {sid} -> EngineSID {eng_sid} (EngineID: {eng_id})")
    finally:
        session.close()


@sio.on('*', namespace='/gui-socket')
def on_gui_catch_all(event, data):
    app = current_app._get_current_object()
    sid = request.sid
    known = {
        'connect', 'disconnect', 'request_presets_list', 'request_variables',
        'request_components_list', 'execute_workflow', 'save_preset',
        'request_ai_status', 'request_datasets_list', 'request_local_models', 'request_training_job_status',
        'request_settings', 'save_settings', 'update_variable', 'delete_variable',
        'request_prompts_list', 'update_prompt', 'delete_prompt', 'load_preset',
        'delete_preset', 'request_dataset_data', 'create_dataset', 'add_dataset_data',
        'delete_dataset', 'update_dataset_row', 'delete_dataset_row',
        'install_component', 'uninstall_component', 'start_training_job'
    }
    if event not in known:
        app.logger.warning(f"[Gateway GUI] Unhandled event '{event}' from SID {sid}. Data: {data}")
