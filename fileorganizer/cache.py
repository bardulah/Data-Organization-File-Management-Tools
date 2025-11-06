"""
Simple JSON-based cache for file scanning.
Stores file metadata to avoid re-scanning unchanged files.
"""

import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class ScanCache:
    """Simple cache for file scan results."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache.

        Args:
            cache_dir: Directory to store cache files (defaults to ~/.fileorganizer/cache)
        """
        if cache_dir is None:
            cache_dir = Path.home() / '.fileorganizer' / 'cache'

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_file(self, directory: str) -> Path:
        """Get cache file path for a directory."""
        # Use hash of directory path as filename to avoid path issues
        import hashlib
        dir_hash = hashlib.md5(directory.encode()).hexdigest()
        return self.cache_dir / f"scan_{dir_hash}.json"

    def get(self, directory: str) -> Optional[Dict]:
        """
        Get cached scan results for a directory.

        Args:
            directory: Directory path

        Returns:
            Cached results dictionary or None if not cached/expired
        """
        cache_file = self._get_cache_file(directory)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)

            # Simple validation
            if 'directory' not in cached or cached['directory'] != directory:
                return None

            return cached

        except (json.JSONDecodeError, IOError):
            # Cache corrupted, ignore it
            return None

    def set(self, directory: str, scan_results: Dict):
        """
        Save scan results to cache.

        Args:
            directory: Directory path
            scan_results: Scan results to cache
        """
        cache_file = self._get_cache_file(directory)

        try:
            # Add metadata
            cached_data = {
                'directory': directory,
                'cached_at': datetime.now().isoformat(),
                'results': scan_results
            }

            with open(cache_file, 'w') as f:
                json.dump(cached_data, f, indent=2)

        except IOError as e:
            # Don't fail if cache write fails
            print(f"Warning: Could not write cache: {e}")

    def invalidate(self, directory: str):
        """Remove cache for a directory."""
        cache_file = self._get_cache_file(directory)

        if cache_file.exists():
            try:
                cache_file.unlink()
            except IOError:
                pass

    def clear_all(self):
        """Clear all cached data."""
        for cache_file in self.cache_dir.glob('scan_*.json'):
            try:
                cache_file.unlink()
            except IOError:
                pass

    def is_cached(self, directory: str) -> bool:
        """Check if directory has cached results."""
        return self.get(directory) is not None

    def get_file_from_cache(self, directory: str, file_path: str) -> Optional[Dict]:
        """
        Get cached information for a specific file.

        Args:
            directory: Root directory
            file_path: File path

        Returns:
            Cached file info or None
        """
        cached = self.get(directory)

        if not cached:
            return None

        # Look for file in cached results
        for file_info in cached.get('results', {}).get('files', []):
            if file_info['path'] == file_path:
                return file_info

        return None

    def should_use_cache(self, directory: str, file_path: Path) -> bool:
        """
        Check if cached data is still valid for a file.

        Args:
            directory: Root directory
            file_path: File path

        Returns:
            True if cache is valid for this file
        """
        cached_info = self.get_file_from_cache(directory, str(file_path))

        if not cached_info:
            return False

        # Check if file has been modified since cache
        try:
            current_mtime = file_path.stat().st_mtime
            cached_mtime = datetime.fromisoformat(cached_info['modified']).timestamp()

            # Use cache if file hasn't been modified
            return abs(current_mtime - cached_mtime) < 1.0  # Allow 1 second tolerance

        except (OSError, KeyError, ValueError):
            return False
