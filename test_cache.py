#!/usr/bin/env python3
"""Test cached scanner"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fileorganizer.scanner_cached import CachedFileScanner

def test_cache():
    print("Testing Cached Scanner")
    print("=" * 60)

    # First scan (no cache)
    print("\n1. First scan (building cache)...")
    start = time.time()
    scanner1 = CachedFileScanner('/tmp/test_files', use_cache=True)
    results1 = scanner1.scan()
    time1 = time.time() - start
    print(f"   Time: {time1:.3f}s")
    print(f"   Files: {results1['file_count']}")

    # Second scan (with cache)
    print("\n2. Second scan (using cache)...")
    start = time.time()
    scanner2 = CachedFileScanner('/tmp/test_files', use_cache=True)
    results2 = scanner2.scan()
    time2 = time.time() - start
    print(f"   Time: {time2:.3f}s")
    print(f"   Files: {results2['file_count']}")

    # Calculate speedup
    if time2 < time1:
        speedup = time1 / time2
        print(f"\n✓ Cache provides {speedup:.1f}x speedup!")
    else:
        print(f"\n⚠ Cache didn't improve speed (too few files)")

    # Verify results are the same
    if results1['file_count'] == results2['file_count']:
        print("✓ Results are consistent")
    else:
        print("✗ Results differ!")
        return False

    return True

if __name__ == '__main__':
    success = test_cache()
    sys.exit(0 if success else 1)
