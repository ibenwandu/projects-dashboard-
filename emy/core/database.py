"""
Emy SQLite database connection and schema management.

Extends Trade-Alerts Database pattern with Emy-specific tables for:
- Task orchestration and history
- Sub-agent execution tracking
- Skill outcome logging and self-improvement
- Approval request tracking
- Scheduled job history
- Job application tracking
- API spending and budget management
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from pathlib import Path


class EMyDatabase:
    """SQLite database handler for Emy agent system."""

    def __init__(self, db_path: str = "emy/data/emy.db"):
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

            # Emy tasks (main task queue and history)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emy_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,  -- 'scheduler' | 'user' | 'internal'
                    domain TEXT NOT NULL,  -- 'trading' | 'job_search' | 'knowledge' | 'project_monitor'
                    task_type TEXT NOT NULL,  -- 'monitor' | 'execute' | 'update' | etc
                    status TEXT NOT NULL,  -- 'pending' | 'in_progress' | 'completed' | 'failed'
                    description TEXT,
                    result_json TEXT,  -- JSON result data
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)

            # Sub-agent execution log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sub_agent_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    agent_name TEXT NOT NULL,  -- 'TradingAgent' | 'JobSearchAgent' | etc
                    model TEXT NOT NULL,  -- 'claude-haiku-4-5-20251001' | 'claude-sonnet-4-6'
                    status TEXT NOT NULL,  -- 'success' | 'failed' | 'timeout'
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost_usd REAL,
                    error_message TEXT,
                    result_summary TEXT,
                    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES emy_tasks(id)
                )
            """)

            # Skill outcomes (for self-improvement)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    success BOOLEAN NOT NULL,  -- 1 | 0
                    notes TEXT,
                    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    run_duration_seconds REAL
                )
            """)

            # Approval requests for destructive actions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,  -- 'git_push' | 'delete_file' | etc
                    domain TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,  -- 'pending' | 'approved' | 'rejected'
                    resolution_notes TEXT,
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP
                )
            """)

            # Scheduled task run history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedule_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name TEXT NOT NULL,  -- 'render_health_check' | 'job_search_daily' | etc
                    scheduled_time TIMESTAMP NOT NULL,
                    actual_start_time TIMESTAMP,
                    actual_end_time TIMESTAMP,
                    status TEXT NOT NULL,  -- 'scheduled' | 'running' | 'completed' | 'failed'
                    result_json TEXT,
                    error_message TEXT
                )
            """)

            # Job application tracker
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,  -- 'linkedin' | 'indeed' | 'glassdoor' | etc
                    track TEXT NOT NULL,  -- 'analyst' | 'pm' | 'ops' | 'cs'
                    job_title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    status TEXT NOT NULL,  -- 'found' | 'scored' | 'tailored' | 'applied' | 'rejected'
                    score REAL,  -- 0.0-1.0 relevance score
                    application_date TIMESTAMP,
                    job_url TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # API spending and budget tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_spend (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model TEXT NOT NULL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost_usd REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Workflow execution and output persistence
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,  -- 'knowledge_query' | 'trading_analysis' | 'job_search' | etc
                    status TEXT NOT NULL,  -- 'pending' | 'in_progress' | 'complete' | 'error'
                    input TEXT,  -- Input data for the workflow
                    output TEXT,  -- Output/result data
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Alert history for badge tracking and persistence
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    sent_at TEXT NOT NULL,
                    read_at TEXT DEFAULT NULL
                )
            """)

            conn.commit()

        # Create OANDA-specific tables
        self._create_oanda_trades_table()
        self._create_oanda_limits_table()

    def log_task(self, source: str, domain: str, task_type: str,
                 description: str = None) -> int:
        """Create a new task record and return task_id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO emy_tasks (source, domain, task_type, status, description)
                VALUES (?, ?, ?, 'pending', ?)
            """, (source, domain, task_type, description))
            return cursor.lastrowid

    def update_task(self, task_id: int, status: str, result_json: str = None,
                   error_message: str = None):
        """Update task status and results."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            if status == 'in_progress':
                cursor.execute("""
                    UPDATE emy_tasks
                    SET status = ?, started_at = ?
                    WHERE id = ?
                """, (status, now, task_id))
            elif status in ['completed', 'failed']:
                cursor.execute("""
                    UPDATE emy_tasks
                    SET status = ?, completed_at = ?, result_json = ?, error_message = ?
                    WHERE id = ?
                """, (status, now, result_json, error_message, task_id))
            else:
                cursor.execute("""
                    UPDATE emy_tasks
                    SET status = ?
                    WHERE id = ?
                """, (status, task_id))
            conn.commit()

    def log_agent_run(self, task_id: int, agent_name: str, model: str,
                     status: str, input_tokens: int = 0, output_tokens: int = 0,
                     cost_usd: float = 0.0, error_message: str = None,
                     result_summary: str = None):
        """Log a sub-agent execution."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sub_agent_runs
                (task_id, agent_name, model, status, input_tokens, output_tokens,
                 cost_usd, error_message, result_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task_id, agent_name, model, status, input_tokens, output_tokens,
                  cost_usd, error_message, result_summary))
            conn.commit()

    def log_skill_outcome(self, skill_name: str, version: str, domain: str,
                         success: bool, notes: str = None,
                         duration_seconds: float = None):
        """Log a skill execution outcome (for self-improvement)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO skill_outcomes
                (skill_name, version, domain, success, notes, run_duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (skill_name, version, domain, int(success), notes, duration_seconds))
            conn.commit()

    def get_skill_success_rate(self, skill_name: str, window_runs: int = 5) -> float:
        """Get recent success rate for a skill (for self-improvement triggering)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(success) as wins, COUNT(*) as total
                FROM (
                    SELECT success FROM skill_outcomes
                    WHERE skill_name = ?
                    ORDER BY run_timestamp DESC
                    LIMIT ?
                )
            """, (skill_name, window_runs))
            row = cursor.fetchone()
            if row['total'] == 0:
                return 1.0  # No data = assume success
            return row['wins'] / row['total']

    def log_approval_request(self, action_type: str, domain: str,
                            description: str) -> int:
        """Create an approval request for destructive action."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO approval_requests
                (action_type, domain, description, status)
                VALUES (?, ?, ?, 'pending')
            """, (action_type, domain, description))
            return cursor.lastrowid

    def update_approval_request(self, request_id: int, status: str,
                               resolution_notes: str = None):
        """Update approval request status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE approval_requests
                SET status = ?, resolution_notes = ?, resolved_at = ?
                WHERE id = ?
            """, (status, resolution_notes, now, request_id))
            conn.commit()

    def get_approval_request(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific approval request."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM approval_requests WHERE id = ?
            """, (request_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def auto_reject_expired_approvals(self, cutoff_time: datetime) -> int:
        """Auto-reject approvals older than cutoff_time that are still pending."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_iso = cutoff_time.isoformat()
            cursor.execute("""
                UPDATE approval_requests
                SET status = 'auto_rejected', resolution_notes = 'Timeout (24h)'
                WHERE status = 'pending' AND requested_at < ?
            """, (cutoff_iso,))
            conn.commit()
            return cursor.rowcount

    def resolve_approval(self, request_id: int, approved: bool, notes: str = None):
        """Resolve an approval request (legacy method for compatibility)."""
        status = 'approved' if approved else 'rejected'
        self.update_approval_request(request_id, status, notes)

    def log_scheduled_run(self, job_name: str, scheduled_time: str):
        """Log a scheduled job (before execution)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedule_runs (job_name, scheduled_time, status)
                VALUES (?, ?, 'scheduled')
            """, (job_name, scheduled_time))
            return cursor.lastrowid

    def update_scheduled_run(self, run_id: int, status: str, result_json: str = None,
                            error_message: str = None):
        """Update a scheduled job run after execution."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            if status == 'running':
                cursor.execute("""
                    UPDATE schedule_runs
                    SET status = ?, actual_start_time = ?
                    WHERE id = ?
                """, (status, now, run_id))
            else:
                cursor.execute("""
                    UPDATE schedule_runs
                    SET status = ?, actual_end_time = ?, result_json = ?, error_message = ?
                    WHERE id = ?
                """, (status, now, result_json, error_message, run_id))
            conn.commit()

    def track_job_application(self, platform: str, track: str, job_title: str,
                             company: str, score: float = None, job_url: str = None) -> int:
        """Track a new job application."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO job_applications
                (platform, track, job_title, company, status, score, job_url)
                VALUES (?, ?, ?, ?, 'found', ?, ?)
            """, (platform, track, job_title, company, score, job_url))
            return cursor.lastrowid

    def log_api_spend(self, model: str, input_tokens: int, output_tokens: int,
                     cost_usd: float):
        """Log API usage and cost."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO api_spend (model, input_tokens, output_tokens, cost_usd)
                VALUES (?, ?, ?, ?)
            """, (model, input_tokens, output_tokens, cost_usd))
            conn.commit()

    def get_daily_spend(self, date: str = None) -> float:
        """Get total API spend for a day (default: today)."""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(cost_usd) as total
                FROM api_spend
                WHERE DATE(timestamp) = ?
            """, (date,))
            row = cursor.fetchone()
            return row['total'] or 0.0

    def set_config(self, key: str, value: str):
        """Store configuration value."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
            conn.commit()

    def get_config(self, key: str, default: str = None) -> Optional[str]:
        """Retrieve configuration value."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default

    def store_workflow_output(self, workflow_id: str, workflow_type: str,
                            status: str, output: str, input_data: str = None) -> bool:
        """
        Store workflow output to database.

        Args:
            workflow_id: Unique workflow identifier
            workflow_type: Type of workflow (knowledge, trading, job_search, etc.)
            status: Workflow status (complete, error, etc.)
            output: The workflow output/result
            input_data: Optional input data for the workflow

        Returns:
            True if stored successfully
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                # Try to update existing workflow first
                cursor.execute("""
                    SELECT workflow_id FROM workflows WHERE workflow_id = ?
                """, (workflow_id,))

                if cursor.fetchone():
                    # Update existing
                    cursor.execute("""
                        UPDATE workflows
                        SET status = ?, output = ?, updated_at = ?
                        WHERE workflow_id = ?
                    """, (status, output, now, workflow_id))
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO workflows
                        (workflow_id, type, status, input, output, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (workflow_id, workflow_type, status, input_data, output, now, now))

                conn.commit()
                return True

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error storing workflow output: {e}")
            return False

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve workflow from database.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            Workflow dict or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT workflow_id, type, status, input, output, created_at, updated_at
                    FROM workflows
                    WHERE workflow_id = ?
                """, (workflow_id,))

                row = cursor.fetchone()
                if row:
                    return {
                        "workflow_id": row['workflow_id'],
                        "type": row['type'],
                        "status": row['status'],
                        "input": row['input'],
                        "output": row['output'],
                        "created_at": row['created_at'],
                        "updated_at": row['updated_at']
                    }
                return None

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error retrieving workflow: {e}")
            return None

    def get_workflows(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List workflows with pagination, newest first.

        Args:
            limit: Number of results to return (1-100)
            offset: Number of results to skip

        Returns:
            List of workflow dicts
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT workflow_id, type, status, input, output, created_at, updated_at
                    FROM workflows
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error listing workflows: {e}")
            return []

    def count_workflows(self) -> int:
        """
        Return total count of workflows.

        Returns:
            Total workflow count
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as cnt FROM workflows")
                row = cursor.fetchone()
                return row['cnt'] if row else 0
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error counting workflows: {e}")
            return 0

    def _create_oanda_trades_table(self):
        """Create table for tracking OANDA trades."""
        with self.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS oanda_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE,
                account_id TEXT,
                symbol TEXT NOT NULL,
                units REAL NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                status TEXT DEFAULT 'OPEN',
                reason_rejected TEXT,
                opened_at TIMESTAMP,
                closed_at TIMESTAMP,
                pnl_usd REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_oanda_trades_status ON oanda_trades(status)")

    def _create_oanda_limits_table(self):
        """Create table for tracking risk limits per day."""
        with self.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS oanda_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                max_position_size INTEGER DEFAULT 10000,
                max_daily_loss_usd REAL DEFAULT 100.0,
                max_concurrent_positions INTEGER DEFAULT 5,
                daily_loss_usd REAL DEFAULT 0.0,
                concurrent_open_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_oanda_limits_date ON oanda_limits(date)")

    def log_oanda_trade(self, trade_id, account_id, symbol, units, direction, entry_price, stop_loss, take_profit, status='OPEN'):
        """Log a trade to oanda_trades table.

        Args:
            trade_id: OANDA trade ID (string)
            account_id: OANDA account ID
            symbol: Instrument (e.g., 'EUR_USD')
            units: Number of units (positive or negative)
            direction: 'BUY' or 'SELL'
            entry_price: Entry price
            stop_loss: SL price
            take_profit: TP price
            status: Trade status (default 'OPEN')

        Raises:
            ValueError: If trade_id already exists in database
        """
        try:
            with self.get_connection() as conn:
                conn.execute("""
                INSERT INTO oanda_trades
                (trade_id, account_id, symbol, units, direction, entry_price, stop_loss, take_profit, status, opened_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (trade_id, account_id, symbol, units, direction, entry_price, stop_loss, take_profit, status))
                conn.commit()
        except sqlite3.IntegrityError as e:
            raise ValueError(f"Trade {trade_id} already logged or database error: {e}") from e

    def log_trade_rejection(self, symbol, units, reason):
        """Log a rejected trade attempt.

        Args:
            symbol: Instrument (e.g., 'EUR_USD')
            units: Requested units
            reason: Why the trade was rejected

        Raises:
            RuntimeError: If database error occurs during logging
        """
        try:
            with self.get_connection() as conn:
                conn.execute("""
                INSERT INTO oanda_trades
                (symbol, units, direction, status, reason_rejected, opened_at)
                VALUES (?, ?, 'NONE', 'REJECTED', ?, CURRENT_TIMESTAMP)
                """, (symbol, units, reason))
                conn.commit()
        except sqlite3.IntegrityError as e:
            raise RuntimeError(f"Failed to log rejection for {symbol}: {e}") from e

    def get_daily_pnl(self, date=None):
        """Get total P&L for a specific date (default: today UTC).

        Args:
            date: YYYY-MM-DD format (default: today in UTC)

        Returns:
            float: Daily P&L in USD. Positive = profit, negative = loss
        """
        if date is None:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        with self.get_connection() as conn:
            cursor = conn.execute("""
            SELECT COALESCE(SUM(pnl_usd), 0) as daily_pnl FROM oanda_trades
            WHERE DATE(closed_at) = ? AND status = 'CLOSED'
            """, (date,))
            result = cursor.fetchone()
            return result[0] if result else 0.0

    def get_open_positions_count(self):
        """Count open positions.

        Returns:
            int: Number of open trades
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
            SELECT COUNT(*) FROM oanda_trades WHERE status = 'OPEN'
            """)
            result = cursor.fetchone()
            return result[0] if result else 0

    def get_max_daily_loss(self, date: str = None) -> float:
        """Get max daily loss limit for a date (default: today).

        Args:
            date: YYYY-MM-DD format (default: today in UTC)

        Returns:
            float: Max daily loss in USD (default 100.0)
        """
        if date is None:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT max_daily_loss_usd FROM oanda_limits WHERE date = ?",
                (date,)
            )
            row = cursor.fetchone()
            return row['max_daily_loss_usd'] if row else 100.0  # Default to 100 USD

    def get_max_position_size(self, date: str = None) -> int:
        """Get max position size limit for a date (default: today).

        Args:
            date: YYYY-MM-DD format (default: today in UTC)

        Returns:
            int: Max position size in units (default 10000)
        """
        if date is None:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT max_position_size FROM oanda_limits WHERE date = ?",
                (date,)
            )
            row = cursor.fetchone()
            return row['max_position_size'] if row else 10000  # Default to 10000 units

    def update_daily_limits(self):
        """Update daily limits tracking for today (call once at market close).

        Calculates and persists daily loss and open position count.
        Daily loss is calculated as max(0, -daily_pnl) to ensure losses are
        represented as positive values only when there is an actual loss.
        """
        today = datetime.utcnow().strftime('%Y-%m-%d')
        daily_pnl = self.get_daily_pnl(date=today)
        daily_loss = max(0, -daily_pnl)  # Convert negative P&L to positive loss only if loss
        open_count = self.get_open_positions_count()

        with self.get_connection() as conn:
            # Check if record exists for today
            cursor = conn.execute("SELECT id FROM oanda_limits WHERE date = ?", (today,))
            if cursor.fetchone():
                conn.execute("""
                UPDATE oanda_limits SET daily_loss_usd = ?, concurrent_open_count = ?
                WHERE date = ?
                """, (daily_loss, open_count, today))
            else:
                conn.execute("""
                INSERT INTO oanda_limits (date, daily_loss_usd, concurrent_open_count)
                VALUES (?, ?, ?)
                """, (today, daily_loss, open_count))
            conn.commit()

    def log_alert(self, alert_type: str, title: str, message: str,
                  priority: int = 0) -> int:
        """
        Insert sent alert to history. Return row id.

        Args:
            alert_type: Type of alert (e.g., 'trade_opened')
            title: Alert title
            message: Alert message
            priority: Alert priority (0=Normal, 1=High, 2=Emergency)

        Returns:
            Row ID of inserted alert
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO alert_history (alert_type, title, message, priority, sent_at)
                VALUES (?, ?, ?, ?, ?)
            """, (alert_type, title, message, priority, now))
            conn.commit()
            return cursor.lastrowid

    def get_unread_alerts(self, alert_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return unread alerts, optionally filtered by type.

        Args:
            alert_type: Optional filter by alert type. None returns all unread.

        Returns:
            List of alert records with unread (read_at IS NULL)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if alert_type:
                cursor.execute("""
                    SELECT * FROM alert_history
                    WHERE alert_type = ? AND read_at IS NULL
                    ORDER BY sent_at DESC
                """, (alert_type,))
            else:
                cursor.execute("""
                    SELECT * FROM alert_history
                    WHERE read_at IS NULL
                    ORDER BY sent_at DESC
                """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_alerts_read(self, alert_type: Optional[str] = None) -> int:
        """
        Set read_at for unread alerts. Return count updated.

        Args:
            alert_type: Optional filter by alert type. None marks all read.

        Returns:
            Count of alerts marked as read
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            if alert_type:
                cursor.execute("""
                    UPDATE alert_history
                    SET read_at = ?
                    WHERE alert_type = ? AND read_at IS NULL
                """, (now, alert_type))
            else:
                cursor.execute("""
                    UPDATE alert_history
                    SET read_at = ?
                    WHERE read_at IS NULL
                """, (now,))
            conn.commit()
            return cursor.rowcount
