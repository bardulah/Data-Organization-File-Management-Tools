#!/usr/bin/env python3
"""Benchmark v1 vs v1.5 scanner performance"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fileorganizer.scanner import FileScanner
from fileorganizer.scanner_cached import CachedFileScanner
from fileorganizer.cache import ScanCache

def benchmark():
    test_dir = '/tmp/large_test'

    print("="*60)
    print("PERFORMANCE BENCHMARK: v1 vs v1.5")
    print("="*60)
    print(f"Test directory: {test_dir}")
    print(f"Files: ~1,000")
    print()

    # Clear cache first
    cache = ScanCache()
    cache.invalidate(test_dir)

    # Benchmark v1 (no cache)
    print("1. v1 Scanner (no cache)...")
    start = time.time()
    scanner_v1 = FileScanner(test_dir)
    results_v1 = scanner_v1.scan()
    time_v1 = time.time() - start
    print(f"   Time: {time_v1:.3f}s")
    print(f"   Files: {results_v1['file_count']}")

    # Benchmark v1.5 first scan (building cache)
    cache.invalidate(test_dir)
    print("\n2. v1.5 Scanner - First scan (building cache)...")
    start = time.time()
    scanner_v15_1 = CachedFileScanner(test_dir, use_cache=True)
    results_v15_1 = scanner_v15_1.scan()
    time_v15_1 = time.time() - start
    print(f"   Time: {time_v15_1:.3f}s")
    print(f"   Files: {results_v15_1['file_count']}")

    # Benchmark v1.5 second scan (using cache)
    print("\n3. v1.5 Scanner - Second scan (using cache)...")
    start = time.time()
    scanner_v15_2 = CachedFileScanner(test_dir, use_cache=True)
    results_v15_2 = scanner_v15_2.scan()
    time_v15_2 = time.time() - start
    print(f"   Time: {time_v15_2:.3f}s")
    print(f"   Files: {results_v15_2['file_count']}")

    # Results
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)

    if time_v15_1 < time_v1:
        print(f"✓ v1.5 first scan is {time_v1/time_v15_1:.1f}x faster than v1")
    else:
        print(f"  v1.5 first scan: {time_v15_1/time_v1:.1f}x slower (cache building overhead)")

    speedup = time_v1 / time_v15_2
    print(f"✓ v1.5 cached scan is {speedup:.1f}x faster than v1")

    cache_speedup = time_v15_1 / time_v15_2
    print(f"✓ Cache provides {cache_speedup:.1f}x speedup on subsequent scans")

    print(f"\nFor users rescanning the same directory:")
    print(f"  Time saved per scan: {time_v1 - time_v15_2:.3f}s")

    # Verify correctness
    if results_v1['file_count'] == results_v15_2['file_count']:
        print(f"\n✓ Results are consistent")
    else:
        print(f"\n✗ Warning: File counts differ!")

if __name__ == '__main__':
    benchmark()
