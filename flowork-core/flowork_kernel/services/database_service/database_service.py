########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\database_service\database_service.py total lines 156 
########################################################################

import sqlite3
import logging
import os
import threading
from flowork_kernel.singleton import Singleton # (ADDED) Import Singleton
from typing import Set # <-- START ADDED CODE (FIX - Self-Healing)
class DatabaseService(metaclass=Singleton):
    def __init__(self, db_name='core.db'): # English Hardcode
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initializing DatabaseService...") # English Hardcode
        core_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.data_dir = os.path.join(core_root, 'data')
        self.db_path = os.path.join(self.data_dir, db_name)
        os.makedirs(self.data_dir, exist_ok=True)
        self.logger.info(f"Database path set to: {self.db_path}") # English Hardcode
        self.initialize_database()
    def _get_existing_columns(self, cursor: sqlite3.Cursor, table_name: str) -> Set[str]:
        """(English Hardcode) Helper function to get all column names from a table."""
        try:
            cursor.execute(f"PRAGMA table_info({table_name});")
            return {row[1] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            self.logger.warning(f"Could not get table info for {table_name}: {e}") # English Hardcode
            return set()
    def _ensure_backward_compatible_columns(self, conn: sqlite3.Connection, cursor: sqlite3.Cursor):
        """
        (English Hardcode) (FIX - Self-Healing) Non-destructively adds missing columns to the Jobs table
        if an old database file is mounted via bind mount.
        """
        try:
            self.logger.info("Running non-destructive schema validation...") # English Hardcode
            jobs_columns = self._get_existing_columns(cursor, "Jobs")
            if "workflow_id" not in jobs_columns:
                self.logger.warning("Column 'workflow_id' missing from Jobs table. Adding it now...") # English Hardcode
                cursor.execute("ALTER TABLE Jobs ADD COLUMN workflow_id TEXT")
            if "user_id" not in jobs_columns:
                self.logger.warning("Column 'user_id' missing from Jobs table. Adding it now...") # English Hardcode
                cursor.execute("ALTER TABLE Jobs ADD COLUMN user_id TEXT")
            executions_columns = self._get_existing_columns(cursor, "Executions")
            if "user_id" not in executions_columns:
                 self.logger.warning("Column 'user_id' missing from Executions table. Adding it now...") # English Hardcode
                 cursor.execute("ALTER TABLE Executions ADD COLUMN user_id TEXT")
            conn.commit()
            self.logger.info("Schema validation complete.") # English Hardcode
        except sqlite3.Error as e:
            self.logger.error(f"Failed to run self-healing migration: {e}", exc_info=True) # English Hardcode
            conn.rollback()
    def initialize_database(self):
        """
        (Per Roadmap 2/8 & 6/8)
        Initializes the database, enables WAL mode, and ensures
        all necessary DAG tables exist.
        """
        try:
            conn = self.create_connection()
            if not conn:
                 raise sqlite3.Error("Failed to create initial connection.") # English Hardcode
            cursor = conn.cursor()
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=5000;")
            cursor.execute("PRAGMA cache_size=-8000;")
            cursor.execute("PRAGMA temp_store=MEMORY;")
            self.logger.info(f"Database journal mode set to WAL for: {self.db_path}") # English Hardcode
            self.logger.info("Ensuring DAG schema exists (Workflows, Nodes, Edges)...") # English Hardcode
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Workflows (
                workflow_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Nodes (
                node_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                node_type TEXT NOT NULL,
                config_json TEXT,
                FOREIGN KEY (workflow_id) REFERENCES Workflows (workflow_id)
            );
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Edges (
                edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                source_node_id TEXT NOT NULL,
                target_node_id TEXT NOT NULL,
                FOREIGN KEY (workflow_id) REFERENCES Workflows (workflow_id),
                FOREIGN KEY (source_node_id) REFERENCES Nodes (node_id),
                FOREIGN KEY (target_node_id) REFERENCES Nodes (node_id)
            );
            ''')
            self.logger.info("Ensuring reliable Job Queue schema exists (Executions, Jobs)...") # English Hardcode
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Executions (
                execution_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'RUNNING',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                finished_at DATETIME
            );
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Jobs (
                job_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                input_data TEXT,
                output_data TEXT,
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                finished_at DATETIME,
                FOREIGN KEY (execution_id) REFERENCES Executions (execution_id) ON DELETE CASCADE
            );
            ''')
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON Jobs (status, created_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_workflow_user ON Executions (workflow_id, user_id);")
            self._ensure_backward_compatible_columns(conn, cursor)
            conn.commit()
            conn.close()
            self.logger.info(f"Database (core.db) initialized with WAL mode and DAG schema.") # English Hardcode
        except sqlite3.Error as e:
            self.logger.error(f"Error initializing core database: {e}") # English Hardcode
    def create_connection(self):
        """
        (Per Roadmap 2/8)
        Creates and configures a new, worker-safe SQLite connection.
        This is the 'factory function' recommended in the .docx.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.execute('PRAGMA journal_mode=WAL;') # (ADDED) Ensure WAL mode on every connection
            conn.execute('PRAGMA synchronous=NORMAL;')
            conn.execute('PRAGMA foreign_keys=ON;')
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA cache_size=-8000;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            self.logger.debug("Core DB connection created (WAL, 5s timeout, sync=NORMAL, busy=5000).") # English Hardcode
            return conn
        except sqlite3.Error as e:
            self.logger.error(f"Error creating core database connection: {e}") # English Hardcode
            if conn:
                conn.close()
            return None
