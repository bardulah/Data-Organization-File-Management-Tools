"""
Improved file scanner with progress bars, parallel hashing, and caching.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import logging

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from ..utils.hashing import calculate_hash, smart_hash, calculate_hash_parallel
from ..utils.errors import FileOrganizerError, handle_error
from ..database import Database
from ..smart_detection import get_detector

logger = logging.getLogger(__name__)


class ScannerV2:
    """Improved file scanner with caching and parallel processing."""

    def __init__(
        self,
        root_path: str,
        exclude_dirs: Optional[List[str]] = None,
        use_cache: bool = True,
        parallel_hashing: bool = True,
        smart_detection: bool = False,
        show_progress: bool = True
    ):
        """
        Initialize the improved scanner.

        Args:
            root_path: Root directory to scan
            exclude_dirs: List of directory names to exclude
            use_cache: Whether to use incremental caching
            parallel_hashing: Whether to use parallel hashing for speed
            smart_detection: Whether to extract smart metadata (EXIF, PDF, etc.)
            show_progress: Whether to show progress bars
        """
        self.root_path = Path(root_path)
        self.exclude_dirs = set(exclude_dirs or [
            '.git', '.svn', 'node_modules', '__pycache__', '.venv',
            'venv', '__MACOSX', '.DS_Store'
        ])
        self.use_cache = use_cache
        self.parallel_hashing = parallel_hashing
        self.smart_detection = smart_detection
        self.show_progress = show_progress and HAS_TQDM

        self.db = Database() if use_cache else None
        self.detector = get_detector() if smart_detection else None

        self.files_by_hash = defaultdict(list)
        self.files_by_extension = defaultdict(list)
        self.total_size = 0
        self.file_count = 0

    def scan(
        self,
        include_hidden: bool = False,
        quick_scan: bool = False,
        update_cache: bool = True
    ) -> Dict:
        """
        Scan the directory tree and collect file information.

        Args:
            include_hidden: Whether to include hidden files
            quick_scan: Use quick hash for large files (faster but less accurate)
            update_cache: Whether to update the cache after scanning

        Returns:
            Dictionary containing scan results
        """
        logger.info(f"Starting scan of {self.root_path}")
        start_time = datetime.now()

        # Load cache if available
        cached_files = {}
        if self.use_cache and self.db:
            cached_files = self.db.get_scan_cache(str(self.root_path))
            logger.info(f"Loaded {len(cached_files)} cached files")

        results = {
            'files': [],
            'duplicates': {},
            'by_extension': {},
            'total_size': 0,
            'file_count': 0,
            'scan_date': datetime.now().isoformat(),
            'cache_hits': 0,
            'cache_misses': 0,
            'scan_duration': 0
        }

        # Phase 1: Discover files
        logger.info("Phase 1: Discovering files...")
        files_to_process = []

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

                    # Check cache
                    rel_path = str(file_path.relative_to(self.root_path))
                    cached = cached_files.get(rel_path)

                    # Use cache if file hasn't been modified
                    if cached and cached['modified_time'] == stat_info.st_mtime:
                        file_info = {
                            'path': str(file_path),
                            'name': filename,
                            'size': cached['file_size'],
                            'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                            'extension': file_path.suffix.lower(),
                            'hash': cached['file_hash'],
                            'cached': True
                        }
                        results['cache_hits'] += 1
                    else:
                        # Need to process this file
                        file_info = {
                            'path': str(file_path),
                            'name': filename,
                            'size': stat_info.st_size,
                            'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                            'accessed': datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                            'extension': file_path.suffix.lower(),
                            'modified_time': stat_info.st_mtime,
                            'cached': False
                        }
                        files_to_process.append(file_info)
                        results['cache_misses'] += 1

                    results['files'].append(file_info)
                    self.total_size += stat_info.st_size
                    self.file_count += 1

                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not access {file_path}: {e}")

        logger.info(f"Found {len(results['files'])} files ({results['cache_hits']} from cache)")

        # Phase 2: Hash files (parallel if enabled)
        if files_to_process:
            logger.info(f"Phase 2: Hashing {len(files_to_process)} files...")

            if self.parallel_hashing:
                self._hash_files_parallel(files_to_process, quick_scan)
            else:
                self._hash_files_sequential(files_to_process, quick_scan)

        # Phase 3: Smart detection (if enabled)
        if self.smart_detection and self.detector:
            logger.info("Phase 3: Extracting smart metadata...")
            self._extract_smart_metadata(files_to_process)

        # Phase 4: Organize results
        logger.info("Phase 4: Organizing results...")

        for file_info in results['files']:
            # Group by hash for duplicate detection
            if 'hash' in file_info and file_info['hash']:
                self.files_by_hash[file_info['hash']].append(file_info)

            # Group by extension
            ext = file_info['extension'] or '.no_extension'
            self.files_by_extension[ext].append(file_info)

            # Update cache
            if update_cache and self.use_cache and self.db and not file_info.get('cached'):
                try:
                    rel_path = str(Path(file_info['path']).relative_to(self.root_path))
                    self.db.update_scan_cache(
                        str(self.root_path),
                        rel_path,
                        {
                            'hash': file_info.get('hash'),
                            'size': file_info['size'],
                            'modified_time': file_info.get('modified_time', 0)
                        }
                    )
                except Exception as e:
                    logger.debug(f"Could not update cache: {e}")

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

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        results['scan_duration'] = duration

        logger.info(f"Scan complete in {duration:.2f}s: {self.file_count} files, "
                   f"{len(results['duplicates'])} duplicate groups")

        return results

    def _hash_files_parallel(self, files: List[Dict], quick_scan: bool):
        """Hash files in parallel."""
        file_paths = [f['path'] for f in files]

        # Create progress bar
        progress = None
        if self.show_progress:
            progress = tqdm(total=len(file_paths), desc="Hashing files", unit="file")

        # Use ProcessPoolExecutor for CPU-bound hashing
        with ProcessPoolExecutor() as executor:
            futures = {}

            for file_info in files:
                file_path = Path(file_info['path'])
                future = executor.submit(
                    smart_hash if quick_scan else calculate_hash,
                    file_path
                )
                futures[future] = file_info

            # Collect results
            for future in as_completed(futures):
                file_info = futures[future]
                try:
                    result = future.result()

                    if quick_scan:
                        hash_value, is_quick = result
                        file_info['hash'] = hash_value
                        file_info['quick_hash'] = is_quick
                    else:
                        file_info['hash'] = result

                except Exception as e:
                    logger.warning(f"Failed to hash {file_info['path']}: {e}")

                if progress:
                    progress.update(1)

        if progress:
            progress.close()

    def _hash_files_sequential(self, files: List[Dict], quick_scan: bool):
        """Hash files sequentially."""
        progress = None
        if self.show_progress:
            progress = tqdm(files, desc="Hashing files", unit="file")
        else:
            files_iter = files

        files_iter = progress if progress else files

        for file_info in files_iter:
            file_path = Path(file_info['path'])

            try:
                if quick_scan:
                    hash_value, is_quick = smart_hash(file_path)
                    file_info['hash'] = hash_value
                    file_info['quick_hash'] = is_quick
                else:
                    file_info['hash'] = calculate_hash(file_path)

            except Exception as e:
                logger.warning(f"Failed to hash {file_path}: {e}")

    def _extract_smart_metadata(self, files: List[Dict]):
        """Extract smart metadata from files."""
        progress = None
        if self.show_progress:
            progress = tqdm(files, desc="Extracting metadata", unit="file")
        else:
            files_iter = files

        files_iter = progress if progress else files

        for file_info in files_iter:
            try:
                file_path = Path(file_info['path'])
                metadata = self.detector.get_smart_metadata(file_path)

                # Add smart metadata to file info
                if metadata.get('smart_date'):
                    file_info['smart_date'] = metadata['smart_date'].isoformat()

                if metadata.get('exif_data'):
                    file_info['has_exif'] = True

                if metadata.get('pdf_metadata'):
                    file_info['pdf_info'] = metadata['pdf_metadata']

                if metadata.get('detected_type'):
                    file_info['mime_type'] = metadata['detected_type']

            except Exception as e:
                logger.debug(f"Could not extract metadata from {file_info['path']}: {e}")

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

        progress = None
        if self.show_progress:
            # Count files first
            total = sum(1 for _ in self.root_path.rglob('*') if _.is_file())
            progress = tqdm(total=total, desc="Finding old files", unit="file")

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

                    if progress:
                        progress.update(1)

                except (PermissionError, OSError):
                    pass

        if progress:
            progress.close()

        return sorted(old_files, key=lambda x: x['days_since_access'], reverse=True)
