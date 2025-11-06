#!/usr/bin/env python3
"""Test production scanner with logging and progress."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fileorganizer.scanner_production import ProductionScanner
from fileorganizer.logging_config import setup_logging

def test_production():
    print("Testing Production Scanner")
    print("=" * 60)

    # Setup logging
    setup_logging(verbose=True)

    # Test on large dataset
    test_dir = '/tmp/large_test'

    print(f"\n1. Testing with progress indicators...")
    scanner = ProductionScanner(test_dir, use_cache=False, show_progress=True)
    results = scanner.scan()

    print(f"\n2. Results:")
    print(f"   Files: {results['file_count']}")
    print(f"   Size: {results['total_size']} bytes")
    print(f"   Duplicates: {len(results['duplicates'])} groups")
    print(f"   Duration: {results['scan_duration']:.2f}s")
    print(f"   Errors: {len(results['errors'])}")

    # Test with cache
    print(f"\n3. Testing with cache...")
    scanner2 = ProductionScanner(test_dir, use_cache=True, show_progress=True)
    results2 = scanner2.scan()
    print(f"   Duration: {results2['scan_duration']:.2f}s")

    print(f"\n✓ Production scanner works!")
    return True

if __name__ == '__main__':
    try:
        success = test_production()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
