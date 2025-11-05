"""
File organizer module for moving and renaming files.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import re


class FileOrganizer:
    """Organizes files into structured directories."""

    # Default file type categories
    FILE_CATEGORIES = {
        'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.tex'],
        'Spreadsheets': ['.xls', '.xlsx', '.csv', '.ods'],
        'Presentations': ['.ppt', '.pptx', '.key', '.odp'],
        'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp', '.tiff'],
        'Videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'],
        'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'],
        'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
        'Code': ['.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift'],
        'Web': ['.html', '.css', '.scss', '.sass', '.less'],
        'Data': ['.json', '.xml', '.yaml', '.yml', '.sql', '.db', '.sqlite'],
        'Executables': ['.exe', '.msi', '.app', '.deb', '.rpm', '.dmg'],
        'Fonts': ['.ttf', '.otf', '.woff', '.woff2'],
    }

    def __init__(self, dry_run: bool = True):
        """
        Initialize the file organizer.

        Args:
            dry_run: If True, only simulate operations without making changes
        """
        self.dry_run = dry_run
        self.operations = []

    def get_category(self, file_path: Path) -> str:
        """
        Determine the category of a file based on its extension.

        Args:
            file_path: Path to the file

        Returns:
            Category name or 'Other'
        """
        extension = file_path.suffix.lower()

        for category, extensions in self.FILE_CATEGORIES.items():
            if extension in extensions:
                return category

        return 'Other'

    def suggest_structure(self, scan_results: Dict) -> Dict[str, List[str]]:
        """
        Suggest an organized folder structure based on scanned files.

        Args:
            scan_results: Results from FileScanner.scan()

        Returns:
            Dictionary mapping suggested folders to file paths
        """
        structure = {}

        for file_info in scan_results['files']:
            file_path = Path(file_info['path'])
            category = self.get_category(file_path)

            if category not in structure:
                structure[category] = []

            structure[category].append(str(file_path))

        return structure

    def organize_by_type(self, source_dir: str, target_dir: str) -> List[Dict]:
        """
        Organize files by type into categorized folders.

        Args:
            source_dir: Source directory to organize
            target_dir: Target directory for organized files

        Returns:
            List of operations performed
        """
        source_path = Path(source_dir)
        target_path = Path(target_dir)
        operations = []

        for file_path in source_path.rglob('*'):
            if file_path.is_file():
                category = self.get_category(file_path)
                category_dir = target_path / category
                dest_path = category_dir / file_path.name

                # Handle name conflicts
                counter = 1
                original_dest = dest_path
                while dest_path.exists():
                    dest_path = category_dir / f"{original_dest.stem}_{counter}{original_dest.suffix}"
                    counter += 1

                operation = {
                    'action': 'move',
                    'source': str(file_path),
                    'destination': str(dest_path),
                    'category': category
                }

                if not self.dry_run:
                    category_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(dest_path))

                operations.append(operation)

        return operations

    def organize_by_date(self, source_dir: str, target_dir: str, date_format: str = "%Y/%m") -> List[Dict]:
        """
        Organize files by modification date.

        Args:
            source_dir: Source directory to organize
            target_dir: Target directory for organized files
            date_format: Format for date-based folders (e.g., %Y/%m for Year/Month)

        Returns:
            List of operations performed
        """
        source_path = Path(source_dir)
        target_path = Path(target_dir)
        operations = []

        for file_path in source_path.rglob('*'):
            if file_path.is_file():
                try:
                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    date_dir = target_path / mod_time.strftime(date_format)
                    dest_path = date_dir / file_path.name

                    # Handle name conflicts
                    counter = 1
                    original_dest = dest_path
                    while dest_path.exists():
                        dest_path = date_dir / f"{original_dest.stem}_{counter}{original_dest.suffix}"
                        counter += 1

                    operation = {
                        'action': 'move',
                        'source': str(file_path),
                        'destination': str(dest_path),
                        'date': mod_time.isoformat()
                    }

                    if not self.dry_run:
                        date_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(file_path), str(dest_path))

                    operations.append(operation)

                except (PermissionError, OSError) as e:
                    print(f"Warning: Could not process {file_path}: {e}")

        return operations

    def rename_files(self, directory: str, pattern: str, replacement: str,
                    use_regex: bool = False) -> List[Dict]:
        """
        Batch rename files based on a pattern.

        Args:
            directory: Directory containing files to rename
            pattern: Pattern to match in filenames
            replacement: Replacement string
            use_regex: Whether to use regex matching

        Returns:
            List of rename operations
        """
        dir_path = Path(directory)
        operations = []

        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                old_name = file_path.name

                if use_regex:
                    new_name = re.sub(pattern, replacement, old_name)
                else:
                    new_name = old_name.replace(pattern, replacement)

                if new_name != old_name:
                    new_path = file_path.parent / new_name

                    # Handle conflicts
                    counter = 1
                    original_new_path = new_path
                    while new_path.exists() and new_path != file_path:
                        new_path = file_path.parent / f"{original_new_path.stem}_{counter}{original_new_path.suffix}"
                        counter += 1

                    operation = {
                        'action': 'rename',
                        'old_name': old_name,
                        'new_name': new_path.name,
                        'path': str(file_path.parent)
                    }

                    if not self.dry_run:
                        file_path.rename(new_path)

                    operations.append(operation)

        return operations

    def smart_rename(self, directory: str, template: str = "{date}_{name}") -> List[Dict]:
        """
        Rename files using a smart template with variables.

        Variables:
            {date} - Modification date (YYYY-MM-DD)
            {time} - Modification time (HH-MM-SS)
            {name} - Original filename (without extension)
            {ext} - File extension
            {counter} - Sequential counter

        Args:
            directory: Directory containing files to rename
            template: Template for new filenames

        Returns:
            List of rename operations
        """
        dir_path = Path(directory)
        operations = []
        counter = 1

        for file_path in sorted(dir_path.rglob('*')):
            if file_path.is_file():
                stat_info = file_path.stat()
                mod_time = datetime.fromtimestamp(stat_info.st_mtime)

                # Replace template variables
                new_name = template
                new_name = new_name.replace('{date}', mod_time.strftime('%Y-%m-%d'))
                new_name = new_name.replace('{time}', mod_time.strftime('%H-%M-%S'))
                new_name = new_name.replace('{name}', file_path.stem)
                new_name = new_name.replace('{ext}', file_path.suffix[1:] if file_path.suffix else '')
                new_name = new_name.replace('{counter}', f"{counter:03d}")

                # Add extension if not in template
                if not new_name.endswith(file_path.suffix):
                    new_name += file_path.suffix

                new_path = file_path.parent / new_name

                # Handle conflicts
                conflict_counter = 1
                original_new_path = new_path
                while new_path.exists() and new_path != file_path:
                    new_path = file_path.parent / f"{original_new_path.stem}_{conflict_counter}{original_new_path.suffix}"
                    conflict_counter += 1

                operation = {
                    'action': 'smart_rename',
                    'old_name': file_path.name,
                    'new_name': new_path.name,
                    'path': str(file_path.parent)
                }

                if not self.dry_run:
                    file_path.rename(new_path)

                operations.append(operation)
                counter += 1

        return operations
