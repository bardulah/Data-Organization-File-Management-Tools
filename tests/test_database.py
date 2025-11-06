"""
Tests for database module.
"""

import pytest
from pathlib import Path
import tempfile

from fileorganizer.database import Database


class TestDatabase:
    """Test database operations."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database."""
        db_path = tmp_path / "test.db"
        return Database(db_path)

    def test_database_initialization(self, temp_db):
        """Test database initializes correctly."""
        # Database should be created and initialized
        assert temp_db.db_path.exists()

        # Check statistics
        stats = temp_db.get_statistics()
        assert 'total_operations' in stats
        assert stats['total_operations'] == 0

    def test_start_and_complete_operation(self, temp_db):
        """Test logging operations."""
        # Start operation
        op_id = temp_db.start_operation(
            'test_session',
            'test command',
            'scan',
            {'test': 'data'}
        )

        assert op_id > 0

        # Complete operation
        temp_db.complete_operation(op_id, 'completed', 1.5)

        # Verify in history
        history = temp_db.get_operation_history()
        assert len(history) == 1
        assert history[0]['id'] == op_id
        assert history[0]['status'] == 'completed'
        assert history[0]['duration_seconds'] == 1.5

    def test_log_file_operations(self, temp_db):
        """Test logging file operations."""
        # Create operation
        op_id = temp_db.start_operation('session1', 'move files', 'organize')

        # Log file operations
        temp_db.log_file_operation(
            op_id,
            'move',
            '/source/file.txt',
            destination_path='/dest/file.txt',
            file_size=1024,
            file_hash='abc123',
            status='success',
            can_undo=True
        )

        # Get file operations
        file_ops = temp_db.get_file_operations(op_id)
        assert len(file_ops) == 1
        assert file_ops[0]['action'] == 'move'
        assert file_ops[0]['source_path'] == '/source/file.txt'
        assert file_ops[0]['can_undo'] == 1

    def test_scan_cache(self, temp_db):
        """Test scan cache functionality."""
        directory = '/test/directory'
        file_path = 'subdir/file.txt'

        file_info = {
            'hash': 'abc123',
            'size': 2048,
            'modified_time': 1234567890.0
        }

        # Update cache
        temp_db.update_scan_cache(directory, file_path, file_info)

        # Retrieve cache
        cache = temp_db.get_scan_cache(directory)

        assert file_path in cache
        assert cache[file_path]['file_hash'] == 'abc123'
        assert cache[file_path]['file_size'] == 2048

    def test_snapshots(self, temp_db):
        """Test snapshot functionality."""
        snapshot_data = {
            'files': ['file1.txt', 'file2.txt'],
            'count': 2
        }

        # Create snapshot
        snapshot_id = temp_db.create_snapshot(
            'session1',
            '/test/dir',
            'organize',
            snapshot_data,
            'Test snapshot'
        )

        assert snapshot_id > 0

        # Retrieve snapshot
        snapshot = temp_db.get_snapshot(snapshot_id)

        assert snapshot is not None
        assert snapshot['directory'] == '/test/dir'
        assert snapshot['snapshot_data']['count'] == 2
        assert snapshot['description'] == 'Test snapshot'

    def test_get_undoable_operations(self, temp_db):
        """Test retrieving undoable operations."""
        # Create operation with undoable file operations
        op_id = temp_db.start_operation('session1', 'move files', 'organize')

        temp_db.log_file_operation(
            op_id,
            'move',
            '/file1.txt',
            destination_path='/moved/file1.txt',
            can_undo=True
        )

        temp_db.complete_operation(op_id, 'completed')

        # Get undoable operations
        undoable = temp_db.get_undoable_operations()

        assert len(undoable) == 1
        assert undoable[0]['id'] == op_id
        assert undoable[0]['file_count'] == 1
