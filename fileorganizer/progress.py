"""
Simple progress indicators without external dependencies.
"""

import sys
import time


class ProgressIndicator:
    """Simple progress indicator for terminal."""

    def __init__(self, total: int = None, desc: str = "", show: bool = True):
        """
        Initialize progress indicator.

        Args:
            total: Total number of items (if known)
            desc: Description to show
            show: Whether to show progress
        """
        self.total = total
        self.desc = desc
        self.show = show
        self.current = 0
        self.start_time = time.time()
        self.last_update = 0

    def update(self, n: int = 1):
        """Update progress by n items."""
        if not self.show:
            return

        self.current += n
        current_time = time.time()

        # Update at most every 0.1 seconds
        if current_time - self.last_update < 0.1 and self.current < self.total:
            return

        self.last_update = current_time
        self._display()

    def _display(self):
        """Display current progress."""
        elapsed = time.time() - self.start_time

        if self.total:
            percent = (self.current / self.total) * 100
            bar_length = 30
            filled = int(bar_length * self.current / self.total)
            bar = '█' * filled + '░' * (bar_length - filled)

            # Calculate ETA
            if self.current > 0:
                rate = self.current / elapsed
                remaining = (self.total - self.current) / rate if rate > 0 else 0
                eta_str = f"ETA: {int(remaining)}s"
            else:
                eta_str = "ETA: --"

            msg = f"\r{self.desc}: {bar} {percent:5.1f}% ({self.current}/{self.total}) {eta_str}"
        else:
            # Spinner for unknown total
            spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
            idx = int(elapsed * 10) % len(spinner)
            msg = f"\r{self.desc}: {spinner[idx]} {self.current} items ({elapsed:.1f}s)"

        sys.stdout.write(msg)
        sys.stdout.flush()

    def close(self):
        """Finish progress display."""
        if not self.show:
            return

        elapsed = time.time() - self.start_time

        if self.total:
            sys.stdout.write(f"\r{self.desc}: ✓ {self.total} items in {elapsed:.1f}s{' ' * 20}\n")
        else:
            sys.stdout.write(f"\r{self.desc}: ✓ {self.current} items in {elapsed:.1f}s{' ' * 20}\n")

        sys.stdout.flush()

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, *args):
        """Context manager cleanup."""
        self.close()


def show_spinner(desc: str = "Processing", show: bool = True):
    """
    Context manager for showing a spinner during long operations.

    Args:
        desc: Description text
        show: Whether to show spinner

    Example:
        with show_spinner("Scanning files"):
            # Long operation
            pass
    """
    class Spinner:
        def __init__(self, desc, show):
            self.desc = desc
            self.show = show
            self.start_time = None

        def __enter__(self):
            if self.show:
                self.start_time = time.time()
                sys.stdout.write(f"{self.desc}... ")
                sys.stdout.flush()
            return self

        def __exit__(self, *args):
            if self.show:
                elapsed = time.time() - self.start_time
                sys.stdout.write(f"✓ ({elapsed:.2f}s)\n")
                sys.stdout.flush()

    return Spinner(desc, show)
