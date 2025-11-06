#!/usr/bin/env python3
"""Test undo functionality"""
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fileorganizer.operation_log import OperationLog

def test_undo():
    print("Testing Undo Functionality")
    print("=" * 60)

    # Setup test files
    test_dir = Path('/tmp/test_undo')
    test_dir.mkdir(exist_ok=True)

    source_dir = test_dir / 'source'
    dest_dir = test_dir / 'dest'
    source_dir.mkdir(exist_ok=True)
    dest_dir.mkdir(exist_ok=True)

    test_file = source_dir / 'test.txt'
    test_file.write_text('Test content')

    print(f"\n1. Setup:")
    print(f"   Created: {test_file}")

    # Initialize operation log
    log = OperationLog(test_dir / 'operations.json')
    log.clear_log()  # Start fresh

    # Test move with logging
    print(f"\n2. Move file:")
    moved_file = dest_dir / 'test.txt'
    shutil.move(str(test_file), str(moved_file))
    log.log_move(str(test_file), str(moved_file))
    print(f"   Moved to: {moved_file}")
    print(f"   Source exists: {test_file.exists()}")
    print(f"   Dest exists: {moved_file.exists()}")

    # Show recent operations
    print(f"\n3. Recent operations:")
    recent = log.get_recent_operations(limit=5)
    for op in recent:
        print(f"   [{op['id']}] {op['type']}: {Path(op['source']).name} -> {Path(op['destination']).name}")

    # Undo the move
    print(f"\n4. Undo the move:")
    if recent:
        success = log.undo_operation(recent[0]['id'])
        print(f"   Undo successful: {success}")
        print(f"   Source exists: {test_file.exists()}")
        print(f"   Dest exists: {moved_file.exists()}")

        if test_file.exists() and not moved_file.exists():
            print(f"\n✓ Undo works correctly!")
            return True
        else:
            print(f"\n✗ Undo failed!")
            return False
    else:
        print("✗ No operations to undo")
        return False

if __name__ == '__main__':
    try:
        success = test_undo()
        sys.exit(0 if success else 1)
    finally:
        # Cleanup
        import shutil
        test_dir = Path('/tmp/test_undo')
        if test_dir.exists():
            shutil.rmtree(test_dir)
