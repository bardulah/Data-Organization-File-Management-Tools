"""
File scanner module for analyzing directories and files.
"""

import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class FileScanner:
    """Scans directories and analyzes file information."""

    def __init__(self, root_path: str, exclude_dirs: List[str] = None):
        """
        Initialize the file scanner.

        Args:
            root_path: Root directory to scan
            exclude_dirs: List of directory names to exclude from scanning
        """
        self.root_path = Path(root_path)
        self.exclude_dirs = set(exclude_dirs or ['.git', '.svn', 'node_modules', '__pycache__', '.venv'])
        self.files_by_hash = defaultdict(list)
        self.files_by_extension = defaultdict(list)
        self.total_size = 0
        self.file_count = 0

    def calculate_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """
        Calculate MD5 hash of a file.

        Args:
            file_path: Path to the file
            chunk_size: Size of chunks to read

        Returns:
            MD5 hash string
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, PermissionError):
            return None

    def scan(self, include_hidden: bool = False) -> Dict:
        """
        Scan the directory tree and collect file information.

        Args:
            include_hidden: Whether to include hidden files

        Returns:
            Dictionary containing scan results
        """
        results = {
            'files': [],
            'duplicates': {},
            'by_extension': {},
            'total_size': 0,
            'file_count': 0,
            'scan_date': datetime.now().isoformat()
        }

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
                    if stat_info.st_size > 0:  # Skip empty files
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

                except (PermissionError, OSError) as e:
                    print(f"Warning: Could not access {file_path}: {e}")

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

        return results

    def find_old_files(self, days_threshold: int = 365) -> List[Dict]:
        """
        Find files that haven't been accessed in a specified number of days.

        Args:
            days_threshold: Number of days to consider a file as old

        Returns:
            List of old file information
        """
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
