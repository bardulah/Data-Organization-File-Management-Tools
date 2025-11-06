#!/usr/bin/env python3
"""
File Organization Assistant v1.5.1 - Production Release
Production-ready with logging, progress, and robust error handling.
"""

import argparse
import sys
from pathlib import Path

from .scanner_production import ProductionScanner
from .duplicates import DuplicateManager
from .operation_log import OperationLog
from .organizer import FileOrganizer
from .logging_config import setup_logging, get_logger


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def cmd_scan(args):
    """Execute scan command."""
    logger = get_logger(__name__)
    logger.info(f"Scan command: {args.directory}")

    try:
        scanner = ProductionScanner(
            args.directory,
            exclude_dirs=args.exclude,
            use_cache=not args.no_cache,
            show_progress=not args.quiet
        )

        results = scanner.scan(include_hidden=args.include_hidden)

        # Print summary
        print(f"\n{'='*60}")
        print("SCAN RESULTS")
        print(f"{'='*60}")
        print(f"Files found: {results['file_count']:,}")
        print(f"Total size: {format_size(results['total_size'])}")
        print(f"Scan time: {results['scan_duration']:.2f}s")

        if results.get('errors'):
            print(f"⚠ Errors: {len(results['errors'])} (see log for details)")

        # Show duplicates if found
        if results['duplicates']:
            print(f"\nDuplicates found:")
            dup_manager = DuplicateManager()
            analysis = dup_manager.analyze_duplicates(results['duplicates'])

            print(f"  Groups: {analysis['duplicate_groups']}")
            print(f"  Duplicate files: {analysis['total_duplicate_files']}")
            print(f"  Wasted space: {format_size(analysis['wasted_space'])}")

            if args.show_duplicates:
                print("\nTop duplicate groups:")
                sorted_dups = sorted(
                    results['duplicates'].items(),
                    key=lambda x: x[1][0]['size'] * len(x[1]),
                    reverse=True
                )

                for i, (hash_val, files) in enumerate(sorted_dups[:5], 1):
                    wasted = files[0]['size'] * (len(files) - 1)
                    print(f"\n  #{i}: {len(files)} copies, {format_size(wasted)} wasted")
                    for f in files[:3]:
                        print(f"    - {f['path']}")
                    if len(files) > 3:
                        print(f"    ... and {len(files) - 3} more")

        print(f"{'='*60}\n")

        logger.info("Scan completed successfully")
        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.error(f"Scan failed: {e}", exc_info=True)
        return 1


def cmd_duplicates(args):
    """Handle duplicates."""
    logger = get_logger(__name__)
    logger.info(f"Duplicates command: {args.directory}")

    try:
        # Scan for duplicates
        scanner = ProductionScanner(args.directory, show_progress=not args.quiet)
        results = scanner.scan()
        duplicates = results['duplicates']

        if not duplicates:
            print("\n✓ No duplicates found!")
            return 0

        # Analyze
        dup_manager = DuplicateManager(dry_run=args.dry_run)
        analysis = dup_manager.analyze_duplicates(duplicates)

        print(f"\n{'='*60}")
        print(f"Found {analysis['duplicate_groups']} duplicate groups")
        print(f"Duplicate files: {analysis['total_duplicate_files']}")
        print(f"Wasted space: {format_size(analysis['wasted_space'])}")
        print(f"{'='*60}\n")

        if args.action == 'report':
            report_file = args.report or 'duplicate_report.txt'
            dup_manager.create_duplicate_report(duplicates, report_file)
            print(f"✓ Report saved to: {report_file}")
            logger.info(f"Duplicate report saved to {report_file}")

        elif args.action in ['remove', 'move']:
            if args.dry_run:
                print("[DRY RUN MODE - No files will be modified]\n")

            if args.action == 'move' and not args.target:
                print("✗ Error: --target directory required for move action")
                return 1

            # Confirm if not dry run
            if not args.dry_run and not args.yes:
                response = input(f"Proceed with {args.action}? [y/N]: ")
                if response.lower() != 'y':
                    print("Cancelled")
                    return 0

            # Execute operation
            op_log = OperationLog()

            if args.action == 'remove':
                operations = dup_manager.remove_duplicates(duplicates, keep_strategy=args.keep)
                action_word = "Would remove" if args.dry_run else "Removed"
                print(f"\n✓ {action_word} {len(operations)} duplicate files")

            else:  # move
                operations = dup_manager.move_duplicates(duplicates, args.target, keep_strategy=args.keep)

                if not args.dry_run:
                    for op in operations:
                        if op['action'] == 'move_duplicate':
                            op_log.log_move(op['source'], op['destination'])

                action_word = "Would move" if args.dry_run else "Moved"
                print(f"\n✓ {action_word} {len(operations)} files to {args.target}")

            logger.info(f"Duplicates {args.action}: {len(operations)} files")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.error(f"Duplicates command failed: {e}", exc_info=True)
        return 1


def cmd_undo(args):
    """Undo operations."""
    logger = get_logger(__name__)

    try:
        op_log = OperationLog()

        if args.list:
            operations = op_log.get_undoable_operations(limit=args.limit)

            if not operations:
                print("No operations to undo")
                return 0

            print(f"\n{'='*60}")
            print("UNDOABLE OPERATIONS")
            print(f"{'='*60}")

            for op in operations:
                timestamp = op['timestamp'][:19]
                print(f"\n[{op['id']}] {timestamp} - {op['type']}")

                if op['type'] == 'move':
                    print(f"  From: {op['source']}")
                    print(f"  To:   {op['destination']}")

            print(f"\n{'='*60}")
            print(f"To undo: fileorganizer undo <id>\n")

            return 0

        if args.operation_id:
            # Confirm
            if not args.yes:
                response = input(f"Undo operation {args.operation_id}? [y/N]: ")
                if response.lower() != 'y':
                    print("Cancelled")
                    return 0

            success = op_log.undo_operation(args.operation_id)
            logger.info(f"Undo operation {args.operation_id}: {success}")
            return 0 if success else 1

        # Show stats
        stats = op_log.get_stats()
        print(f"\n{'='*60}")
        print("OPERATION LOG STATISTICS")
        print(f"{'='*60}")
        print(f"Total operations: {stats['total_operations']}")
        print(f"Active: {stats['active']}")
        print(f"Undone: {stats['undone']}")

        if stats['by_type']:
            print("\nBy type:")
            for op_type, count in stats['by_type'].items():
                print(f"  {op_type}: {count}")

        print(f"{'='*60}\n")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.error(f"Undo command failed: {e}", exc_info=True)
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='File Organization Assistant v1.5.1 - Production Release',
        epilog='Examples:\n'
               '  fileorganizer scan ~/Downloads\n'
               '  fileorganizer scan ~/Downloads --show-duplicates\n'
               '  fileorganizer duplicates ~/Documents --action move --target ~/Duplicates\n'
               '  fileorganizer undo --list\n',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging output')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress progress indicators')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan directory')
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
    dup_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompts')

    # Undo command
    undo_parser = subparsers.add_parser('undo', help='Undo operations')
    undo_parser.add_argument('operation_id', nargs='?', type=int, help='Operation ID to undo')
    undo_parser.add_argument('--list', action='store_true', help='List undoable operations')
    undo_parser.add_argument('--limit', type=int, default=10, help='Number of operations to show')
    undo_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')

    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)

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
        print(f"\n✗ Unexpected error: {e}")
        get_logger(__name__).error(f"Unexpected error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
