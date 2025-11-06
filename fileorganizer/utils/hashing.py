"""
Improved hashing utilities with parallel processing support.
"""

import hashlib
from pathlib import Path
from typing import Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

# Constants
CHUNK_SIZE = 65536  # 64KB chunks
QUICK_HASH_SIZE = 1048576  # 1MB for quick hash (first and last 512KB)


def calculate_hash(
    file_path: Path,
    algorithm: str = 'sha256',
    chunk_size: int = CHUNK_SIZE
) -> Optional[str]:
    """
    Calculate cryptographic hash of a file.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (sha256, md5, sha1)
        chunk_size: Size of chunks to read

    Returns:
        Hash string or None if error
    """
    try:
        hash_obj = hashlib.new(algorithm)

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    except (IOError, PermissionError, OSError) as e:
        logger.warning(f"Could not hash {file_path}: {e}")
        return None


def quick_hash(file_path: Path, size: int = QUICK_HASH_SIZE) -> Optional[str]:
    """
    Calculate a quick hash based on file size and first/last chunks.
    Useful for quickly identifying potential duplicates of large files.

    Args:
        file_path: Path to the file
        size: Total size to hash from beginning and end

    Returns:
        Quick hash string or None if error
    """
    try:
        file_size = file_path.stat().st_size

        # For small files, just do a full hash
        if file_size <= size:
            return calculate_hash(file_path)

        hash_obj = hashlib.sha256()

        # Hash file size first (cheap way to differentiate)
        hash_obj.update(str(file_size).encode())

        chunk_size = size // 2

        with open(file_path, 'rb') as f:
            # Hash first chunk
            first_chunk = f.read(chunk_size)
            hash_obj.update(first_chunk)

            # Hash last chunk
            f.seek(-chunk_size, 2)  # Seek from end
            last_chunk = f.read(chunk_size)
            hash_obj.update(last_chunk)

        return hash_obj.hexdigest()

    except (IOError, PermissionError, OSError) as e:
        logger.warning(f"Could not quick hash {file_path}: {e}")
        return None


def calculate_hash_parallel(
    file_paths: list,
    algorithm: str = 'sha256',
    max_workers: Optional[int] = None
) -> dict:
    """
    Calculate hashes for multiple files in parallel.

    Args:
        file_paths: List of file paths
        algorithm: Hash algorithm to use
        max_workers: Maximum number of parallel workers (None = CPU count)

    Returns:
        Dictionary mapping file paths to hashes
    """
    results = {}

    # Use ProcessPoolExecutor for CPU-bound hashing
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_path = {
            executor.submit(calculate_hash, Path(fp), algorithm): fp
            for fp in file_paths
        }

        # Collect results as they complete
        for future in as_completed(future_to_path):
            file_path = future_to_path[future]
            try:
                hash_value = future.result()
                if hash_value:
                    results[file_path] = hash_value
            except Exception as e:
                logger.error(f"Error hashing {file_path}: {e}")

    return results


def smart_hash(file_path: Path, threshold_mb: int = 100) -> Tuple[str, bool]:
    """
    Smart hashing strategy: quick hash for large files, full hash for small files.

    Args:
        file_path: Path to the file
        threshold_mb: Size threshold in MB for using quick hash

    Returns:
        Tuple of (hash, is_quick_hash)
    """
    try:
        file_size = file_path.stat().st_size
        threshold_bytes = threshold_mb * 1024 * 1024

        if file_size > threshold_bytes:
            # Large file - use quick hash
            hash_value = quick_hash(file_path)
            return (hash_value, True) if hash_value else (None, False)
        else:
            # Small file - use full hash
            hash_value = calculate_hash(file_path)
            return (hash_value, False) if hash_value else (None, False)

    except Exception as e:
        logger.error(f"Error in smart_hash for {file_path}: {e}")
        return (None, False)


def verify_duplicate(file1: Path, file2: Path) -> bool:
    """
    Verify two files are truly identical with full hash comparison.
    Use this after quick hash suggests they might be duplicates.

    Args:
        file1: First file path
        file2: Second file path

    Returns:
        True if files are identical
    """
    # First check: file sizes must match
    try:
        if file1.stat().st_size != file2.stat().st_size:
            return False
    except (IOError, OSError):
        return False

    # Second check: full hash comparison
    hash1 = calculate_hash(file1)
    hash2 = calculate_hash(file2)

    return hash1 is not None and hash1 == hash2
