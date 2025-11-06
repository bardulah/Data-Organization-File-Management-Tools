"""
Undo/redo system for file operations.
"""

import shutil
from pathlib import Path
from typing import Dict, List, Optional
import logging
from datetime import datetime

from .database import Database
from .utils.errors import OperationError, handle_error

logger = logging.getLogger(__name__)


class UndoManager:
    """Manages undo/redo operations."""

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize undo manager.

        Args:
            db: Database instance (creates new if None)
        """
        self.db = db or Database()

    def can_undo(self, operation_id: int) -> bool:
        """
        Check if an operation can be undone.

        Args:
            operation_id: Operation ID to check

        Returns:
            True if operation can be undone
        """
        file_ops = self.db.get_file_operations(operation_id)

        # All file operations must be undoable
        return all(op['can_undo'] for op in file_ops)

    def get_undo_list(self, limit: int = 10) -> List[Dict]:
        """
        Get list of operations that can be undone.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of undoable operations
        """
        return self.db.get_undoable_operations(limit)

    def undo_operation(self, operation_id: int, dry_run: bool = False) -> Dict:
        """
        Undo a specific operation.

        Args:
            operation_id: Operation ID to undo
            dry_run: If True, simulate without making changes

        Returns:
            Dictionary with undo results
        """
        logger.info(f"Starting undo for operation {operation_id} (dry_run={dry_run})")

        # Get operation details
        operations = self.db.get_operation_history(limit=1000)
        operation = next((op for op in operations if op['id'] == operation_id), None)

        if not operation:
            raise OperationError("undo", Path(""), f"Operation {operation_id} not found")

        # Get file operations
        file_ops = self.db.get_file_operations(operation_id)

        if not file_ops:
            raise OperationError("undo", Path(""), "No file operations to undo")

        results = {
            'operation_id': operation_id,
            'operation_type': operation['operation_type'],
            'timestamp': operation['timestamp'],
            'undone': [],
            'failed': [],
            'dry_run': dry_run
        }

        # Reverse operations in reverse order
        for file_op in reversed(file_ops):
            if not file_op['can_undo']:
                logger.warning(f"Cannot undo operation {file_op['id']}")
                results['failed'].append({
                    'file_op': file_op,
                    'reason': 'Operation marked as non-undoable'
                })
                continue

            try:
                undo_result = self._undo_file_operation(file_op, dry_run)
                results['undone'].append(undo_result)
            except Exception as e:
                logger.error(f"Failed to undo operation {file_op['id']}: {e}")
                results['failed'].append({
                    'file_op': file_op,
                    'reason': str(e)
                })

        logger.info(f"Undo complete: {len(results['undone'])} succeeded, {len(results['failed'])} failed")
        return results

    def _undo_file_operation(self, file_op: Dict, dry_run: bool) -> Dict:
        """
        Undo a single file operation.

        Args:
            file_op: File operation dictionary
            dry_run: If True, simulate without making changes

        Returns:
            Dictionary with undo details
        """
        action = file_op['action']
        source = Path(file_op['source_path'])
        dest = Path(file_op['destination_path']) if file_op['destination_path'] else None

        logger.debug(f"Undoing {action}: {source} -> {dest}")

        result = {
            'action': action,
            'original_operation': file_op,
            'status': 'simulated' if dry_run else 'success'
        }

        if action == 'move':
            # Undo move: move file back
            if not dry_run:
                if not dest or not dest.exists():
                    raise OperationError("undo move", source, "Destination file no longer exists")

                if source.exists():
                    raise OperationError("undo move", source, "Source path already exists")

                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dest), str(source))

            result['undo_action'] = f"Moved {dest} back to {source}"

        elif action == 'copy':
            # Undo copy: delete the copy
            if not dry_run:
                if dest and dest.exists():
                    dest.unlink()
                else:
                    logger.warning(f"Copy destination {dest} doesn't exist, nothing to undo")

            result['undo_action'] = f"Deleted copy at {dest}"

        elif action == 'delete':
            # Cannot undo delete (file is gone)
            result['status'] = 'failed'
            result['reason'] = 'Cannot restore deleted files (no backup available)'
            logger.error("Cannot undo delete - file is permanently deleted")

        elif action == 'rename':
            # Undo rename: rename back
            if not dry_run:
                if not dest or not dest.exists():
                    raise OperationError("undo rename", source, "Renamed file no longer exists")

                if source.exists():
                    raise OperationError("undo rename", source, "Original name already exists")

                dest.rename(source)

            result['undo_action'] = f"Renamed {dest} back to {source}"

        elif action == 'archived_to_zip':
            # Would need to extract from zip - complex
            result['status'] = 'failed'
            result['reason'] = 'Undo from archive requires manual extraction'

        else:
            result['status'] = 'failed'
            result['reason'] = f'Unknown action type: {action}'

        return result

    def create_undo_point(
        self,
        session_id: str,
        operation_type: str,
        directory: str,
        description: Optional[str] = None
    ) -> int:
        """
        Create an undo point (snapshot) before an operation.

        Args:
            session_id: Session ID
            operation_type: Type of operation
            directory: Directory being operated on
            description: Optional description

        Returns:
            Snapshot ID
        """
        logger.info(f"Creating undo point for {operation_type} in {directory}")

        # Scan directory state
        dir_path = Path(directory)
        snapshot_data = {
            'files': [],
            'timestamp': datetime.now().isoformat()
        }

        try:
            for item in dir_path.rglob('*'):
                if item.is_file():
                    stat = item.stat()
                    snapshot_data['files'].append({
                        'path': str(item.relative_to(dir_path)),
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })
        except Exception as e:
            logger.error(f"Error creating snapshot: {e}")

        snapshot_id = self.db.create_snapshot(
            session_id,
            directory,
            operation_type,
            snapshot_data,
            description
        )

        logger.info(f"Created snapshot {snapshot_id} with {len(snapshot_data['files'])} files")
        return snapshot_id

    def restore_snapshot(self, snapshot_id: int, dry_run: bool = False) -> Dict:
        """
        Restore from a snapshot (restore directory state).

        Args:
            snapshot_id: Snapshot ID to restore
            dry_run: If True, simulate without making changes

        Returns:
            Dictionary with restore results
        """
        snapshot = self.db.get_snapshot(snapshot_id)

        if not snapshot:
            raise OperationError("restore", Path(""), f"Snapshot {snapshot_id} not found")

        logger.info(f"Restoring snapshot {snapshot_id} (dry_run={dry_run})")

        directory = Path(snapshot['directory'])
        snapshot_data = snapshot['snapshot_data']

        results = {
            'snapshot_id': snapshot_id,
            'directory': str(directory),
            'timestamp': snapshot['timestamp'],
            'files_in_snapshot': len(snapshot_data['files']),
            'changes': [],
            'dry_run': dry_run
        }

        # Get current state
        current_files = {}
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    rel_path = str(item.relative_to(directory))
                    current_files[rel_path] = item
        except Exception as e:
            logger.error(f"Error scanning directory: {e}")

        # Find differences
        snapshot_files = {f['path']: f for f in snapshot_data['files']}

        # Files that exist now but not in snapshot (should be removed)
        for path in current_files:
            if path not in snapshot_files:
                results['changes'].append({
                    'action': 'remove',
                    'path': path,
                    'reason': 'Not in snapshot'
                })
                if not dry_run:
                    try:
                        current_files[path].unlink()
                        logger.debug(f"Removed {path}")
                    except Exception as e:
                        logger.error(f"Failed to remove {path}: {e}")

        # Files in snapshot but not now (warning - can't restore)
        for path in snapshot_files:
            if path not in current_files:
                results['changes'].append({
                    'action': 'warning',
                    'path': path,
                    'reason': 'File missing, cannot restore (no backup)'
                })

        logger.info(f"Restore complete: {len(results['changes'])} changes")
        return results

    def list_undoable(self) -> List[str]:
        """
        Get a formatted list of undoable operations.

        Returns:
            List of formatted strings describing undoable operations
        """
        operations = self.get_undo_list()

        formatted = []
        for op in operations:
            timestamp = datetime.fromisoformat(op['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            formatted.append(
                f"[{op['id']}] {op['operation_type']} - {op['command']} "
                f"({op['file_count']} files) - {timestamp}"
            )

        return formatted
