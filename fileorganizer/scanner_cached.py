"""
Enhanced file scanner with simple caching support.
"""

import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple
from collections import defaultdict

from .cache import ScanCache


class CachedFileScanner:
    """File scanner with caching for improved performance."""

    def __init__(self, root_path: str, exclude_dirs: List[str] = None, use_cache: bool = True):
        """
        Initialize the cached file scanner.

        Args:
            root_path: Root directory to scan
            exclude_dirs: List of directory names to exclude
            use_cache: Whether to use caching
        """
        self.root_path = Path(root_path)
        self.exclude_dirs = set(exclude_dirs or ['.git', '.svn', 'node_modules', '__pycache__', '.venv'])
        self.use_cache = use_cache
        self.cache = ScanCache() if use_cache else None

        self.files_by_hash = defaultdict(list)
        self.files_by_extension = defaultdict(list)
        self.total_size = 0
        self.file_count = 0

    def calculate_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """Calculate MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, PermissionError, OSError):
            return None

    def scan(self, include_hidden: bool = False) -> Dict:
        """
        Scan the directory tree with caching support.

        Args:
            include_hidden: Whether to include hidden files

        Returns:
            Dictionary containing scan results
        """
        start_time = datetime.now()

        # Try to load from cache first
        if self.use_cache and self.cache:
            cached = self.cache.get(str(self.root_path))
            if cached:
                print(f"Using cached results from {cached['cached_at']}")
                return cached['results']

        # No cache, do full scan
        results = {
            'files': [],
            'duplicates': {},
            'by_extension': {},
            'total_size': 0,
            'file_count': 0,
            'scan_date': datetime.now().isoformat()
        }

        files_scanned = 0

        for root, dirs, files in os.walk(self.root_path):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            # Skip hidden directories if not included
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in files:
                # Skip hidden files if not included
                if not include_hidden and filename.startswith('.'):
                    continue

                file_path = Path(root) / filename

                try:
                    stat_info = file_path.stat()
                    file_info = {
                        'path': str(file_path),
                        'name': filename,
                        'size': stat_info.st_size,
                        'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        'accessed': datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                        'extension': file_path.suffix.lower(),
                    }

                    # Calculate hash for duplicate detection
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
                    files_scanned += 1

                    # Progress feedback
                    if files_scanned % 100 == 0:
                        print(f"  Scanned {files_scanned} files...", end='\r')

                except (PermissionError, OSError) as e:
                    print(f"Warning: Could not access {file_path}: {e}")

        print(f"  Scanned {files_scanned} files - Done!     ")

        # Find duplicates
        results['duplicates'] = {
            hash_val: files
            for hash_val, files in self.files_by_hash.items()
            if len(files) > 1
        }

        # Group by extension
        results['by_extension'] = dict(self.files_by_extension)
        results['total_size'] = self.total_size
        results['file_count'] = self.file_count

        # Calculate scan duration
        duration = (datetime.now() - start_time).total_seconds()
        results['scan_duration'] = duration

        # Save to cache
        if self.use_cache and self.cache:
            self.cache.set(str(self.root_path), results)

        return results

    def find_old_files(self, days_threshold: int = 365) -> List[Dict]:
        """Find files that haven't been accessed in a specified number of days."""
        old_files = []
        threshold_date = datetime.now().timestamp() - (days_threshold * 24 * 60 * 60)

        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for filename in files:
                file_path = Path(root) / filename

                try:
                    stat_info = file_path.stat()
                    if stat_info.st_atime < threshold_date:
                        old_files.append({
                            'path': str(file_path),
                            'name': filename,
                            'size': stat_info.st_size,
                            'last_accessed': datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                            'days_since_access': (datetime.now().timestamp() - stat_info.st_atime) / (24 * 60 * 60)
                        })
                except (PermissionError, OSError):
                    pass

        return sorted(old_files, key=lambda x: x['days_since_access'], reverse=True)
