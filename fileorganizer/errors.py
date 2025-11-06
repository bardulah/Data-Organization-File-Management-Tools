"""
Custom exceptions and error handling for production.
"""

from pathlib import Path
from typing import Optional


class FileOrganizerError(Exception):
    """Base exception for file organizer errors."""

    def __init__(self, message: str, path: Optional[Path] = None, suggestion: Optional[str] = None):
        self.message = message
        self.path = path
        self.suggestion = suggestion
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with helpful information."""
        msg = f"Error: {self.message}"

        if self.path:
            msg += f"\n  Path: {self.path}"

        if self.suggestion:
            msg += f"\n  💡 Suggestion: {self.suggestion}"

        return msg


class PermissionError(FileOrganizerError):
    """Permission denied error."""

    def __init__(self, path: Path, operation: str = "access"):
        super().__init__(
            f"Permission denied: Cannot {operation} file",
            path=path,
            suggestion=f"Try: chmod +rw {path} or check file ownership"
        )


class NotFoundError(FileOrganizerError):
    """File or directory not found."""

    def __init__(self, path: Path):
        super().__init__(
            "File or directory not found",
            path=path,
            suggestion="Check that the path is correct and the file exists"
        )


class CacheError(FileOrganizerError):
    """Cache-related error."""

    def __init__(self, message: str):
        super().__init__(
            f"Cache error: {message}",
            suggestion="Try running with --no-cache flag"
        )


def handle_error(error: Exception, path: Optional[Path] = None, operation: str = "process") -> FileOrganizerError:
    """
    Convert generic exceptions to FileOrganizerError.

    Args:
        error: Original exception
        path: Path where error occurred
        operation: Operation being performed

    Returns:
        FileOrganizerError with helpful information
    """
    if isinstance(error, FileOrganizerError):
        return error

    if isinstance(error, PermissionError):
        return PermissionError(path, operation)

    if isinstance(error, FileNotFoundError):
        return NotFoundError(path)

    if isinstance(error, OSError) and error.errno == 28:
        return FileOrganizerError(
            "No space left on device",
            path=path,
            suggestion="Free up disk space or use a different target directory"
        )

    # Generic error
    return FileOrganizerError(
        f"Unexpected error during {operation}: {str(error)}",
        path=path
    )
