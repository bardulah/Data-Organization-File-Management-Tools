"""
Smart file detection - EXIF data, PDF parsing, content analysis.
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Optional imports with graceful fallback
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL not available - EXIF extraction disabled")

try:
    from PyPDF2 import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
    logger.warning("PyPDF2 not available - PDF parsing disabled")

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    logger.warning("python-magic not available - content-based type detection disabled")


class SmartDetector:
    """Detects file metadata and content intelligently."""

    def __init__(self):
        """Initialize smart detector."""
        self.capabilities = {
            'exif': HAS_PIL,
            'pdf': HAS_PYPDF,
            'magic': HAS_MAGIC
        }

    def get_smart_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract smart metadata from file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'extension': file_path.suffix.lower(),
            'size': 0,
            'modified_time': None,
            'detected_type': None,
            'smart_date': None,
            'extracted_text': None,
            'exif_data': None,
            'pdf_metadata': None
        }

        try:
            stat = file_path.stat()
            metadata['size'] = stat.st_size
            metadata['modified_time'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        except Exception as e:
            logger.warning(f"Could not get file stats for {file_path}: {e}")

        # Detect content type
        if HAS_MAGIC:
            metadata['detected_type'] = self.detect_content_type(file_path)

        # Extract EXIF for images
        if self._is_image(file_path) and HAS_PIL:
            metadata['exif_data'] = self.extract_exif(file_path)
            if metadata['exif_data']:
                # Try to get actual photo date
                metadata['smart_date'] = self._get_exif_date(metadata['exif_data'])

        # Extract PDF metadata
        elif file_path.suffix.lower() == '.pdf' and HAS_PYPDF:
            metadata['pdf_metadata'] = self.extract_pdf_metadata(file_path)
            if metadata['pdf_metadata']:
                # Try to extract dates and text
                metadata['smart_date'] = self._get_pdf_date(metadata['pdf_metadata'])
                metadata['extracted_text'] = self.extract_pdf_text(file_path, max_pages=1)

        return metadata

    def detect_content_type(self, file_path: Path) -> Optional[str]:
        """
        Detect file type by content (not extension).

        Args:
            file_path: Path to file

        Returns:
            MIME type or None
        """
        if not HAS_MAGIC:
            return None

        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(str(file_path))
        except Exception as e:
            logger.debug(f"Could not detect content type for {file_path}: {e}")
            return None

    def extract_exif(self, image_path: Path) -> Optional[Dict]:
        """
        Extract EXIF data from image.

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with EXIF data or None
        """
        if not HAS_PIL:
            return None

        try:
            image = Image.open(image_path)
            exif_data = image._getexif()

            if not exif_data:
                return None

            # Convert EXIF tags to readable names
            exif = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                exif[tag] = value

            logger.debug(f"Extracted EXIF from {image_path}: {len(exif)} tags")
            return exif

        except Exception as e:
            logger.debug(f"Could not extract EXIF from {image_path}: {e}")
            return None

    def extract_pdf_metadata(self, pdf_path: Path) -> Optional[Dict]:
        """
        Extract metadata from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with PDF metadata or None
        """
        if not HAS_PYPDF:
            return None

        try:
            reader = PdfReader(pdf_path)
            metadata = {}

            # Extract document info
            if reader.metadata:
                for key, value in reader.metadata.items():
                    # Remove leading slash from keys
                    clean_key = key.lstrip('/')
                    metadata[clean_key] = value

            # Add page count
            metadata['page_count'] = len(reader.pages)

            logger.debug(f"Extracted PDF metadata from {pdf_path}")
            return metadata

        except Exception as e:
            logger.debug(f"Could not extract PDF metadata from {pdf_path}: {e}")
            return None

    def extract_pdf_text(self, pdf_path: Path, max_pages: int = 5) -> Optional[str]:
        """
        Extract text from PDF.

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to extract

        Returns:
            Extracted text or None
        """
        if not HAS_PYPDF:
            return None

        try:
            reader = PdfReader(pdf_path)
            text_parts = []

            for i, page in enumerate(reader.pages[:max_pages]):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    logger.debug(f"Could not extract text from page {i}: {e}")

            return '\n'.join(text_parts) if text_parts else None

        except Exception as e:
            logger.debug(f"Could not extract text from PDF {pdf_path}: {e}")
            return None

    def extract_dates_from_text(self, text: str) -> list:
        """
        Extract dates from text using regex patterns.

        Args:
            text: Text to search

        Returns:
            List of found date strings
        """
        if not text:
            return []

        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}\.\d{2}\.\d{4}',  # DD.MM.YYYY
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',  # DD Month YYYY
        ]

        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)

        return dates

    def extract_invoice_info(self, pdf_path: Path) -> Optional[Dict]:
        """
        Extract invoice-specific information from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with invoice info (vendor, date, number) or None
        """
        text = self.extract_pdf_text(pdf_path, max_pages=2)

        if not text:
            return None

        info = {
            'vendor': None,
            'invoice_number': None,
            'invoice_date': None,
            'amount': None
        }

        # Look for common invoice patterns
        # Invoice number
        invoice_patterns = [
            r'Invoice\s*#?\s*:?\s*([A-Z0-9-]+)',
            r'Invoice\s+Number\s*:?\s*([A-Z0-9-]+)',
            r'INV[-\s]?([A-Z0-9-]+)'
        ]

        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['invoice_number'] = match.group(1)
                break

        # Dates
        dates = self.extract_dates_from_text(text)
        if dates:
            info['invoice_date'] = dates[0]

        # Amount
        amount_patterns = [
            r'Total\s*:?\s*\$?([0-9,]+\.?\d*)',
            r'Amount\s+Due\s*:?\s*\$?([0-9,]+\.?\d*)',
        ]

        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['amount'] = match.group(1)
                break

        logger.debug(f"Extracted invoice info from {pdf_path}: {info}")
        return info

    def get_smart_date(self, file_path: Path) -> Optional[datetime]:
        """
        Get the "smart" date for a file (actual creation date, not modified).

        For photos: EXIF date taken
        For PDFs: Document creation date
        For others: File modified date

        Args:
            file_path: Path to file

        Returns:
            datetime object or None
        """
        metadata = self.get_smart_metadata(file_path)

        if metadata.get('smart_date'):
            return metadata['smart_date']

        # Fallback to file modified time
        if metadata.get('modified_time'):
            try:
                return datetime.fromisoformat(metadata['modified_time'])
            except:
                pass

        return None

    def _is_image(self, file_path: Path) -> bool:
        """Check if file is an image."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        return file_path.suffix.lower() in image_extensions

    def _get_exif_date(self, exif_data: Dict) -> Optional[datetime]:
        """Extract date from EXIF data."""
        # Try different date tags
        date_tags = ['DateTimeOriginal', 'DateTime', 'DateTimeDigitized']

        for tag in date_tags:
            if tag in exif_data:
                try:
                    # EXIF date format: "YYYY:MM:DD HH:MM:SS"
                    date_str = str(exif_data[tag])
                    return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                except Exception as e:
                    logger.debug(f"Could not parse EXIF date {exif_data[tag]}: {e}")

        return None

    def _get_pdf_date(self, pdf_metadata: Dict) -> Optional[datetime]:
        """Extract date from PDF metadata."""
        # Try different date fields
        date_fields = ['CreationDate', 'ModDate']

        for field in date_fields:
            if field in pdf_metadata:
                try:
                    # PDF date format: "D:YYYYMMDDHHmmSS"
                    date_str = str(pdf_metadata[field])

                    # Strip D: prefix and timezone
                    if date_str.startswith('D:'):
                        date_str = date_str[2:16]  # Get YYYYMMDDHHmmSS

                    return datetime.strptime(date_str, '%Y%m%d%H%M%S')
                except Exception as e:
                    logger.debug(f"Could not parse PDF date {pdf_metadata[field]}: {e}")

        return None


# Global instance
_detector = None


def get_detector() -> SmartDetector:
    """Get global SmartDetector instance."""
    global _detector
    if _detector is None:
        _detector = SmartDetector()
    return _detector
