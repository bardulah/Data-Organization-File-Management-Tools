"""
Built-in plugins for common organization tasks.
"""

from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import re

from .base import Plugin


class InvoiceOrganizerPlugin(Plugin):
    """Plugin for organizing invoice files."""

    def __init__(self):
        """Initialize invoice organizer plugin."""
        super().__init__()
        self.name = "InvoiceOrganizer"
        self.version = "1.0.0"

    def should_process(self, file_path: Path, metadata: Dict) -> bool:
        """Check if file is an invoice."""
        # Check if filename contains invoice-related keywords
        name_lower = file_path.name.lower()
        invoice_keywords = ['invoice', 'inv_', 'inv-', 'bill', 'receipt']

        if any(keyword in name_lower for keyword in invoice_keywords):
            return True

        # Check if it's a PDF with invoice metadata
        if file_path.suffix.lower() == '.pdf' and metadata.get('pdf_info'):
            pdf_text = metadata.get('extracted_text', '')
            if pdf_text and 'invoice' in pdf_text.lower():
                return True

        return False

    def get_target_path(self, file_path: Path, metadata: Dict, target_root: Path) -> Path:
        """Organize invoices by vendor and date."""
        # Try to extract vendor name from filename
        vendor = self._extract_vendor(file_path.name)

        # Try to extract date
        date = self._extract_date(file_path, metadata)

        if date:
            # Organize as: Invoices/Vendor/YYYY/MM/filename
            year = date.strftime('%Y')
            month = date.strftime('%m')
            return target_root / 'Invoices' / vendor / year / month / file_path.name
        else:
            # Organize as: Invoices/Vendor/filename
            return target_root / 'Invoices' / vendor / file_path.name

    def _extract_vendor(self, filename: str) -> str:
        """Extract vendor name from filename."""
        # Remove common prefixes
        name = filename
        for prefix in ['invoice_', 'inv_', 'inv-', 'bill_', 'receipt_']:
            if name.lower().startswith(prefix):
                name = name[len(prefix):]
                break

        # Take first part before date or number
        # Example: "Amazon_2024-01-15.pdf" -> "Amazon"
        parts = re.split(r'[-_\s]\d', name)
        if parts:
            vendor = parts[0].strip('_-. ')
            if vendor:
                return vendor.title()

        return 'Unknown_Vendor'

    def _extract_date(self, file_path: Path, metadata: Dict) -> Optional[datetime]:
        """Extract date from filename or metadata."""
        # Try filename patterns
        filename = file_path.stem

        # Pattern: YYYY-MM-DD or YYYY_MM_DD
        pattern1 = r'(\d{4})[-_](\d{2})[-_](\d{2})'
        match = re.search(pattern1, filename)
        if match:
            try:
                return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                pass

        # Pattern: YYYYMMDD
        pattern2 = r'(\d{8})'
        match = re.search(pattern2, filename)
        if match:
            try:
                date_str = match.group(1)
                return datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                pass

        # Try smart date from metadata
        if metadata.get('smart_date'):
            try:
                return datetime.fromisoformat(metadata['smart_date'])
            except:
                pass

        # Fall back to modified date
        if metadata.get('modified'):
            try:
                return datetime.fromisoformat(metadata['modified'])
            except:
                pass

        return None


class PhotoOrganizerPlugin(Plugin):
    """Plugin for organizing photos by date taken (EXIF)."""

    def __init__(self):
        """Initialize photo organizer plugin."""
        super().__init__()
        self.name = "PhotoOrganizer"
        self.version = "1.0.0"

        self.photo_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            '.tiff', '.tif', '.webp', '.heic', '.raw',
            '.cr2', '.nef', '.arw', '.dng'
        }

    def should_process(self, file_path: Path, metadata: Dict) -> bool:
        """Check if file is a photo."""
        return file_path.suffix.lower() in self.photo_extensions

    def get_target_path(self, file_path: Path, metadata: Dict, target_root: Path) -> Path:
        """Organize photos by date taken (YYYY/MM/DD)."""
        # Try to get smart date (EXIF date taken)
        date = None

        if metadata.get('smart_date'):
            try:
                date = datetime.fromisoformat(metadata['smart_date'])
            except:
                pass

        # Fall back to modified date
        if not date and metadata.get('modified'):
            try:
                date = datetime.fromisoformat(metadata['modified'])
            except:
                pass

        if date:
            year = date.strftime('%Y')
            month = date.strftime('%m')
            day = date.strftime('%d')
            return target_root / 'Photos' / year / month / day / file_path.name
        else:
            # No date available - put in undated folder
            return target_root / 'Photos' / 'Undated' / file_path.name

    def get_new_filename(self, file_path: Path, metadata: Dict) -> Optional[str]:
        """Generate filename with date prefix if not already present."""
        # Check if filename already starts with date
        if re.match(r'^\d{4}[-_]\d{2}[-_]\d{2}', file_path.stem):
            return None

        # Get date
        date = None
        if metadata.get('smart_date'):
            try:
                date = datetime.fromisoformat(metadata['smart_date'])
            except:
                pass

        if date:
            date_prefix = date.strftime('%Y-%m-%d')
            return f"{date_prefix}_{file_path.name}"

        return None


class DocumentOrganizerPlugin(Plugin):
    """Plugin for organizing documents by type and year."""

    def __init__(self):
        """Initialize document organizer plugin."""
        super().__init__()
        self.name = "DocumentOrganizer"
        self.version = "1.0.0"

        self.document_extensions = {
            '.pdf', '.doc', '.docx', '.txt', '.rtf',
            '.odt', '.pages'
        }

    def should_process(self, file_path: Path, metadata: Dict) -> bool:
        """Check if file is a document."""
        return file_path.suffix.lower() in self.document_extensions

    def get_target_path(self, file_path: Path, metadata: Dict, target_root: Path) -> Path:
        """Organize documents by year."""
        # Get date
        date = None

        if metadata.get('smart_date'):
            try:
                date = datetime.fromisoformat(metadata['smart_date'])
            except:
                pass

        if not date and metadata.get('modified'):
            try:
                date = datetime.fromisoformat(metadata['modified'])
            except:
                pass

        if date:
            year = date.strftime('%Y')
            return target_root / 'Documents' / year / file_path.name
        else:
            return target_root / 'Documents' / 'Unsorted' / file_path.name


class ProjectOrganizerPlugin(Plugin):
    """Plugin for organizing project files by project name."""

    def __init__(self):
        """Initialize project organizer plugin."""
        super().__init__()
        self.name = "ProjectOrganizer"
        self.version = "1.0.0"

        self.project_extensions = {
            '.xcodeproj', '.project', '.sln', '.csproj',
            '.vcxproj', '.iml', '.gradle'
        }

        self.code_extensions = {
            '.py', '.java', '.cpp', '.c', '.h', '.js',
            '.ts', '.go', '.rs', '.rb', '.php', '.cs'
        }

    def should_process(self, file_path: Path, metadata: Dict) -> bool:
        """Check if file is project-related."""
        if file_path.suffix.lower() in self.project_extensions:
            return True

        # Check if in a project directory structure
        parts = file_path.parts
        project_indicators = {'src', 'source', 'lib', 'include', 'test', 'tests'}

        return (file_path.suffix.lower() in self.code_extensions and
                any(part.lower() in project_indicators for part in parts))

    def get_target_path(self, file_path: Path, metadata: Dict, target_root: Path) -> Path:
        """Organize by project name (detected from path)."""
        # Try to find project root
        project_name = self._find_project_name(file_path)

        return target_root / 'Projects' / project_name / file_path.name

    def _find_project_name(self, file_path: Path) -> str:
        """Find project name from path."""
        # Look for common project indicators in parent directories
        current = file_path.parent

        for _ in range(5):  # Check up to 5 levels up
            # Check for project files
            if any((current / pattern).exists()
                   for pattern in ['*.project', '*.sln', '.git', 'package.json', 'Cargo.toml']):
                return current.name

            if current.parent == current:
                break
            current = current.parent

        return 'Unknown_Project'
