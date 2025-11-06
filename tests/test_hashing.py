"""
Tests for hashing utilities.
"""

import pytest
from pathlib import Path
import tempfile
import hashlib

from fileorganizer.utils.hashing import calculate_hash, quick_hash, smart_hash, verify_duplicate


class TestHashing:
    """Test hashing functions."""

    def test_calculate_hash_basic(self, tmp_path):
        """Test basic hash calculation."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        content = b"Hello, World!"
        test_file.write_bytes(content)

        # Calculate hash
        file_hash = calculate_hash(test_file)

        # Verify against known hash
        expected = hashlib.sha256(content).hexdigest()
        assert file_hash == expected

    def test_calculate_hash_different_algorithms(self, tmp_path):
        """Test different hash algorithms."""
        test_file = tmp_path / "test.txt"
        content = b"Test content"
        test_file.write_bytes(content)

        # Test SHA256
        hash_sha256 = calculate_hash(test_file, algorithm='sha256')
        assert hash_sha256 == hashlib.sha256(content).hexdigest()

        # Test MD5
        hash_md5 = calculate_hash(test_file, algorithm='md5')
        assert hash_md5 == hashlib.md5(content).hexdigest()

    def test_calculate_hash_nonexistent(self, tmp_path):
        """Test hash calculation on nonexistent file."""
        nonexistent = tmp_path / "nonexistent.txt"
        result = calculate_hash(nonexistent)
        assert result is None

    def test_quick_hash_small_file(self, tmp_path):
        """Test quick hash on small file (should do full hash)."""
        test_file = tmp_path / "small.txt"
        content = b"Small file content"
        test_file.write_bytes(content)

        # Quick hash of small file should match full hash
        quick = quick_hash(test_file)
        full = calculate_hash(test_file)

        assert quick == full

    def test_quick_hash_large_file(self, tmp_path):
        """Test quick hash on large file."""
        test_file = tmp_path / "large.txt"

        # Create a 10MB file
        with open(test_file, 'wb') as f:
            f.write(b'A' * (10 * 1024 * 1024))

        # Quick hash should return something
        result = quick_hash(test_file)
        assert result is not None
        assert len(result) == 64  # SHA256 hex length

    def test_smart_hash_threshold(self, tmp_path):
        """Test smart hash behavior based on size threshold."""
        # Small file
        small_file = tmp_path / "small.txt"
        small_file.write_bytes(b"Small" * 100)

        hash_small, is_quick_small = smart_hash(small_file, threshold_mb=1)
        assert not is_quick_small  # Should use full hash

        # Large file
        large_file = tmp_path / "large.txt"
        with open(large_file, 'wb') as f:
            f.write(b'X' * (2 * 1024 * 1024))  # 2MB

        hash_large, is_quick_large = smart_hash(large_file, threshold_mb=1)
        assert is_quick_large  # Should use quick hash

    def test_verify_duplicate_identical(self, tmp_path):
        """Test verification of identical files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        content = b"Identical content"
        file1.write_bytes(content)
        file2.write_bytes(content)

        assert verify_duplicate(file1, file2) is True

    def test_verify_duplicate_different(self, tmp_path):
        """Test verification of different files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_bytes(b"Content 1")
        file2.write_bytes(b"Content 2")

        assert verify_duplicate(file1, file2) is False

    def test_verify_duplicate_different_sizes(self, tmp_path):
        """Test verification fails fast on different sizes."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_bytes(b"Short")
        file2.write_bytes(b"Much longer content")

        assert verify_duplicate(file1, file2) is False
