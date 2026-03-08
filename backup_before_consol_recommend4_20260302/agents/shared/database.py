"""
SQLite database connection and helper functions.

Provides:
- Database connection management
- Schema initialization
- CRUD operations for all tables
- Transaction safety
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from pathlib import Path


class Database:
    """SQLite database handler for agent system."""

    def __init__(self, db_path: str = "data/agent_system.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self._ensure_directory()
        self.connection = None

    def _ensure_directory(self):
        """Ensure database directory exists."""
        directory = os.path.dirname(self.db_path)
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """Context manager for database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def initialize_schema(self):
        """Create all tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Agent outputs tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_number INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL,
                    analysis_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(cycle_number)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_number INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL,
                    recommendation_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(cycle_number)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_implementations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_number INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL,
                    implementation_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    git_commit_hash TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(cycle_number)
                )
            """)

            # Approval tracking table (KEY TABLE for user review)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS approval_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    cycle_number INTEGER NOT NULL,
                    implementation_id INTEGER NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT,
                    auto_approved BOOLEAN NOT NULL,
                    test_coverage REAL,
                    risk_assessment TEXT,
                    critical_issues_count INTEGER,
                    git_commit_hash TEXT,
                    files_modified TEXT,
                    changes_summary TEXT,
                    user_reviewed BOOLEAN DEFAULT FALSE,
                    user_reviewed_timestamp DATETIME,
                    user_review_comments TEXT,
                    rollback_available BOOLEAN DEFAULT TRUE,
                    rollback_hash TEXT,
                    rollback_command TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(cycle_number)
                )
            """)

            # Audit trail table (event log)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    cycle_number INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    agent_name TEXT,
                    phase TEXT,
                    event_data_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Workflow state table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orchestrator_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_number INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL,
                    workflow_state_json TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(cycle_number)
                )
            """)

            # Configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cycle_number ON agent_analyses(cycle_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_approval_cycle ON approval_history(cycle_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_approval_user_reviewed ON approval_history(user_reviewed)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_cycle ON audit_trail(cycle_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_trail(event_type)")

            conn.commit()

    def save_analysis(self, cycle_number: int, analysis_json: str) -> int:
        """Save analysis to database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_analyses (cycle_number, timestamp, analysis_json, status)
                VALUES (?, ?, ?, ?)
            """, (cycle_number, datetime.utcnow().isoformat() + "Z", analysis_json, "COMPLETED"))
            conn.commit()
            return cursor.lastrowid

    def save_recommendation(self, cycle_number: int, recommendation_json: str) -> int:
        """Save recommendation to database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_recommendations (cycle_number, timestamp, recommendation_json, status)
                VALUES (?, ?, ?, ?)
            """, (cycle_number, datetime.utcnow().isoformat() + "Z", recommendation_json, "COMPLETED"))
            conn.commit()
            return cursor.lastrowid

    def save_implementation(self, cycle_number: int, implementation_json: str, git_hash: Optional[str] = None) -> int:
        """Save implementation to database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_implementations (cycle_number, timestamp, implementation_json, status, git_commit_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (cycle_number, datetime.utcnow().isoformat() + "Z", implementation_json, "COMPLETED", git_hash))
            conn.commit()
            return cursor.lastrowid

    def save_approval(self, approval_record: Dict[str, Any]) -> int:
        """Save approval decision to database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO approval_history (
                    timestamp, cycle_number, implementation_id, decision, reason,
                    auto_approved, test_coverage, risk_assessment, critical_issues_count,
                    git_commit_hash, files_modified, changes_summary, rollback_hash, rollback_command
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                approval_record.get("timestamp"),
                approval_record.get("cycle"),
                approval_record.get("implementation_id", 0),
                approval_record.get("decision"),
                approval_record.get("reason", ""),
                approval_record.get("auto_approved", False),
                approval_record.get("test_coverage", 0.0),
                approval_record.get("risk_assessment", "UNKNOWN"),
                approval_record.get("critical_issues_count", 0),
                approval_record.get("git_commit_hash", ""),
                json.dumps(approval_record.get("files_modified", [])),
                approval_record.get("changes_summary", ""),
                approval_record.get("rollback_hash", ""),
                approval_record.get("rollback_command", "")
            ))
            conn.commit()
            return cursor.lastrowid

    def log_audit_event(self, event_data: Dict[str, Any]) -> int:
        """Log audit trail event."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_trail (timestamp, cycle_number, event_type, agent_name, phase, event_data_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_data.get("timestamp"),
                event_data.get("cycle_number"),
                event_data.get("event"),
                event_data.get("agent", ""),
                event_data.get("phase", ""),
                json.dumps(event_data.get("details", {}))
            ))
            conn.commit()
            return cursor.lastrowid

    def get_analysis(self, cycle_number: int) -> Optional[Dict[str, Any]]:
        """Get analysis for cycle."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_analyses WHERE cycle_number = ?", (cycle_number,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "cycle_number": row[1],
                    "timestamp": row[2],
                    "analysis_json": json.loads(row[3]),
                    "status": row[4]
                }
            return None

    def get_latest_analysis(self) -> Optional[Dict[str, Any]]:
        """Get latest completed analysis."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_analyses
                WHERE status = 'COMPLETED'
                ORDER BY cycle_number DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "cycle_number": row[1],
                    "timestamp": row[2],
                    "analysis_json": json.loads(row[3]),
                    "status": row[4]
                }
            return None

    def get_latest_recommendation(self) -> Optional[Dict[str, Any]]:
        """Get latest completed recommendation."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_recommendations
                WHERE status = 'COMPLETED'
                ORDER BY cycle_number DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "cycle_number": row[1],
                    "timestamp": row[2],
                    "recommendation_json": json.loads(row[3]),
                    "status": row[4]
                }
            return None

    def get_latest_implementation(self) -> Optional[Dict[str, Any]]:
        """Get latest completed implementation."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_implementations
                WHERE status = 'COMPLETED'
                ORDER BY cycle_number DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "cycle_number": row[1],
                    "timestamp": row[2],
                    "implementation_json": json.loads(row[3]),
                    "status": row[4],
                    "git_commit_hash": row[5]
                }
            return None

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approvals awaiting user review."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM approval_history
                WHERE user_reviewed = FALSE AND decision = 'PENDING'
                ORDER BY timestamp DESC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_approval_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get approval history."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM approval_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_approval_decision(self, cycle_number: int, decision: str, user_comments: Optional[str] = None) -> bool:
        """Update approval decision after user review."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE approval_history
                SET decision = ?, user_reviewed = TRUE, user_reviewed_timestamp = ?, user_review_comments = ?
                WHERE cycle_number = ?
            """, (decision, datetime.utcnow().isoformat() + "Z", user_comments, cycle_number))
            conn.commit()
            return cursor.rowcount > 0

    def get_audit_trail(self, cycle_number: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit trail events."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if cycle_number:
                cursor.execute("""
                    SELECT * FROM audit_trail
                    WHERE cycle_number = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (cycle_number, limit))
            else:
                cursor.execute("""
                    SELECT * FROM audit_trail
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def set_config(self, key: str, value: str):
        """Set configuration value."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.utcnow().isoformat() + "Z"))
            conn.commit()

    def get_config(self, key: str) -> Optional[str]:
        """Get configuration value."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def health_check(self) -> bool:
        """Check database health."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False


# Global database instance
_db_instance: Optional[Database] = None


def get_database(db_path: str = "data/agent_system.db") -> Database:
    """Get or create global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
        _db_instance.initialize_schema()
    return _db_instance
