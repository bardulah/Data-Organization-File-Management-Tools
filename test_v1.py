#!/usr/bin/env python3
"""
Quick test of v1 scanner functionality
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from fileorganizer.scanner import FileScanner

def test_scanner():
    print("Testing FileScanner on /tmp/test_files")
    print("=" * 60)

    try:
        scanner = FileScanner('/tmp/test_files')
        results = scanner.scan()

        print(f"✓ Scan completed successfully")
        print(f"  Files found: {results['file_count']}")
        print(f"  Total size: {results['total_size']} bytes")
        print(f"  Duplicates: {len(results['duplicates'])} groups")

        if results['duplicates']:
            print("\n  Duplicate files:")
            for hash_val, files in results['duplicates'].items():
                print(f"    {len(files)} copies:")
                for f in files:
                    print(f"      - {f['name']}")

        print("\n✓ Scanner works correctly!")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_scanner()
    sys.exit(0 if success else 1)
