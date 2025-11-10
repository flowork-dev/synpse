########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\db\pragma.py total lines 77 
########################################################################

import logging
import os
import sqlite3
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
log = logging.getLogger(__name__)
PRAGMAS = [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA busy_timeout=5000;",
    "PRAGMA cache_size=-8000;",  # ~8MB
    "PRAGMA temp_store=MEMORY;",
]
def _apply_pragmas_on_connect(dbapi_connection, connection_record):
    """
    (English Hardcode) Issues PRAGMA statements on a new SQLite connection.
    """
    try:
        cursor = dbapi_connection.cursor()
        for pragma in PRAGMAS:
            cursor.execute(pragma)
        cursor.close()
        log.debug("[PRAGMA] Applied SQLite PRAGMAs (WAL, Normal Sync).")
    except Exception as e:
        log.error(f"[PRAGMA] Failed to apply SQLite PRAGMAs: {e}")
def init_pragma(app: Flask, db_instance: SQLAlchemy):
    """
    (English Hardcode) Registers the PRAGMA event listener.
    This is the function app/__init__.py is looking for.
    """
    try:
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if db_uri.startswith("sqlite"):
            @event.listens_for(db_instance.engine, "connect")
            def on_connect(dbapi_con, con_record):
                _apply_pragmas_on_connect(dbapi_con, con_record)
            log.info("[PRAGMA] SQLite 'connect' event listener registered.")
        else:
            log.info(f"[PRAGMA] Skipping WAL pragmas for non-SQLite DB: {db_uri.split('://')[0]}")
    except Exception as e:
        log.warning(f"[PRAGMA] Failed to register 'connect' listener (expected during init): {e}")
def apply_pragma_on_connect(engine: Engine):
     """
     (English Hardcode) Legacy function for manage.py
     """
     if engine.driver == 'sqlite':
         try:
             with engine.connect() as conn:
                 for pragma_stmt in PRAGMAS:
                     conn.execute(text(pragma_stmt))
             log.info("[PRAGMA] apply_pragma_on_connect executed (legacy).")
         except Exception as e:
             log.error(f"[PRAGMA] Legacy apply_pragma_on_connect failed: {e}")
def apply_sqlite_pragmas(db_path: str):
    """
    (English Hardcode) Original function from user's file, kept for any
    other potential dependencies.
    """
    if not os.path.exists(db_path):
        return
    try:
        con = sqlite3.connect(db_path, timeout=5.0, isolation_level=None)
        cur = con.cursor()
        for pragma in PRAGMAS:
            cur.execute(pragma)
        con.commit()
        con.close()
    except Exception as e:
        log.error(f"[PRAGMA] Standalone apply_sqlite_pragmas failed: {e}")
