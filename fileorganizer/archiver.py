"""
File archiver module for managing old and unused files.
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class FileArchiver:
    """Archives old or unused files."""

    def __init__(self, dry_run: bool = True):
        """
        Initialize the file archiver.

        Args:
            dry_run: If True, only simulate operations without making changes
        """
        self.dry_run = dry_run

    def archive_old_files(self, source_dir: str, archive_dir: str,
                         days_threshold: int = 365,
                         compress: bool = True) -> Dict:
        """
        Archive files that haven't been accessed in a specified number of days.

        Args:
            source_dir: Directory to scan for old files
            archive_dir: Directory to store archived files
            days_threshold: Number of days to consider a file as old
            compress: Whether to compress files into a zip archive

        Returns:
            Dictionary containing archive operation results
        """
        source_path = Path(source_dir)
        archive_path = Path(archive_dir)
        threshold_date = datetime.now().timestamp() - (days_threshold * 24 * 60 * 60)

        old_files = []
        total_size = 0

        # Find old files
        for file_path in source_path.rglob('*'):
            if file_path.is_file():
                try:
                    stat_info = file_path.stat()
                    if stat_info.st_atime < threshold_date:
                        old_files.append(file_path)
                        total_size += stat_info.st_size
                except (PermissionError, OSError):
                    pass

        results = {
            'files_archived': len(old_files),
            'total_size': total_size,
            'archive_path': None,
            'operations': []
        }

        if not old_files:
            return results

        if not self.dry_run:
            archive_path.mkdir(parents=True, exist_ok=True)

        if compress:
            # Create a zip archive
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_name = f"archive_{timestamp}.zip"
            zip_path = archive_path / zip_name

            if not self.dry_run:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in old_files:
                        # Preserve relative path structure in archive
                        arcname = file_path.relative_to(source_path)
                        zipf.write(file_path, arcname)

                        results['operations'].append({
                            'action': 'archived_to_zip',
                            'source': str(file_path),
                            'archive': str(zip_path)
                        })

                # Delete original files after successful archiving
                for file_path in old_files:
                    try:
                        file_path.unlink()
                    except (PermissionError, OSError) as e:
                        print(f"Warning: Could not delete {file_path}: {e}")

            results['archive_path'] = str(zip_path)

        else:
            # Move files to archive directory
            for file_path in old_files:
                # Preserve relative path structure
                rel_path = file_path.relative_to(source_path)
                dest_path = archive_path / rel_path

                if not self.dry_run:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(dest_path))

                results['operations'].append({
                    'action': 'moved_to_archive',
                    'source': str(file_path),
                    'destination': str(dest_path)
                })

            results['archive_path'] = str(archive_path)

        return results

    def archive_by_extension(self, source_dir: str, archive_dir: str,
                           extensions: List[str],
                           compress: bool = True) -> Dict:
        """
        Archive files with specific extensions.

        Args:
            source_dir: Directory to scan
            archive_dir: Directory to store archived files
            extensions: List of file extensions to archive (e.g., ['.tmp', '.log'])
            compress: Whether to compress files into a zip archive

        Returns:
            Dictionary containing archive operation results
        """
        source_path = Path(source_dir)
        archive_path = Path(archive_dir)

        files_to_archive = []
        total_size = 0

        # Find files with matching extensions
        for file_path in source_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                files_to_archive.append(file_path)
                try:
                    total_size += file_path.stat().st_size
                except (PermissionError, OSError):
                    pass

        results = {
            'files_archived': len(files_to_archive),
            'total_size': total_size,
            'archive_path': None,
            'operations': []
        }

        if not files_to_archive:
            return results

        if not self.dry_run:
            archive_path.mkdir(parents=True, exist_ok=True)

        if compress:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext_str = '_'.join(ext.replace('.', '') for ext in extensions)
            zip_name = f"archive_{ext_str}_{timestamp}.zip"
            zip_path = archive_path / zip_name

            if not self.dry_run:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in files_to_archive:
                        arcname = file_path.relative_to(source_path)
                        zipf.write(file_path, arcname)

                        results['operations'].append({
                            'action': 'archived_to_zip',
                            'source': str(file_path),
                            'archive': str(zip_path)
                        })

                # Delete original files
                for file_path in files_to_archive:
                    try:
                        file_path.unlink()
                    except (PermissionError, OSError) as e:
                        print(f"Warning: Could not delete {file_path}: {e}")

            results['archive_path'] = str(zip_path)

        else:
            for file_path in files_to_archive:
                rel_path = file_path.relative_to(source_path)
                dest_path = archive_path / rel_path

                if not self.dry_run:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(dest_path))

                results['operations'].append({
                    'action': 'moved_to_archive',
                    'source': str(file_path),
                    'destination': str(dest_path)
                })

            results['archive_path'] = str(archive_path)

        return results

    def cleanup_empty_dirs(self, directory: str) -> List[str]:
        """
        Remove empty directories recursively.

        Args:
            directory: Root directory to clean up

        Returns:
            List of removed directories
        """
        dir_path = Path(directory)
        removed_dirs = []

        # Walk bottom-up to remove nested empty directories
        for root, dirs, files in os.walk(dir_path, topdown=False):
            for dir_name in dirs:
                dir_to_check = Path(root) / dir_name
                try:
                    # Check if directory is empty
                    if not any(dir_to_check.iterdir()):
                        if not self.dry_run:
                            dir_to_check.rmdir()
                        removed_dirs.append(str(dir_to_check))
                except (PermissionError, OSError):
                    pass

        return removed_dirs
