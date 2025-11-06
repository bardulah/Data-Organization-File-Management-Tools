"""
Production-ready file scanner with logging, progress, and error handling.
"""

import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

from .cache import ScanCache
from .progress import ProgressIndicator
from .logging_config import get_logger
from .errors import handle_error, PermissionError as OrgPermissionError

logger = get_logger(__name__)


class ProductionScanner:
    """Production-ready file scanner with full error handling."""

    def __init__(self, root_path: str, exclude_dirs: List[str] = None, use_cache: bool = True, show_progress: bool = True):
        """
        Initialize production scanner.

        Args:
            root_path: Root directory to scan
            exclude_dirs: Directories to exclude
            use_cache: Whether to use caching
            show_progress: Whether to show progress
        """
        self.root_path = Path(root_path)
        self.exclude_dirs = set(exclude_dirs or ['.git', '.svn', 'node_modules', '__pycache__', '.venv'])
        self.use_cache = use_cache
        self.show_progress = show_progress
        self.cache = ScanCache() if use_cache else None

        self.files_by_hash = defaultdict(list)
        self.files_by_extension = defaultdict(list)
        self.total_size = 0
        self.file_count = 0
        self.errors = []

        logger.info(f"Initializing scanner for: {self.root_path}")

    def calculate_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """Calculate MD5 hash of a file."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.warning(f"Could not hash {file_path}: {e}")
            return None

    def scan(self, include_hidden: bool = False) -> Dict:
        """
        Scan directory with full production features.

        Args:
            include_hidden: Include hidden files

        Returns:
            Scan results dictionary
        """
        start_time = datetime.now()
        logger.info(f"Starting scan of {self.root_path} (cache={self.use_cache})")

        # Check if path exists
        if not self.root_path.exists():
            error = f"Directory not found: {self.root_path}"
            logger.error(error)
            raise FileNotFoundError(error)

        if not self.root_path.is_dir():
            error = f"Not a directory: {self.root_path}"
            logger.error(error)
            raise NotADirectoryError(error)

        # Try cache first
        if self.use_cache and self.cache:
            cached = self.cache.get(str(self.root_path))
            if cached:
                logger.info(f"Using cached results from {cached['cached_at']}")
                if self.show_progress:
                    print(f"✓ Using cached results from {cached['cached_at'][:19]}")
                return cached['results']

        # Full scan
        results = {
            'files': [],
            'duplicates': {},
            'by_extension': {},
            'total_size': 0,
            'file_count': 0,
            'scan_date': datetime.now().isoformat(),
            'errors': []
        }

        # Count files first for progress
        if self.show_progress:
            total_files = sum(1 for _ in self._walk_files(include_hidden))
            progress = ProgressIndicator(total=total_files, desc="Scanning files", show=True)
        else:
            progress = ProgressIndicator(show=False)

        with progress:
            for file_path in self._walk_files(include_hidden):
                try:
                    self._process_file(file_path, results)
                    progress.update(1)

                except (PermissionError, OSError) as e:
                    error_msg = f"Cannot access {file_path}: {e}"
                    logger.warning(error_msg)
                    self.errors.append(error_msg)
                    progress.update(1)
                    continue

                except Exception as e:
                    error_msg = f"Unexpected error processing {file_path}: {e}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
                    progress.update(1)
                    continue

        # Find duplicates
        results['duplicates'] = {
            hash_val: files
            for hash_val, files in self.files_by_hash.items()
            if len(files) > 1
        }

        # Finalize results
        results['by_extension'] = dict(self.files_by_extension)
        results['total_size'] = self.total_size
        results['file_count'] = self.file_count
        results['errors'] = self.errors

        duration = (datetime.now() - start_time).total_seconds()
        results['scan_duration'] = duration

        logger.info(f"Scan complete: {self.file_count} files in {duration:.2f}s")
        if self.errors:
            logger.warning(f"Encountered {len(self.errors)} errors during scan")

        # Save to cache
        if self.use_cache and self.cache:
            try:
                self.cache.set(str(self.root_path), results)
                logger.info("Results cached successfully")
            except Exception as e:
                logger.warning(f"Could not cache results: {e}")

        return results

    def _walk_files(self, include_hidden: bool):
        """Generator to walk through all files."""
        for root, dirs, files in os.walk(self.root_path):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in files:
                if not include_hidden and filename.startswith('.'):
                    continue

                yield Path(root) / filename

    def _process_file(self, file_path: Path, results: Dict):
        """Process a single file."""
        stat_info = file_path.stat()

        file_info = {
            'path': str(file_path),
            'name': file_path.name,
            'size': stat_info.st_size,
            'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            'extension': file_path.suffix.lower(),
        }

        # Calculate hash for non-empty files
        if stat_info.st_size > 0:
            file_hash = self.calculate_hash(file_path)
            if file_hash:
                file_info['hash'] = file_hash
                self.files_by_hash[file_hash].append(file_info)

        # Group by extension
        ext = file_path.suffix.lower() or '.no_extension'
        self.files_by_extension[ext].append(file_info)

        results['files'].append(file_info)
        self.total_size += stat_info.st_size
        self.file_count += 1
