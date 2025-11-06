"""
Atomic file operations with rollback support.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Callable
from contextlib import contextmanager
import tempfile
import logging

from .errors import OperationError, handle_error

logger = logging.getLogger(__name__)


class AtomicOperation:
    """Context manager for atomic file operations with rollback."""

    def __init__(self, description: str = "operation"):
        """
        Initialize atomic operation.

        Args:
            description: Description of the operation
        """
        self.description = description
        self.temp_files = []
        self.backups = []
        self.completed = False

    def __enter__(self):
        """Start atomic operation."""
        logger.debug(f"Starting atomic operation: {self.description}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End atomic operation and cleanup."""
        if exc_type is None and self.completed:
            # Success - remove backups
            self._cleanup_backups()
            self._cleanup_temp_files()
            logger.debug(f"Atomic operation completed: {self.description}")
        else:
            # Failure - rollback
            if exc_type:
                logger.error(f"Atomic operation failed: {self.description} - {exc_val}")
            self._rollback()

        return False  # Don't suppress exceptions

    def add_temp_file(self, temp_path: Path):
        """
        Track a temporary file for cleanup.

        Args:
            temp_path: Path to temporary file
        """
        self.temp_files.append(temp_path)

    def add_backup(self, original: Path, backup: Path):
        """
        Track a backup for potential rollback.

        Args:
            original: Original file path
            backup: Backup file path
        """
        self.backups.append((original, backup))

    def complete(self):
        """Mark operation as successfully completed."""
        self.completed = True

    def _rollback(self):
        """Rollback all changes."""
        logger.warning(f"Rolling back atomic operation: {self.description}")

        # Restore from backups
        for original, backup in reversed(self.backups):
            try:
                if backup.exists():
                    if original.exists():
                        original.unlink()
                    shutil.move(str(backup), str(original))
                    logger.debug(f"Restored {original} from backup")
            except Exception as e:
                logger.error(f"Failed to restore {original}: {e}")

        self._cleanup_temp_files()

    def _cleanup_backups(self):
        """Remove backup files."""
        for _, backup in self.backups:
            try:
                if backup.exists():
                    backup.unlink()
                    logger.debug(f"Cleaned up backup: {backup}")
            except Exception as e:
                logger.warning(f"Failed to cleanup backup {backup}: {e}")

    def _cleanup_temp_files(self):
        """Remove temporary files."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")


def atomic_move(src: Path, dst: Path, create_backup: bool = True) -> None:
    """
    Move file atomically with optional backup and rollback on failure.

    Args:
        src: Source file path
        dst: Destination file path
        create_backup: Whether to create a backup of destination if it exists

    Raises:
        OperationError: If operation fails
    """
    with AtomicOperation(f"move {src} to {dst}") as op:
        backup_path = None

        try:
            # Create destination directory
            dst.parent.mkdir(parents=True, exist_ok=True)

            # Backup existing destination file
            if dst.exists() and create_backup:
                backup_path = dst.with_suffix(dst.suffix + '.backup')
                shutil.copy2(str(dst), str(backup_path))
                op.add_backup(dst, backup_path)
                logger.debug(f"Created backup: {backup_path}")

            # Copy to temp location first
            temp_path = dst.with_suffix(dst.suffix + '.tmp')
            shutil.copy2(str(src), str(temp_path))
            op.add_temp_file(temp_path)

            # Atomic rename (on Unix systems)
            temp_path.rename(dst)

            # Remove source
            src.unlink()

            op.complete()

        except Exception as e:
            error = handle_error(e, src, "move")
            raise error


def atomic_copy(src: Path, dst: Path, verify: bool = True) -> None:
    """
    Copy file atomically with verification.

    Args:
        src: Source file path
        dst: Destination file path
        verify: Verify copy by comparing sizes

    Raises:
        OperationError: If operation fails
    """
    with AtomicOperation(f"copy {src} to {dst}") as op:
        try:
            # Create destination directory
            dst.parent.mkdir(parents=True, exist_ok=True)

            # Copy to temp location
            temp_path = dst.with_suffix(dst.suffix + '.tmp')
            shutil.copy2(str(src), str(temp_path))
            op.add_temp_file(temp_path)

            # Verify if requested
            if verify:
                src_size = src.stat().st_size
                temp_size = temp_path.stat().st_size

                if src_size != temp_size:
                    raise OperationError(
                        "copy",
                        src,
                        f"Size mismatch: source {src_size} bytes, copy {temp_size} bytes"
                    )

            # Atomic rename
            temp_path.rename(dst)

            op.complete()

        except Exception as e:
            error = handle_error(e, src, "copy")
            raise error


def atomic_write(file_path: Path, content: str, encoding: str = 'utf-8') -> None:
    """
    Write to file atomically (write to temp, then rename).

    Args:
        file_path: File path to write to
        content: Content to write
        encoding: Text encoding

    Raises:
        OperationError: If operation fails
    """
    with AtomicOperation(f"write {file_path}") as op:
        try:
            # Create directory
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Backup existing file
            if file_path.exists():
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                shutil.copy2(str(file_path), str(backup_path))
                op.add_backup(file_path, backup_path)

            # Write to temp file
            temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
            with open(temp_path, 'w', encoding=encoding) as f:
                f.write(content)
            op.add_temp_file(temp_path)

            # Atomic rename
            temp_path.rename(file_path)

            op.complete()

        except Exception as e:
            error = handle_error(e, file_path, "write")
            raise error


def safe_delete(file_path: Path, create_backup: bool = True, backup_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Delete file with optional backup.

    Args:
        file_path: File to delete
        create_backup: Whether to create a backup before deleting
        backup_dir: Directory for backup (defaults to same directory with .backup suffix)

    Returns:
        Path to backup if created, None otherwise

    Raises:
        OperationError: If operation fails
    """
    try:
        if not file_path.exists():
            logger.warning(f"File doesn't exist: {file_path}")
            return None

        backup_path = None

        if create_backup:
            if backup_dir:
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_path = backup_dir / file_path.name
            else:
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')

            shutil.copy2(str(file_path), str(backup_path))
            logger.debug(f"Created backup before delete: {backup_path}")

        file_path.unlink()
        logger.debug(f"Deleted file: {file_path}")

        return backup_path

    except Exception as e:
        error = handle_error(e, file_path, "delete")
        raise error


@contextmanager
def temp_copy(file_path: Path):
    """
    Context manager that creates a temporary copy of a file.

    Args:
        file_path: File to copy

    Yields:
        Path to temporary copy

    Example:
        with temp_copy(Path('important.txt')) as temp:
            # Work with temp file
            process(temp)
            # Original is untouched, temp is cleaned up automatically
    """
    temp_path = None
    try:
        # Create temp file in same directory
        temp_fd, temp_name = tempfile.mkstemp(
            dir=file_path.parent,
            prefix=f".{file_path.stem}_",
            suffix=file_path.suffix
        )
        os.close(temp_fd)
        temp_path = Path(temp_name)

        # Copy original to temp
        shutil.copy2(str(file_path), str(temp_path))
        logger.debug(f"Created temp copy: {temp_path}")

        yield temp_path

    finally:
        # Cleanup temp file
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
                logger.debug(f"Cleaned up temp copy: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")


def batch_atomic_operation(operations: list, on_error: str = 'rollback') -> dict:
    """
    Execute multiple file operations atomically.

    Args:
        operations: List of (function, args, kwargs) tuples
        on_error: 'rollback' to undo all, 'continue' to keep successes

    Returns:
        Dictionary with results

    Example:
        operations = [
            (atomic_move, (src1, dst1), {}),
            (atomic_copy, (src2, dst2), {'verify': True}),
        ]
        results = batch_atomic_operation(operations)
    """
    results = {
        'total': len(operations),
        'succeeded': [],
        'failed': [],
        'rolled_back': False
    }

    with AtomicOperation("batch operation") as op:
        for i, (func, args, kwargs) in enumerate(operations):
            try:
                func(*args, **kwargs)
                results['succeeded'].append(i)
                logger.debug(f"Operation {i+1}/{len(operations)} succeeded")

            except Exception as e:
                logger.error(f"Operation {i+1}/{len(operations)} failed: {e}")
                results['failed'].append({
                    'index': i,
                    'function': func.__name__,
                    'error': str(e)
                })

                if on_error == 'rollback':
                    # Don't complete, let context manager rollback
                    results['rolled_back'] = True
                    raise

        # All succeeded
        op.complete()

    return results
