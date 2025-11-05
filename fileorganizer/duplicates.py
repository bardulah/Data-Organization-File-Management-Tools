"""
Duplicate file detection and management.
"""

import os
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict


class DuplicateManager:
    """Manages duplicate file detection and removal."""

    def __init__(self, dry_run: bool = True):
        """
        Initialize the duplicate manager.

        Args:
            dry_run: If True, only simulate operations without making changes
        """
        self.dry_run = dry_run

    def find_duplicates(self, scan_results: Dict) -> Dict[str, List[Dict]]:
        """
        Find duplicate files from scan results.

        Args:
            scan_results: Results from FileScanner.scan()

        Returns:
            Dictionary mapping file hashes to lists of duplicate files
        """
        return scan_results.get('duplicates', {})

    def analyze_duplicates(self, duplicates: Dict[str, List[Dict]]) -> Dict:
        """
        Analyze duplicate files and calculate statistics.

        Args:
            duplicates: Dictionary of duplicate files

        Returns:
            Analysis results including space wasted
        """
        total_duplicates = 0
        wasted_space = 0
        duplicate_groups = len(duplicates)

        for hash_val, files in duplicates.items():
            if len(files) > 1:
                # Count all but one as duplicates
                total_duplicates += len(files) - 1
                # Calculate wasted space (all duplicates beyond the first)
                file_size = files[0]['size']
                wasted_space += file_size * (len(files) - 1)

        return {
            'duplicate_groups': duplicate_groups,
            'total_duplicate_files': total_duplicates,
            'wasted_space': wasted_space,
            'wasted_space_mb': wasted_space / (1024 * 1024),
            'wasted_space_gb': wasted_space / (1024 * 1024 * 1024)
        }

    def remove_duplicates(self, duplicates: Dict[str, List[Dict]],
                         keep_strategy: str = 'newest') -> List[Dict]:
        """
        Remove duplicate files, keeping one copy based on a strategy.

        Args:
            duplicates: Dictionary of duplicate files
            keep_strategy: Strategy for which file to keep
                          - 'newest': Keep the most recently modified file
                          - 'oldest': Keep the oldest file
                          - 'shortest_path': Keep file with shortest path
                          - 'first': Keep the first file in the list

        Returns:
            List of removal operations
        """
        operations = []

        for hash_val, files in duplicates.items():
            if len(files) <= 1:
                continue

            # Determine which file to keep
            if keep_strategy == 'newest':
                files_sorted = sorted(files, key=lambda x: x['modified'], reverse=True)
            elif keep_strategy == 'oldest':
                files_sorted = sorted(files, key=lambda x: x['modified'])
            elif keep_strategy == 'shortest_path':
                files_sorted = sorted(files, key=lambda x: len(x['path']))
            else:  # 'first'
                files_sorted = files

            keep_file = files_sorted[0]
            remove_files = files_sorted[1:]

            for file_info in remove_files:
                file_path = Path(file_info['path'])

                operation = {
                    'action': 'delete_duplicate',
                    'path': str(file_path),
                    'size': file_info['size'],
                    'kept_file': keep_file['path'],
                    'hash': hash_val
                }

                if not self.dry_run:
                    try:
                        file_path.unlink()
                        operation['status'] = 'deleted'
                    except (PermissionError, OSError) as e:
                        operation['status'] = 'failed'
                        operation['error'] = str(e)
                else:
                    operation['status'] = 'simulated'

                operations.append(operation)

        return operations

    def move_duplicates(self, duplicates: Dict[str, List[Dict]],
                       target_dir: str,
                       keep_strategy: str = 'newest') -> List[Dict]:
        """
        Move duplicate files to a target directory instead of deleting them.

        Args:
            duplicates: Dictionary of duplicate files
            target_dir: Directory to move duplicates to
            keep_strategy: Strategy for which file to keep (same as remove_duplicates)

        Returns:
            List of move operations
        """
        operations = []
        target_path = Path(target_dir)

        if not self.dry_run:
            target_path.mkdir(parents=True, exist_ok=True)

        for hash_val, files in duplicates.items():
            if len(files) <= 1:
                continue

            # Determine which file to keep
            if keep_strategy == 'newest':
                files_sorted = sorted(files, key=lambda x: x['modified'], reverse=True)
            elif keep_strategy == 'oldest':
                files_sorted = sorted(files, key=lambda x: x['modified'])
            elif keep_strategy == 'shortest_path':
                files_sorted = sorted(files, key=lambda x: len(x['path']))
            else:
                files_sorted = files

            keep_file = files_sorted[0]
            move_files = files_sorted[1:]

            for file_info in move_files:
                source_path = Path(file_info['path'])
                dest_path = target_path / source_path.name

                # Handle name conflicts
                counter = 1
                original_dest = dest_path
                while dest_path.exists():
                    dest_path = target_path / f"{original_dest.stem}_{counter}{original_dest.suffix}"
                    counter += 1

                operation = {
                    'action': 'move_duplicate',
                    'source': str(source_path),
                    'destination': str(dest_path),
                    'size': file_info['size'],
                    'kept_file': keep_file['path'],
                    'hash': hash_val
                }

                if not self.dry_run:
                    try:
                        import shutil
                        shutil.move(str(source_path), str(dest_path))
                        operation['status'] = 'moved'
                    except (PermissionError, OSError) as e:
                        operation['status'] = 'failed'
                        operation['error'] = str(e)
                else:
                    operation['status'] = 'simulated'

                operations.append(operation)

        return operations

    def create_duplicate_report(self, duplicates: Dict[str, List[Dict]],
                               output_file: str = 'duplicate_report.txt') -> str:
        """
        Create a human-readable report of duplicate files.

        Args:
            duplicates: Dictionary of duplicate files
            output_file: Path to save the report

        Returns:
            Path to the report file
        """
        analysis = self.analyze_duplicates(duplicates)

        with open(output_file, 'w') as f:
            f.write("DUPLICATE FILES REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total duplicate groups: {analysis['duplicate_groups']}\n")
            f.write(f"Total duplicate files: {analysis['total_duplicate_files']}\n")
            f.write(f"Wasted space: {analysis['wasted_space_mb']:.2f} MB ")
            f.write(f"({analysis['wasted_space_gb']:.2f} GB)\n\n")
            f.write("=" * 80 + "\n\n")

            for i, (hash_val, files) in enumerate(duplicates.items(), 1):
                if len(files) <= 1:
                    continue

                f.write(f"Duplicate Group #{i}\n")
                f.write(f"Hash: {hash_val}\n")
                f.write(f"Size: {files[0]['size']:,} bytes\n")
                f.write(f"Count: {len(files)} copies\n")
                f.write(f"Wasted space: {files[0]['size'] * (len(files) - 1):,} bytes\n\n")

                for j, file_info in enumerate(files, 1):
                    f.write(f"  {j}. {file_info['path']}\n")
                    f.write(f"     Modified: {file_info['modified']}\n")

                f.write("\n" + "-" * 80 + "\n\n")

        return output_file
