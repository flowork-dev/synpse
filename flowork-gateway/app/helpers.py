########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\helpers.py total lines 670 
########################################################################

import functools
from flask import request, current_app as app, jsonify, g
from functools import wraps
import jwt
import logging
import re
import os
import aiohttp
import datetime
import requests
import threading

from types import SimpleNamespace
from sqlalchemy.orm import joinedload

from .extensions import db
from .models import User, RegisteredEngine
from werkzeug.security import check_password_hash

from web3 import Web3
from eth_account.messages import encode_defunct


logger = logging.getLogger('flowork_gateway')


def get_db():
    """
    Gets the database connection from the application context.
    (GEMINI NOTE: This function is failing in socket context,
    we are now using get_db_session() instead)
    """
    if 'db' not in app.config:
        logger.error("[Helper] Database connection 'db' not found in app.config!")
        if not hasattr(app, 'db'):
            logger.error("[Helper] Database instance 'app.db' not found!")
            return None
        return app.db
    return app.config['db']

def get_db_session():
    """
    V2: Get the DB session from Flask-SQLAlchemy's registry.
    This is thread-safe (managed by SQLAlchemy).
    IMPORTANT: Caller MUST .close() or .remove() this session.
    """
    try:
        return db.session
    except Exception as e:
        logger.error(f"[Helper] Failed to get db.session: {e}")
        return None

def get_user_id_from_token(token):
    """
    Decodes a JWT token to get the user_id.
    Returns user_id if valid, None otherwise.
    """
    try:
        secret_key = app.config.get('JWT_SECRET_KEY')
        if not secret_key:
            logger.error("[Helper] JWT_SECRET_KEY is not set!")
            return None
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"], options={"verify_signature": True, "verify_exp": False})
        return decoded.get('user_id')
    except jwt.ExpiredSignatureError:
        logger.warning("[Helper] Token validation failed: ExpiredSignatureError")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"[Helper] Token validation failed: InvalidTokenError: {e}")
        return None

def is_valid_uuid(uuid_string):
    """
    Checks if a string is a valid UUID.
    """
    if not uuid_string:
        return False
    uuid_regex = re.compile(
        r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    )
    return re.match(uuid_regex, str(uuid_string)) is not None

def get_base_url():
    """
    Determines the base URL for the application.
    Priority:
    1. FLOWORK_GATEWAY_BASE_URL env var
    2. 'Host' header from request
    3. 'http://localhost:8000' (default)
    """
    env_url = os.environ.get('FLOWORK_GATEWAY_BASE_URL')
    if env_url:
        return env_url.rstrip('/')

    if request:
        proto = request.headers.get('X-Forwarded-Proto', 'http')
        host = request.headers.get('Host')
        if host:
            return f"{proto}://{host}"
        return request.url_root.rstrip('/')

    return 'http://localhost:8000'

def verify_web3_signature(address: str, message: str, signature: str) -> bool:
    """
    Verifies a Web3 (EIP-191) signature.
    """
    if not address or not message or not signature:
        logger.warning("[Helper] Web3 verification missing address, message, or signature.")
        return False

    try:
        w3 = Web3()
        message_hash = encode_defunct(text=message)
        signer = w3.eth.account.recover_message(message_hash, signature=signature)

        is_valid = signer.lower() == address.lower()
        if not is_valid:
            logger.warning(f"[Helper] Signature invalid. Expected {address}, got {signer}")

        return is_valid
    except Exception as e:
        logger.error(f"[Helper] Error during Web3 signature recovery: {e}", exc_info=True)
        return False


async def emit_error(sid, event_name, message, data=None):
    """
    Standardized way to emit an error message back to a specific client.
    """
    if data is None:
        data = {}

    error_response = {
        "error": message,
        **data
    }

    if hasattr(app, 'sio'):
        try:
            await app.sio.emit(event_name, error_response, to=sid)
            logger.debug(f"[Helper] Emitted error to {sid} on event '{event_name}': {message}")
        except Exception as e:
            logger.error(f"[Helper] Failed to emit error to {sid}: {e}")
    else:
        logger.error(f"[Helper] app.sio not available. Cannot emit error: {message}")

async def emit_success(sid, event_name, data=None):
    """
    Standardized way to emit a success message back to a specific client.
    """
    if data is None:
        data = {}

    if hasattr(app, 'sio'):
        try:
            await app.sio.emit(event_name, data, to=sid)
            logger.debug(f"[Helper] Emitted success to {sid} on event '{event_name}'")
        except Exception as e:
            logger.error(f"[Helper] Failed to emit success to {sid}: {e}")
    else:
        logger.error(f"[Helper] app.sio not available. Cannot emit success for event '{event_name}'")


async def get_user_id_from_sid(sid):
    """
    Retrieves the user_id from the socket.io session.
    """
    if not hasattr(app, 'sio'):
        logger.error("[Helper] app.sio not available. Cannot get session.")
        return None

    try:
        session = await app.sio.get_session(sid)
        if not session:
            logger.warning(f"[Helper] No active session found for SID: {sid}")
            return None

        user_id = session.get('user_id')
        if not user_id:
            logger.warning(f"[Helper] user_id not found in session for SID: {sid}")
            return None

        return user_id
    except KeyError:
        logger.warning(f"[Helper] SID not found in active connections: {sid}")
        return None
    except Exception as e:
        logger.error(f"[Helper] Error retrieving session for SID {sid}: {e}")
        return None

def get_request_data():
    """
    Helper to get JSON data from a request, handling content-type issues.
    """
    if request.content_type == 'application/json':
        return request.json
    else:
        try:
            return request.get_json(force=True)
        except Exception:
            return None

def crypto_auth_required(f):
    """
    Decorator for routes requiring Web3 cryptographic signature authentication.
    Verifies headers (X-User-Address, X-Signed-Message, X-Signature)
    and places the authenticated 'User' object into 'g.user'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        app_log = app.logger

        address = request.headers.get("X-User-Address")
        message = request.headers.get("X-Signed-Message")
        signature = request.headers.get("X-Signature")
        payload_v = request.headers.get("X-Payload-Version") # V2

        if not all([address, message, signature, payload_v]):
            app_log.warning("[Gateway Auth] Access denied: Missing required auth headers.") # English log
            return jsonify({"error": "Missing required authentication headers."}), 401 # English Hardcode

        try:
            ts = int(message.split('|')[-1])
            now = int(datetime.datetime.utcnow().timestamp())
            if abs(now - ts) > 300: # 5 minutes
                app_log.warning(f"[Gateway Auth] Access denied: Stale timestamp for {address[:10]}.") # English log
                return jsonify({"error": "Stale authentication signature."}), 401 # English Hardcode
        except Exception:
            app_log.warning(f"[Gateway Auth] Access denied: Invalid message format for {address[:10]}.") # English log
            return jsonify({"error": "Invalid authentication message format."}), 401 # English Hardcode

        if not verify_web3_signature(address, message, signature):
            app_log.warning(f"[Gateway Auth] Access denied: Invalid signature for {address[:10]}.") # English log
            return jsonify({"error": "Invalid signature."}), 401 # English Hardcode

        try:
            user = db.session.query(User).filter(User.public_address.ilike(address)).first()
            if not user:
                app_log.info(f"[Gateway Auth] New user authenticated: {address[:10]}. Creating user entry.") # English log
                placeholder_username = f"user_{address[:6]}...{address[-4:]}"
                user = User(public_address=address, username=placeholder_username)
                db.session.add(user)
                db.session.commit()

            g.user = user # (English Hardcode) Set user in Flask global context
            return f(*args, **kwargs)
        except Exception as e:
            db.session.rollback()
            app_log.error(f"[Gateway Auth] DB error during user lookup/create: {e}") # English log
            return jsonify({"error": "Internal server error during authentication."}), 500 # English Hardcode
    return decorated_function

def get_user_permissions(user_obj):
    """
    (REMASTERED) Calculates the user's tier and capabilities.
    V2 Simplification: All auth'd users are 'architect' tier.
    """
    base_tier = "architect"
    capabilities = [
        "basic_access", "execute_workflow", "manage_engines", # (English Hardcode)
        "save_presets", "share_workflows", "api_access" # (English Hardcode)
    ]

    return {
        "tier": base_tier,
        "capabilities": capabilities
    }

def inject_user_data_to_core(user_obj):
    """
    (REMASTERED) Finds the user's active engine (from DB) and forwards
    the user's auth/profile data to that engine's internal API.
    This is run in a thread to avoid blocking the profile response.
    """
    app_log = logging.getLogger('flowork_gateway') # (English Hardcode) Use logger
    app_log.info(f"[Gateway Auth Inject] Starting injection task for user {user_obj.public_address[:10]}...") # English log

    try:
        session = db.session()

        active_engine_session = find_active_engine_session(session, user_obj.id, None) # (FIXED) Use alias

        if not active_engine_session or not active_engine_session.internal_url:
            app_log.warning(f"[Gateway Auth Inject] No active (DB) engine session found for user {user_obj.id}. Skipping injection.") # English log
            session.close()
            return

        internal_api_url = active_engine_session.internal_url
        engine_api_endpoint = f"{internal_api_url.rstrip('/')}/api/v1/uistate/generic/current_user_data" # (English Hardcode)

        permissions_data = get_user_permissions(user_obj)

        payload = {
            "user_id": user_obj.public_address,
            "username": user_obj.username,
            "email": user_obj.email,
            "tier": permissions_data.get("tier"),
            "permissions": permissions_data.get("capabilities"),
        }

        internal_api_key = os.environ.get("FLOWORK_INTERNAL_API_KEY", "flwk_dev_default_internal_key")
        app_log.info(f"[Gateway Auth Inject] Read FLOWORK_INTERNAL_API_KEY from env: {'TOKEN_FOUND' if internal_api_key != 'flwk_dev_default_internal_key' else 'USING_DEFAULT_KEY'}")

        headers = {
            "X-Internal-API-Key": internal_api_key
        }

        app_log.info(f"[Gateway Auth Inject] Forwarding user data to {engine_api_endpoint}...") # English log
        try:
            response = requests.post(engine_api_endpoint, json=payload, headers=headers, timeout=5)
            response.raise_for_status() # (English Hardcode) Raise HTTPError for bad responses (4xx or 5xx)
            app_log.info(f"[Gateway Auth Inject] Successfully injected user data to Core Engine. Status: {response.status_code}") # English log
        except requests.exceptions.RequestException as e:
            app_log.error(f"[Gateway Auth Inject] Failed to connect/inject data to Core Engine at {engine_api_endpoint}: {e}") # English log

    except Exception as e:
        app_log.error(f"[Gateway Auth Inject] Thread error during injection: {e}", exc_info=True) # English log
    finally:
        if 'session' in locals() and session:
            session.close() # (English Hardcode) Ensure session is always closed in thread

def engine_auth_required(f):
    """
    Decorator for routes requiring Engine authentication (X-Engine-Id, X-Engine-Token).
    Places the authenticated 'RegisteredEngine' object into 'g.engine'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        app_log = app.logger

        engine_id = request.headers.get("X-Engine-Id")
        engine_token = request.headers.get("X-Engine-Token")

        if not all([engine_id, engine_token]):
            app_log.warning("[Gateway Auth] Access denied: Missing X-Engine-Id or X-Engine-Token.") # English log
            return jsonify({"error": "Missing engine authentication headers."}), 401 # English Hardcode

        try:
            engine = db.session.query(RegisteredEngine).filter_by(id=engine_id).first()

            if not engine or not check_password_hash(engine.engine_token_hash, engine_token):
                app_log.warning(f"[Gateway Auth] Access denied: Invalid engine ID or token for {engine_id}.") # English log
                return jsonify({"error": "Invalid engine ID or token."}), 401 # English Hardcode

            g.engine = engine # (English Hardcode) Set engine in Flask global context
            return f(*args, **kwargs)
        except Exception as e:
            app_log.error(f"[Gateway Auth] DB error during engine auth: {e}") # English log
            return jsonify({"error": "Internal server error during engine authentication."}), 500 # English Hardcode
    return decorated_function

def admin_token_required(f):
    """
    Decorator for routes requiring the Momod Admin Token (Bearer Token).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        app_log = app.logger

        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            app_log.warning("[Gateway Auth] Access denied: Missing Admin Bearer token.") # English log
            return jsonify({"error": "Admin token required."}), 401 # English Hardcode

        token = auth_header.split(" ")[1]
        MOMOD_ADMIN_TOKEN = os.environ.get("MOMOD_ADMIN_TOKEN", "flowork_momod_default_secret")

        if token != MOMOD_ADMIN_TOKEN:
            app_log.warning("[Gateway Auth] Access denied: Invalid Admin token.") # English log
            return jsonify({"error": "Invalid admin token."}), 403 # English Hardcode

        kwargs['admin_permissions'] = {"plan:update", "user:list", "system:read"} # (English Hardcode)
        return f(*args, **kwargs)
    return decorated_function


async def find_active_engine_session_by_user_id(user_id):
    """
    Finds the 'is_active' engine session for a given user_id from the database.
    It then checks the application's 'live' state to see if this
    engine is *currently* connected via socket.io.

    Returns the session dict with 'is_live' and 'live_sid' keys added,
    or None if no active session is found in the DB.
    """
    db = get_db_session() # (English Hardcode) FIXED: Use the correct db session function
    if not db:
        logger.error("[Helper] find_active_engine_session_by_user_id failed to get DB session.")
        return None

    engine_session_model = None
    try:
        from .models import UserEngineSession
        engine_session_model = db.query(UserEngineSession).filter_by(user_id=user_id, is_active=True).first()
    except Exception as e:
        logger.error(f"[Helper] DB query failed in find_active_engine_session_by_user_id: {e}")
        db.rollback()
        return None
    finally:
        db.close() # (English Hardcode) Always close session from get_db_session()

    if not engine_session_model:
        logger.debug(f"[Helper] No active *owned* engine session found in DB for user {user_id}")
        return None

    engine_session = {
        "engine_id": engine_session_model.engine_id,
        "user_id": engine_session_model.user_id,
        "internal_url": engine_session_model.internal_url,
        "is_active": engine_session_model.is_active
    }

    logger.info(f"[Helper] Found active *owned* engine session for user {user_id}: engine {engine_session['engine_id']}")

    live_engine_sids = app.get_live_engine_sids() # This is { engine_id: sid }
    engine_id_str = str(engine_session['engine_id'])

    logger.debug(f"[Helper DEBUG] find_active_engine_session_by_user_id: Checking for engine '{engine_id_str}'. Current live SIDs: {live_engine_sids}")

    if engine_id_str in live_engine_sids:
        engine_session['live_sid'] = live_engine_sids[engine_id_str]
        engine_session['is_live'] = True
        logger.debug(f"[Helper] Engine {engine_id_str} is LIVE with SID {engine_session['live_sid']}")
    else:
        engine_session['is_live'] = False
        engine_session['live_sid'] = None
        logger.warning(f"[Helper] Engine {engine_id_str} is DB-active but NOT LIVE.")

    return engine_session

def find_active_engine_session_wrapper(session, user_id, engine_id=None):
    """
    (GEMINI ADDED) SYNC wrapper for 'find_active_engine_session' alias.
    Matches the 3-argument call from sockets.py.
    'session' argument is ignored as we use get_db_session() for safety.
    """
    db_sess = get_db_session()
    if not db_sess:
        logger.error("[Helper Wrapper] find_active_engine_session failed to get DB session.")
        return None

    from .models import UserEngineSession # (English Hardcode) Import here

    active_db = None
    try:
        query = db_sess.query(UserEngineSession).options(joinedload(UserEngineSession.engine)).filter_by(user_id=user_id, is_active=True)

        if engine_id:
            active_db = query.filter_by(engine_id=engine_id).first()
        else:
            active_db = query.first()

        if active_db:
            result_obj = SimpleNamespace(
                engine_id=active_db.engine_id,
                user_id=active_db.user_id,
                internal_url=active_db.internal_url,
                is_active=active_db.is_active,
                engine=active_db.engine # (English Hardcode) Eagerly loaded engine
            )
            return result_obj # Return the NEW, safe object
        return None

    except Exception as e:
        logger.error(f"[Helper Wrapper] DB query failed: {e}")
        db_sess.rollback()
        return None
    finally:
        db_sess.close()

find_active_engine_session = find_active_engine_session_wrapper


async def find_specific_active_engine_session(user_id, engine_id):
    """
    Finds a *specific* 'is_active' engine session for a user from the database.
    This is used when we *know* the engine_id (e.g., from a vitals update).

    Returns the session dict with 'is_live' and 'live_sid' keys added,
    or None if not found.
    """
    db = get_db_session() # (English Hardcode) FIXED: Use the correct db session function
    if not db:
        logger.error("[Helper] find_specific_active_engine_session failed to get DB session.")
        return None

    engine_id_str = str(engine_id)

    engine_session_model = None
    try:
        from .models import UserEngineSession
        engine_session_model = db.query(UserEngineSession).filter_by(user_id=user_id, engine_id=engine_id_str, is_active=True).first()
    except Exception as e:
        logger.error(f"[Helper] DB query failed in find_specific_active_engine_session: {e}")
        db.rollback()
        return None
    finally:
        db.close() # (English Hardcode) Always close session

    if not engine_session_model:
        logger.debug(f"[Helper] No specific active engine session found in DB for user {user_id} and engine {engine_id_str}")
        return None

    engine_session = {
        "engine_id": engine_session_model.engine_id,
        "user_id": engine_session_model.user_id,
        "internal_url": engine_session_model.internal_url,
        "is_active": engine_session_model.is_active
    }

    logger.info(f"[Helper] Found specific active session for user {user_id}: engine {engine_session['engine_id']}")

    live_engine_sids = app.get_live_engine_sids() # This is { engine_id: sid }

    if engine_id_str in live_engine_sids:
        engine_session['live_sid'] = live_engine_sids[engine_id_str]
        engine_session['is_live'] = True
        logger.debug(f"[Helper] Specific Engine {engine_id_str} is LIVE with SID {engine_session['live_sid']}")
    else:
        engine_session['is_live'] = False
        engine_session['live_sid'] = None
        logger.warning(f"[Helper] Specific Engine {engine_id_str} is DB-active but NOT LIVE.")

    return engine_session


async def forward_request_to_engine(engine_session, request_data):
    """
    Forwards a request (as a dictionary) to the internal API of a live engine.
    """
    if not engine_session or not engine_session.get('is_live'):
        return {"error": "Engine is not connected or session is invalid."}

    internal_url = engine_session.get('internal_api_url')
    if not internal_url:
        return {"error": "Engine session is missing the internal API URL."}

    engine_api_url = f"{internal_url.rstrip('/')}/api/v1/workflow/execute_raw"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(engine_api_url, json=request_data, timeout=30) as response:

                response.raise_for_status() # Raises HTTPError for 4xx/5xx

                response_json = await response.json()
                logger.info(f"[Helper] Successfully forwarded request to {engine_api_url}, received response.")
                return response_json

    except aiohttp.ClientConnectorError as e:
        logger.error(f"[Helper] Cannot connect to engine at {engine_api_url}. Error: {e}")
        return {"error": f"Cannot connect to the engine's internal API. {e}"}
    except aiohttp.ClientResponseError as e:
        logger.error(f"[Helper] Engine at {engine_api_url} returned an error. Status: {e.status}, Message: {e.message}")
        try:
            error_detail = await response.json()
            return {"error": f"Engine API returned status {e.status}.", "details": error_detail}
        except Exception:
            return {"error": f"Engine API returned status {e.status}. {e.message}"}
    except Exception as e:
        logger.error(f"[Helper] Failed to forward request to engine {engine_api_url}. Error: {e}")
        return {"error": f"An unexpected error occurred while forwarding the request. {e}"}

async def forward_http_request_to_engine_api(engine_session, original_request):
    """
    Forwards a Flask HTTP request (GET, POST, etc.) to the engine's internal API.
    """
    if not engine_session or not engine_session.get('internal_api_url'):
        logger.error("[Helper] Engine session not found or missing internal_api_url.")
        return ({"error": "Active engine is not available or not configured."}, 503)

    internal_url = engine_session['internal_api_url'].rstrip('/')

    if not original_request.path.startswith('/api/v1/engine-proxy/'):
        logger.error(f"Invalid proxy path: {original_request.path}")
        return ({"error": "Invalid proxy request path."}, 400)

    engine_path = original_request.path[len('/api/v1/engine-proxy/'):]
    target_url = f"{internal_url}/{engine_path}"

    if original_request.query_string:
        target_url += f"?{original_request.query_string.decode('utf-8')}"

    internal_api_key = os.environ.get("FLOWORK_INTERNAL_API_KEY", "flwk_dev_default_internal_key")

    headers = {key: value for (key, value) in original_request.headers if key.lower() not in ['host', 'content-length']}
    headers['X-Forwarded-For'] = original_request.remote_addr
    headers['X-Flowork-Gateway-User'] = engine_session.get('user_id', 'unknown')
    headers['X-Internal-API-Key'] = internal_api_key

    data = None
    json_data = None
    if original_request.method in ['POST', 'PUT', 'PATCH']:
        if original_request.is_json:
            json_data = original_request.get_json()
        else:
            data = original_request.get_data() # Raw binary data

    logger.info(f"[Helper] Forwarding HTTP {original_request.method} to: {target_url}")

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.request(
                method=original_request.method,
                url=target_url,
                data=data,
                json=json_data,
                timeout=120, # 2 minute timeout for potentially long API calls
                allow_redirects=False
            ) as response:

                response_content = await response.read()

                excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
                response_headers = {
                    key: value for (key, value) in response.headers.items()
                    if key.lower() not in excluded_headers
                }

                logger.info(f"[Helper] Received {response.status} from engine API.")

                return (response_content, response.status, response_headers)

    except aiohttp.ClientConnectorError as e:
        logger.error(f"[Helper] Cannot connect to engine at {target_url}. Error: {e}")
        return ({"error": f"Cannot connect to the engine's internal API."}, 503, {})
    except aiohttp.ClientResponseError as e:
        logger.error(f"[Helper] Engine at {target_url} returned an error. Status: {e.status}, Message: {e.message}")
        return ({"error": f"Engine API returned status {e.status}: {e.message}"}, e.status, {})
    except Exception as e:
        logger.error(f"[Helper] Failed to forward HTTP request to engine {target_url}. Error: {e}")
        return ({"error": "An unexpected error occurred while proxying the request."}, 500, {})

def engine_api_proxy_decorator(f):
    """
    Decorator for routes that need to be proxied to the active engine.
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return ({"error": "Authorization header is missing or invalid."}, 401)

        token = auth_header.split(' ')[1]
        user_id = get_user_id_from_token(token)
        if not user_id:
            return ({"error": "Invalid or expired token."}, 401)

        engine_session = await find_active_engine_session_by_user_id(user_id)

        if not engine_session:
            return ({"error": "No active engine session found for this user."}, 404)

        if not engine_session.get('is_live'):
            return ({"error": "The active engine is not currently connected to the Gateway."}, 503) # 503 Service Unavailable

        if not engine_session.get('internal_api_url'):
            return ({"error": "Engine session is misconfigured (missing internal API URL)."}, 500)

        return await f(engine_session=engine_session, *args, **kwargs)

    return decorated_function
