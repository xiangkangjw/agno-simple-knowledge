"""Operation management system with SQLite persistence for long-running operations."""

import asyncio
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from .config import config

logger = logging.getLogger(__name__)


class OperationManager:
    """Manages long-running operations with SQLite persistence."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the operation manager.

        Args:
            db_path: Path to SQLite database file. If None, uses config value.
        """
        if db_path is None:
            db_path = config.get('operations.database_file', 'tmp/operations.db')

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Initialize the SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    total_items INTEGER,
                    processed_items INTEGER,
                    failed_items INTEGER,
                    current_item TEXT,
                    result TEXT,
                    error TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON operations(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status
                ON operations(status)
            """)
            conn.commit()
        logger.info(f"Operations database initialized at {self.db_path}")

    async def create_operation(
        self,
        operation_type: str,
        total_items: Optional[int] = None
    ) -> str:
        """Create a new operation.

        Args:
            operation_type: Type of operation (e.g., 'refresh_index', 'add_documents')
            total_items: Total number of items to process (optional)

        Returns:
            Operation ID
        """
        operation_id = f"{operation_type}-{uuid.uuid4().hex[:8]}"
        now = datetime.now().timestamp()

        def _insert():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO operations
                    (id, operation_type, status, created_at, updated_at, total_items, processed_items, failed_items)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (operation_id, operation_type, 'pending', now, now, total_items, 0, 0))
                conn.commit()

        await asyncio.to_thread(_insert)
        logger.info(f"Created operation {operation_id}")
        return operation_id

    async def start_operation(self, operation_id: str) -> None:
        """Mark operation as started.

        Args:
            operation_id: Operation ID to start
        """
        now = datetime.now().timestamp()

        def _update():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE operations
                    SET status = ?, started_at = ?, updated_at = ?
                    WHERE id = ?
                """, ('running', now, now, operation_id))
                conn.commit()

        await asyncio.to_thread(_update)
        logger.info(f"Started operation {operation_id}")

    async def update_progress(
        self,
        operation_id: str,
        processed_items: Optional[int] = None,
        failed_items: Optional[int] = None,
        current_item: Optional[str] = None
    ) -> None:
        """Update operation progress.

        Args:
            operation_id: Operation ID to update
            processed_items: Number of items processed
            failed_items: Number of items failed
            current_item: Current item being processed
        """
        now = datetime.now().timestamp()

        def _update():
            updates = []
            params = []

            if processed_items is not None:
                updates.append("processed_items = ?")
                params.append(processed_items)

            if failed_items is not None:
                updates.append("failed_items = ?")
                params.append(failed_items)

            if current_item is not None:
                updates.append("current_item = ?")
                params.append(current_item)

            if not updates:
                return

            updates.append("updated_at = ?")
            params.append(now)
            params.append(operation_id)

            query = f"UPDATE operations SET {', '.join(updates)} WHERE id = ?"

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(query, params)
                conn.commit()

        await asyncio.to_thread(_update)

    async def complete_operation(
        self,
        operation_id: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark operation as completed successfully.

        Args:
            operation_id: Operation ID to complete
            result: Result data to store (will be JSON serialized)
        """
        now = datetime.now().timestamp()
        result_json = json.dumps(result) if result else None

        def _update():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE operations
                    SET status = ?, completed_at = ?, updated_at = ?, result = ?
                    WHERE id = ?
                """, ('completed', now, now, result_json, operation_id))
                conn.commit()

        await asyncio.to_thread(_update)
        logger.info(f"Completed operation {operation_id}")

    async def fail_operation(
        self,
        operation_id: str,
        error: str
    ) -> None:
        """Mark operation as failed.

        Args:
            operation_id: Operation ID to fail
            error: Error message
        """
        now = datetime.now().timestamp()

        def _update():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE operations
                    SET status = ?, completed_at = ?, updated_at = ?, error = ?
                    WHERE id = ?
                """, ('failed', now, now, error, operation_id))
                conn.commit()

        await asyncio.to_thread(_update)
        logger.error(f"Failed operation {operation_id}: {error}")

    async def cancel_operation(self, operation_id: str) -> None:
        """Mark operation as cancelled.

        Args:
            operation_id: Operation ID to cancel
        """
        now = datetime.now().timestamp()

        def _update():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE operations
                    SET status = ?, completed_at = ?, updated_at = ?
                    WHERE id = ? AND status IN ('pending', 'running')
                """, ('cancelled', now, now, operation_id))
                conn.commit()

        await asyncio.to_thread(_update)
        logger.info(f"Cancelled operation {operation_id}")

    async def get_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get operation details.

        Args:
            operation_id: Operation ID to retrieve

        Returns:
            Operation details or None if not found
        """
        def _fetch():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM operations WHERE id = ?
                """, (operation_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                op_dict = dict(row)
                # Parse JSON fields
                if op_dict['result']:
                    op_dict['result'] = json.loads(op_dict['result'])

                return op_dict

        return await asyncio.to_thread(_fetch)

    async def list_operations(
        self,
        limit: int = 50,
        status: Optional[str] = None
    ) -> list:
        """List recent operations.

        Args:
            limit: Maximum number of operations to return
            status: Filter by status (optional)

        Returns:
            List of operations
        """
        def _fetch():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                if status:
                    query = "SELECT * FROM operations WHERE status = ? ORDER BY created_at DESC LIMIT ?"
                    cursor = conn.execute(query, (status, limit))
                else:
                    query = "SELECT * FROM operations ORDER BY created_at DESC LIMIT ?"
                    cursor = conn.execute(query, (limit,))

                rows = cursor.fetchall()
                operations = []

                for row in rows:
                    op_dict = dict(row)
                    if op_dict['result']:
                        op_dict['result'] = json.loads(op_dict['result'])
                    operations.append(op_dict)

                return operations

        return await asyncio.to_thread(_fetch)

    async def cleanup_old_operations(self, hours: Optional[int] = None) -> int:
        """Clean up operations older than specified hours.

        Args:
            hours: Hours to keep (default from config). Operations older than this are deleted.

        Returns:
            Number of operations deleted
        """
        if hours is None:
            hours = config.get('operations.cleanup_after_hours', 24)

        cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()

        def _delete():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM operations
                    WHERE completed_at IS NOT NULL AND created_at < ?
                """, (cutoff_time,))
                conn.commit()
                return cursor.rowcount

        deleted = await asyncio.to_thread(_delete)
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old operations")

        return deleted

    async def get_operation_status(self, operation_id: str) -> Optional[str]:
        """Get current status of an operation.

        Args:
            operation_id: Operation ID

        Returns:
            Status string or None if not found
        """
        op = await self.get_operation(operation_id)
        return op['status'] if op else None
