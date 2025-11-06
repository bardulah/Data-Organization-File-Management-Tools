"""
Database module for state tracking, history, and undo functionality.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Database location
DB_DIR = Path.home() / '.fileorganizer'
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / 'fileorganizer.db'


class Database:
    """Manages SQLite database for operation tracking and undo."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to database file (defaults to ~/.fileorganizer/fileorganizer.db)
        """
        self.db_path = db_path or DB_PATH
        self.init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def init_database(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Operations table - tracks all file operations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    command TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT,
                    duration_seconds REAL
                )
            ''')

            # File operations table - detailed file-level operations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    destination_path TEXT,
                    file_size INTEGER,
                    file_hash TEXT,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    can_undo BOOLEAN DEFAULT 1,
                    FOREIGN KEY (operation_id) REFERENCES operations(id)
                )
            ''')

            # Scan cache table - for incremental scanning
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    directory TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_hash TEXT,
                    file_size INTEGER,
                    modified_time REAL,
                    last_scanned TEXT,
                    UNIQUE(directory, file_path)
                )
            ''')

            # Snapshots table - for backup/restore
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    directory TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    snapshot_data TEXT NOT NULL,
                    description TEXT
                )
            ''')

            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_operations_session
                ON operations(session_id)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_file_ops_operation
                ON file_operations(operation_id)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_scan_cache_directory
                ON scan_cache(directory)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_scan_cache_modified
                ON scan_cache(modified_time)
            ''')

            logger.info(f"Database initialized at {self.db_path}")

    def start_operation(self, session_id: str, command: str, operation_type: str, details: Optional[Dict] = None) -> int:
        """
        Start tracking a new operation.

        Args:
            session_id: Unique session identifier
            command: Command being executed
            operation_type: Type of operation (scan, organize, duplicate, etc.)
            details: Additional details as dictionary

        Returns:
            Operation ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO operations
                (session_id, timestamp, command, operation_type, status, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                datetime.now().isoformat(),
                command,
                operation_type,
                'in_progress',
                json.dumps(details) if details else None
            ))

            operation_id = cursor.lastrowid
            logger.info(f"Started operation {operation_id}: {command}")
            return operation_id

    def complete_operation(self, operation_id: int, status: str = 'completed', duration: Optional[float] = None):
        """
        Mark an operation as complete.

        Args:
            operation_id: Operation ID
            status: Final status (completed, failed, cancelled)
            duration: Duration in seconds
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE operations
                SET status = ?, duration_seconds = ?
                WHERE id = ?
            ''', (status, duration, operation_id))

            logger.info(f"Operation {operation_id} {status}")

    def log_file_operation(
        self,
        operation_id: int,
        action: str,
        source_path: str,
        destination_path: Optional[str] = None,
        file_size: Optional[int] = None,
        file_hash: Optional[str] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        can_undo: bool = True
    ):
        """
        Log a file-level operation.

        Args:
            operation_id: Parent operation ID
            action: Action performed (move, copy, delete, rename)
            source_path: Original file path
            destination_path: New file path (for move/copy/rename)
            file_size: File size in bytes
            file_hash: File hash
            status: Operation status
            error_message: Error message if failed
            can_undo: Whether operation can be undone
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO file_operations
                (operation_id, action, source_path, destination_path, file_size,
                 file_hash, status, error_message, can_undo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                operation_id, action, source_path, destination_path,
                file_size, file_hash, status, error_message, can_undo
            ))

            logger.debug(f"Logged file operation: {action} {source_path}")

    def get_operation_history(self, session_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Get operation history.

        Args:
            session_id: Filter by session ID (None for all sessions)
            limit: Maximum number of operations to return

        Returns:
            List of operation dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if session_id:
                cursor.execute('''
                    SELECT * FROM operations
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (session_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM operations
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_file_operations(self, operation_id: int) -> List[Dict]:
        """
        Get file operations for a specific operation.

        Args:
            operation_id: Operation ID

        Returns:
            List of file operation dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM file_operations
                WHERE operation_id = ?
                ORDER BY id
            ''', (operation_id,))

            return [dict(row) for row in cursor.fetchall()]

    def get_undoable_operations(self, limit: int = 10) -> List[Dict]:
        """
        Get recent operations that can be undone.

        Args:
            limit: Maximum number of operations

        Returns:
            List of undoable operations
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT o.*, COUNT(f.id) as file_count
                FROM operations o
                JOIN file_operations f ON o.id = f.operation_id
                WHERE f.can_undo = 1 AND o.status = 'completed'
                GROUP BY o.id
                ORDER BY o.timestamp DESC
                LIMIT ?
            ''', (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def create_snapshot(
        self,
        session_id: str,
        directory: str,
        operation_type: str,
        snapshot_data: Dict,
        description: Optional[str] = None
    ) -> int:
        """
        Create a snapshot for backup/restore.

        Args:
            session_id: Session ID
            directory: Directory being operated on
            operation_type: Type of operation
            snapshot_data: Snapshot data as dictionary
            description: Optional description

        Returns:
            Snapshot ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO snapshots
                (session_id, timestamp, directory, operation_type, snapshot_data, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                datetime.now().isoformat(),
                directory,
                operation_type,
                json.dumps(snapshot_data),
                description
            ))

            snapshot_id = cursor.lastrowid
            logger.info(f"Created snapshot {snapshot_id} for {directory}")
            return snapshot_id

    def get_snapshot(self, snapshot_id: int) -> Optional[Dict]:
        """
        Get a snapshot by ID.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            Snapshot dictionary or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM snapshots WHERE id = ?', (snapshot_id,))
            row = cursor.fetchone()

            if row:
                snapshot = dict(row)
                snapshot['snapshot_data'] = json.loads(snapshot['snapshot_data'])
                return snapshot

            return None

    def update_scan_cache(self, directory: str, file_path: str, file_info: Dict):
        """
        Update scan cache for incremental scanning.

        Args:
            directory: Root directory being scanned
            file_path: File path relative to directory
            file_info: File information dictionary
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO scan_cache
                (directory, file_path, file_hash, file_size, modified_time, last_scanned)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                directory,
                file_path,
                file_info.get('hash'),
                file_info.get('size'),
                file_info.get('modified_time'),
                datetime.now().isoformat()
            ))

    def get_scan_cache(self, directory: str) -> Dict[str, Dict]:
        """
        Get cached scan results for a directory.

        Args:
            directory: Directory path

        Returns:
            Dictionary mapping file paths to cached info
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM scan_cache WHERE directory = ?
            ''', (directory,))

            cache = {}
            for row in cursor.fetchall():
                cache[row['file_path']] = dict(row)

            return cache

    def clear_old_cache(self, days: int = 30):
        """
        Clear scan cache older than specified days.

        Args:
            days: Number of days to keep
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
            cursor.execute('''
                DELETE FROM scan_cache
                WHERE last_scanned < ?
            ''', (cutoff,))

            deleted = cursor.rowcount
            logger.info(f"Cleared {deleted} old cache entries")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with statistics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total operations
            cursor.execute('SELECT COUNT(*) as count FROM operations')
            stats['total_operations'] = cursor.fetchone()['count']

            # Total file operations
            cursor.execute('SELECT COUNT(*) as count FROM file_operations')
            stats['total_file_operations'] = cursor.fetchone()['count']

            # Cache entries
            cursor.execute('SELECT COUNT(*) as count FROM scan_cache')
            stats['cache_entries'] = cursor.fetchone()['count']

            # Snapshots
            cursor.execute('SELECT COUNT(*) as count FROM snapshots')
            stats['snapshots'] = cursor.fetchone()['count']

            # Recent operations by type
            cursor.execute('''
                SELECT operation_type, COUNT(*) as count
                FROM operations
                GROUP BY operation_type
            ''')
            stats['operations_by_type'] = {
                row['operation_type']: row['count']
                for row in cursor.fetchall()
            }

            return stats
