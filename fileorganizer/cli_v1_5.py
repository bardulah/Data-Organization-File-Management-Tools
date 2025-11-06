#!/usr/bin/env python3
"""
File Organization Assistant v1.5 - Practical, working improvements
"""

import argparse
import sys
from pathlib import Path

from .scanner_cached import CachedFileScanner
from .duplicates import DuplicateManager
from .operation_log import OperationLog
from .organizer import FileOrganizer


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def cmd_scan(args):
    """Execute scan command with caching."""
    print(f"\n{'='*60}")
    print(f"Scanning: {args.directory}")
    print(f"{'='*60}\n")

    scanner = CachedFileScanner(
        args.directory,
        exclude_dirs=args.exclude,
        use_cache=not args.no_cache
    )

    results = scanner.scan(include_hidden=args.include_hidden)

    # Print results
    print(f"\n✓ Scan complete!")
    print(f"  Files found: {results['file_count']:,}")
    print(f"  Total size: {format_size(results['total_size'])}")

    if 'scan_duration' in results:
        print(f"  Scan time: {results['scan_duration']:.2f}s")

    # Show duplicates if found
    if results['duplicates']:
        print(f"\n  Duplicates: {len(results['duplicates'])} groups found")

        dup_manager = DuplicateManager()
        analysis = dup_manager.analyze_duplicates(results['duplicates'])

        print(f"  Duplicate files: {analysis['total_duplicate_files']}")
        print(f"  Wasted space: {format_size(analysis['wasted_space'])}")

        if args.show_duplicates:
            print("\n  Top duplicate groups:")
            sorted_dups = sorted(
                results['duplicates'].items(),
                key=lambda x: len(x[1]),
                reverse=True
            )

            for i, (hash_val, files) in enumerate(sorted_dups[:5], 1):
                print(f"\n  Group {i}: {len(files)} copies ({format_size(files[0]['size'])} each)")
                for f in files[:3]:
                    print(f"    - {f['path']}")
                if len(files) > 3:
                    print(f"    ... and {len(files) - 3} more")

    return 0


def cmd_duplicates(args):
    """Handle duplicates."""
    print(f"\n{'='*60}")
    print(f"Finding duplicates in: {args.directory}")
    print(f"{'='*60}\n")

    # Scan for duplicates
    scanner = CachedFileScanner(args.directory)
    results = scanner.scan()
    duplicates = results['duplicates']

    if not duplicates:
        print("✓ No duplicates found!")
        return 0

    # Analyze
    dup_manager = DuplicateManager(dry_run=args.dry_run)
    analysis = dup_manager.analyze_duplicates(duplicates)

    print(f"✓ Found {analysis['duplicate_groups']} duplicate groups")
    print(f"  Duplicate files: {analysis['total_duplicate_files']}")
    print(f"  Wasted space: {format_size(analysis['wasted_space'])}")

    if args.action == 'report':
        report_file = args.report or 'duplicate_report.txt'
        dup_manager.create_duplicate_report(duplicates, report_file)
        print(f"\n✓ Report saved to: {report_file}")

    elif args.action == 'remove':
        if args.dry_run:
            print("\n[DRY RUN - No files will be deleted]")

        operations = dup_manager.remove_duplicates(duplicates, keep_strategy=args.keep)

        print(f"\n✓ Would remove {len(operations)} duplicate files" if args.dry_run else f"\n✓ Removed {len(operations)} duplicate files")

    elif args.action == 'move':
        if not args.target:
            print("✗ Error: --target directory required for move action")
            return 1

        if args.dry_run:
            print("\n[DRY RUN - No files will be moved]")

        # Initialize operation log
        op_log = OperationLog()

        operations = dup_manager.move_duplicates(duplicates, args.target, keep_strategy=args.keep)

        # Log all moves
        if not args.dry_run:
            for op in operations:
                if op['action'] == 'move_duplicate':
                    op_log.log_move(op['source'], op['destination'])

        print(f"\n✓ Moved {len(operations)} duplicate files to {args.target}")

    return 0


def cmd_undo(args):
    """Undo operations."""
    op_log = OperationLog()

    if args.list:
        # List recent operations
        operations = op_log.get_undoable_operations(limit=args.limit)

        if not operations:
            print("No operations to undo")
            return 0

        print("\nUndoable operations:")
        print("-" * 60)

        for op in operations:
            timestamp = op['timestamp'][:19]  # Remove microseconds
            print(f"[{op['id']}] {timestamp} - {op['type']}")

            if op['type'] == 'move':
                print(f"     {op['source']}")
                print(f"  -> {op['destination']}")

        print("-" * 60)
        print(f"\nTo undo: fileorganizer undo <id>")

        return 0

    if args.operation_id:
        # Undo specific operation
        success = op_log.undo_operation(args.operation_id)
        return 0 if success else 1

    # Show stats if no arguments
    stats = op_log.get_stats()
    print("\nOperation Log Statistics:")
    print(f"  Total operations: {stats['total_operations']}")
    print(f"  Active: {stats['active']}")
    print(f"  Undone: {stats['undone']}")

    if stats['by_type']:
        print("\n  By type:")
        for op_type, count in stats['by_type'].items():
            print(f"    {op_type}: {count}")

    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='File Organization Assistant v1.5',
        epilog='Examples:\n'
               '  fileorganizer scan ~/Downloads\n'
               '  fileorganizer duplicates ~/Documents --action move --target ~/Duplicates\n'
               '  fileorganizer undo --list\n'
               '  fileorganizer undo 42',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan directory (with caching)')
    scan_parser.add_argument('directory', help='Directory to scan')
    scan_parser.add_argument('--exclude', nargs='+', help='Directories to exclude')
    scan_parser.add_argument('--include-hidden', action='store_true', help='Include hidden files')
    scan_parser.add_argument('--show-duplicates', action='store_true', help='Show duplicate details')
    scan_parser.add_argument('--no-cache', action='store_true', help='Disable caching')

    # Duplicates command
    dup_parser = subparsers.add_parser('duplicates', help='Find and manage duplicates')
    dup_parser.add_argument('directory', help='Directory to scan')
    dup_parser.add_argument('--action', choices=['report', 'remove', 'move'],
                           default='report', help='Action to perform')
    dup_parser.add_argument('--keep', choices=['newest', 'oldest', 'shortest_path', 'first'],
                           default='newest', help='Which file to keep')
    dup_parser.add_argument('--target', help='Target directory for move action')
    dup_parser.add_argument('--report', help='Report file name')
    dup_parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')

    # Undo command
    undo_parser = subparsers.add_parser('undo', help='Undo operations')
    undo_parser.add_argument('operation_id', nargs='?', type=int, help='Operation ID to undo')
    undo_parser.add_argument('--list', action='store_true', help='List undoable operations')
    undo_parser.add_argument('--limit', type=int, default=10, help='Number of operations to show')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == 'scan':
            return cmd_scan(args)
        elif args.command == 'duplicates':
            return cmd_duplicates(args)
        elif args.command == 'undo':
            return cmd_undo(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
