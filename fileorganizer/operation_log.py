"""
Simple operation logger for undo functionality.
Logs file operations to JSON for easy undo.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class OperationLog:
    """Simple logger for file operations with undo support."""

    def __init__(self, log_file: Path = None):
        """
        Initialize operation logger.

        Args:
            log_file: Path to log file (defaults to ~/.fileorganizer/operations.json)
        """
        if log_file is None:
            log_dir = Path.home() / '.fileorganizer'
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / 'operations.json'

        self.log_file = log_file
        self.operations = self._load()

    def _load(self) -> List[Dict]:
        """Load operations from log file."""
        if not self.log_file.exists():
            return []

        try:
            with open(self.log_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print(f"Warning: Could not load operation log")
            return []

    def _save(self):
        """Save operations to log file."""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.operations, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save operation log: {e}")

    def log_move(self, source: str, destination: str, operation_id: str = None):
        """
        Log a file move operation.

        Args:
            source: Original file path
            destination: New file path
            operation_id: Optional operation group ID
        """
        operation = {
            'id': len(self.operations) + 1,
            'type': 'move',
            'source': source,
            'destination': destination,
            'timestamp': datetime.now().isoformat(),
            'operation_id': operation_id,
            'undone': False
        }

        self.operations.append(operation)
        self._save()

    def log_copy(self, source: str, destination: str, operation_id: str = None):
        """Log a file copy operation."""
        operation = {
            'id': len(self.operations) + 1,
            'type': 'copy',
            'source': source,
            'destination': destination,
            'timestamp': datetime.now().isoformat(),
            'operation_id': operation_id,
            'undone': False
        }

        self.operations.append(operation)
        self._save()

    def log_delete(self, file_path: str, operation_id: str = None):
        """
        Log a file deletion (WARNING: Cannot be undone!).

        Args:
            file_path: Path of deleted file
            operation_id: Optional operation group ID
        """
        operation = {
            'id': len(self.operations) + 1,
            'type': 'delete',
            'file_path': file_path,
            'timestamp': datetime.now().isoformat(),
            'operation_id': operation_id,
            'undone': False,
            'can_undo': False
        }

        self.operations.append(operation)
        self._save()

    def get_recent_operations(self, limit: int = 10) -> List[Dict]:
        """
        Get recent operations.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of recent operations
        """
        # Return most recent first
        return list(reversed(self.operations[-limit:]))

    def get_undoable_operations(self, limit: int = 10) -> List[Dict]:
        """
        Get operations that can be undone.

        Args:
            limit: Maximum number to return

        Returns:
            List of undoable operations
        """
        undoable = [
            op for op in self.operations
            if not op.get('undone', False) and op.get('can_undo', True)
        ]

        return list(reversed(undoable[-limit:]))

    def undo_operation(self, operation_id: int) -> bool:
        """
        Undo a specific operation.

        Args:
            operation_id: ID of operation to undo

        Returns:
            True if successful, False otherwise
        """
        # Find the operation
        operation = None
        for op in self.operations:
            if op['id'] == operation_id:
                operation = op
                break

        if not operation:
            print(f"Operation {operation_id} not found")
            return False

        if operation.get('undone', False):
            print(f"Operation {operation_id} already undone")
            return False

        if not operation.get('can_undo', True):
            print(f"Operation {operation_id} cannot be undone (type: {operation['type']})")
            return False

        # Perform undo based on operation type
        success = False

        if operation['type'] == 'move':
            success = self._undo_move(operation)
        elif operation['type'] == 'copy':
            success = self._undo_copy(operation)
        else:
            print(f"Unknown operation type: {operation['type']}")
            return False

        if success:
            operation['undone'] = True
            operation['undone_at'] = datetime.now().isoformat()
            self._save()
            print(f"✓ Undid operation {operation_id}")

        return success

    def _undo_move(self, operation: Dict) -> bool:
        """Undo a move operation by moving file back."""
        import shutil

        source = Path(operation['source'])
        dest = Path(operation['destination'])

        if not dest.exists():
            print(f"✗ Cannot undo: {dest} no longer exists")
            return False

        if source.exists():
            print(f"✗ Cannot undo: {source} already exists")
            return False

        try:
            # Create parent directory if needed
            source.parent.mkdir(parents=True, exist_ok=True)

            # Move file back
            shutil.move(str(dest), str(source))
            print(f"  Moved {dest.name} back to {source}")
            return True

        except (IOError, OSError) as e:
            print(f"✗ Failed to undo move: {e}")
            return False

    def _undo_copy(self, operation: Dict) -> bool:
        """Undo a copy operation by deleting the copy."""
        dest = Path(operation['destination'])

        if not dest.exists():
            print(f"Copy at {dest} already removed")
            return True

        try:
            dest.unlink()
            print(f"  Removed copy at {dest}")
            return True

        except (IOError, OSError) as e:
            print(f"✗ Failed to remove copy: {e}")
            return False

    def clear_log(self):
        """Clear all logged operations."""
        self.operations = []
        self._save()

    def get_stats(self) -> Dict:
        """Get statistics about logged operations."""
        total = len(self.operations)
        by_type = {}
        undone_count = 0

        for op in self.operations:
            op_type = op['type']
            by_type[op_type] = by_type.get(op_type, 0) + 1

            if op.get('undone', False):
                undone_count += 1

        return {
            'total_operations': total,
            'by_type': by_type,
            'undone': undone_count,
            'active': total - undone_count
        }
