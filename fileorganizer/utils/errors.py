"""
Custom exceptions and error handling utilities.
"""

from pathlib import Path
from typing import Optional
import os


class FileOrganizerError(Exception):
    """Base exception for file organizer errors."""

    def __init__(self, message: str, file_path: Optional[Path] = None, suggestion: Optional[str] = None):
        """
        Initialize error with helpful information.

        Args:
            message: Error message
            file_path: Path where error occurred
            suggestion: Suggested fix
        """
        self.message = message
        self.file_path = file_path
        self.suggestion = suggestion
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format a helpful error message."""
        msg = f"❌ {self.message}"

        if self.file_path:
            msg += f"\n   File: {self.file_path}"

        if self.suggestion:
            msg += f"\n   💡 Suggestion: {self.suggestion}"

        return msg


class PermissionError(FileOrganizerError):
    """Permission denied error with helpful suggestions."""

    def __init__(self, file_path: Path, operation: str = "access"):
        """
        Initialize permission error.

        Args:
            file_path: Path where permission was denied
            operation: Operation that was attempted
        """
        message = f"Permission denied: Cannot {operation} file"

        # Generate helpful suggestions based on file
        suggestions = []
        try:
            stat_info = os.stat(file_path)
            mode = stat_info.st_mode

            # Check if we need read permission
            if operation in ["read", "access", "hash"]:
                suggestions.append(f"Try: chmod +r {file_path}")

            # Check if we need write permission
            if operation in ["write", "move", "delete", "rename"]:
                suggestions.append(f"Try: chmod +w {file_path}")

            # Check ownership
            if stat_info.st_uid != os.getuid():
                suggestions.append(f"Try: sudo chown $USER {file_path}")
                suggestions.append(f"Or run with sudo (not recommended)")

        except:
            suggestions.append(f"Try: chmod +rw {file_path}")
            suggestions.append(f"Or: sudo chown $USER {file_path}")

        suggestion = "\n      Or: ".join(suggestions)

        super().__init__(message, file_path, suggestion)


class OperationError(FileOrganizerError):
    """Error during file operation."""

    def __init__(self, operation: str, file_path: Path, reason: str):
        """
        Initialize operation error.

        Args:
            operation: Operation that failed
            file_path: Path where operation failed
            reason: Reason for failure
        """
        message = f"Failed to {operation}: {reason}"

        # Generate suggestions based on operation
        suggestion = None
        if "No such file" in reason:
            suggestion = "Check that the path exists and is spelled correctly"
        elif "not a directory" in reason:
            suggestion = "Parent path must be a directory"
        elif "Directory not empty" in reason:
            suggestion = "Use --force to remove non-empty directories"
        elif "space" in reason.lower():
            suggestion = "Check available disk space with: df -h"

        super().__init__(message, file_path, suggestion)


class ConfigurationError(FileOrganizerError):
    """Configuration error."""

    def __init__(self, message: str, config_path: Optional[Path] = None):
        """
        Initialize configuration error.

        Args:
            message: Error message
            config_path: Path to configuration file
        """
        suggestion = "Check configuration file syntax and values"
        if config_path:
            suggestion += f"\n      Example config: examples/config.yaml"

        super().__init__(message, config_path, suggestion)


def handle_error(error: Exception, file_path: Optional[Path] = None, operation: str = "process") -> FileOrganizerError:
    """
    Convert generic exceptions to FileOrganizerError with helpful messages.

    Args:
        error: Original exception
        file_path: Path where error occurred
        operation: Operation being performed

    Returns:
        FileOrganizerError with helpful information
    """
    if isinstance(error, FileOrganizerError):
        return error

    if isinstance(error, OSError):
        if error.errno == 13:  # Permission denied
            return PermissionError(file_path, operation)
        elif error.errno == 2:  # No such file
            return OperationError(operation, file_path, "File or directory not found")
        elif error.errno == 28:  # No space left
            return OperationError(operation, file_path, "No space left on device")
        else:
            return OperationError(operation, file_path, str(error))

    # Generic error
    return FileOrganizerError(f"Unexpected error during {operation}: {str(error)}", file_path)
