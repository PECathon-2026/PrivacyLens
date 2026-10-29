"""
Database Models and SQLite Storage Layer for PrivacyLens.
Stores strictly non-sensitive audit logs, task states, and metrics.
NEVER records raw passwords, cards, identity values, or secret mappings.
"""

import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path
from Core.contracts import AuditEvent


class AuditDatabase:
    """
    Local SQLite repository for non-sensitive operational auditing.
    Adheres strictly to docs/DATABASE_SCHEMA.md guidelines.
    """

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            db_dir = Path(__file__).parent.parent / "database"
            db_dir.mkdir(exist_ok=True)
            self.db_path = str(db_dir / "privacylens_audit.sqlite3")
        else:
            self.db_path = db_path

        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def init_db(self):
        """Initializes tables adhering to docs/DATABASE_SCHEMA.md."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Tasks Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL CHECK (
                    status IN ('created', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled')
                ),
                task_label TEXT,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT,
                error_code TEXT
            );
            """)

            # 2. Privacy Events Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS privacy_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                category TEXT,
                item_count INTEGER NOT NULL DEFAULT 0,
                decision TEXT,
                duration_ms INTEGER,
                error_code TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            );
            """)

            # 3. Action Events Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_events (
                action_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target_element_id TEXT,
                validation_status TEXT NOT NULL CHECK (
                    validation_status IN ('approved', 'rejected', 'pending')
                ),
                approval_required INTEGER NOT NULL DEFAULT 0,
                approval_status TEXT,
                reason_code TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            );
            """)

            conn.commit()

    def create_task(self, task_id: str, task_label: str) -> None:
        """Records task creation metadata."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tasks (task_id, status, task_label) VALUES (?, 'running', ?)",
                (task_id, task_label)
            )
            conn.commit()

    def record_privacy_event(self, event: AuditEvent) -> None:
        """Records a non-sensitive audit event (counts and decisions only)."""
        with self._get_connection() as conn:
            # Ensure task exists
            conn.execute(
                "INSERT OR IGNORE INTO tasks (task_id, status, task_label) VALUES (?, 'running', 'Task')",
                (event.task_id,)
            )
            conn.execute(
                """INSERT INTO privacy_events (task_id, event_type, category, item_count, decision, error_code)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    event.task_id,
                    event.event_type,
                    event.category,
                    event.item_count,
                    event.decision,
                    event.error_code,
                )
            )
            conn.commit()

    def get_task_events(self, task_id: str) -> List[Dict[str, Any]]:
        """Retrieves audit trail for a specific task."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM privacy_events WHERE task_id = ? ORDER BY created_at DESC",
                (task_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

