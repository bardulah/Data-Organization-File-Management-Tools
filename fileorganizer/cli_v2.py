#!/usr/bin/env python3
"""
Improved command-line interface with all new features integrated.
"""

import argparse
import json
import sys
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from .core.scanner_v2 import ScannerV2
from .organizer import FileOrganizer
from .archiver import FileArchiver
from .duplicates import DuplicateManager
from .database import Database
from .undo import UndoManager
from .config import Config
from .interactive import InteractiveMode
from .plugins import PluginManager
from .utils.logging import setup_logging, get_logger
from .utils.errors import FileOrganizerError

logger = None  # Will be initialized after setup_logging


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_section(text: str):
    """Print a formatted section header."""
    print(f"\n{text}")
    print("-" * len(text))


def cmd_scan(args, config: Config, db: Database):
    """Execute the scan command with new features."""
    print_header(f"Scanning Directory: {args.directory}")

    session_id = str(uuid.uuid4())[:8]
    operation_id = db.start_operation(
        session_id,
        f"scan {args.directory}",
        'scan',
        {'include_hidden': args.include_hidden, 'smart': args.smart}
    )

    try:
        scanner = ScannerV2(
            args.directory,
            exclude_dirs=args.exclude or config.get('exclude_dirs'),
            use_cache=args.use_cache,
            parallel_hashing=args.parallel,
            smart_detection=args.smart,
            show_progress=not args.no_progress
        )

        start_time = datetime.now()
        results = scanner.scan(
            include_hidden=args.include_hidden,
            quick_scan=args.quick
        )
        duration = (datetime.now() - start_time).total_seconds()

        # Show results
        print(f"✓ Files scanned: {results['file_count']:,}")
        print(f"✓ Total size: {format_size(results['total_size'])}")
        print(f"✓ Scan duration: {duration:.2f}s")

        if args.use_cache:
            print(f"✓ Cache hits: {results['cache_hits']}")
            print(f"✓ Cache misses: {results['cache_misses']}")

        # Show file type distribution
        if args.verbose:
            print_section("File Types Distribution")
            by_extension = results['by_extension']
            sorted_extensions = sorted(by_extension.items(), key=lambda x: len(x[1]), reverse=True)

            for ext, files in sorted_extensions[:15]:
                count = len(files)
                total_size = sum(f['size'] for f in files)
                print(f"  {ext:20s} {count:6,} files  {format_size(total_size):>10s}")

        # Show duplicates if found
        duplicates = results['duplicates']
        if duplicates:
            print_section("Duplicate Files Found")
            duplicate_manager = DuplicateManager()
            dup_analysis = duplicate_manager.analyze_duplicates(duplicates)

            print(f"  ✓ Duplicate groups: {dup_analysis['duplicate_groups']}")
            print(f"  ✓ Duplicate files: {dup_analysis['total_duplicate_files']}")
            print(f"  ✓ Wasted space: {format_size(dup_analysis['wasted_space'])}")

            if args.show_duplicates:
                print("\n  Top duplicate groups:")
                sorted_dups = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)
                for hash_val, files in sorted_dups[:5]:
                    print(f"\n    {len(files)} copies ({format_size(files[0]['size'])} each):")
                    for file_info in files[:3]:
                        print(f"      - {file_info['path']}")
                    if len(files) > 3:
                        print(f"      ... and {len(files) - 3} more")

        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n✓ Results saved to: {args.output}")

        db.complete_operation(operation_id, 'completed', duration)

    except Exception as e:
        logger.error(f"Scan failed: {e}")
        db.complete_operation(operation_id, 'failed')
        if args.verbose:
            raise
        else:
            print(f"\n❌ Error: {e}")
            return 1

    return 0


def cmd_duplicates(args, config: Config, db: Database):
    """Execute the duplicates command with interactive mode."""
    print_header(f"Finding Duplicates in: {args.directory}")

    session_id = str(uuid.uuid4())[:8]
    operation_id = db.start_operation(
        session_id,
        f"duplicates {args.directory}",
        'duplicates',
        {'action': args.action}
    )

    try:
        # Scan for duplicates
        scanner = ScannerV2(
            args.directory,
            exclude_dirs=args.exclude or config.get('exclude_dirs'),
            show_progress=not args.no_progress
        )
        results = scanner.scan()
        duplicates = results['duplicates']

        if not duplicates:
            print("✓ No duplicate files found!")
            db.complete_operation(operation_id, 'completed')
            return 0

        duplicate_manager = DuplicateManager(dry_run=args.dry_run)
        analysis = duplicate_manager.analyze_duplicates(duplicates)

        print(f"✓ Duplicate groups: {analysis['duplicate_groups']}")
        print(f"✓ Duplicate files: {analysis['total_duplicate_files']}")
        print(f"✓ Wasted space: {format_size(analysis['wasted_space'])}")

        if args.action == 'report':
            report_file = args.report or 'duplicate_report.txt'
            duplicate_manager.create_duplicate_report(duplicates, report_file)
            print(f"\n✓ Report saved to: {report_file}")

        elif args.action == 'remove' or args.action == 'move':
            if args.dry_run:
                print("\n[DRY RUN MODE - No files will be modified]")

            # Interactive mode
            if args.interactive:
                selections = InteractiveMode.interactive_duplicate_removal(duplicates)

                if selections['remove']:
                    if not args.dry_run:
                        confirmed = InteractiveMode.confirm(
                            f"Remove {len(selections['remove'])} files?",
                            default=False
                        )
                        if not confirmed:
                            print("Operation cancelled")
                            db.complete_operation(operation_id, 'cancelled')
                            return 0

                    # Log file operations
                    for file_info in selections['remove']:
                        db.log_file_operation(
                            operation_id,
                            'delete_duplicate',
                            file_info['path'],
                            status='pending'
                        )

                    # Actually remove files
                    for file_info in selections['remove']:
                        if not args.dry_run:
                            try:
                                Path(file_info['path']).unlink()
                                logger.info(f"Removed: {file_info['path']}")
                            except Exception as e:
                                logger.error(f"Failed to remove {file_info['path']}: {e}")

                    print(f"\n✓ Removed {len(selections['remove'])} duplicate files")

            else:
                # Non-interactive mode
                if args.action == 'remove':
                    operations = duplicate_manager.remove_duplicates(duplicates, keep_strategy=args.keep)

                    # Log operations
                    for op in operations:
                        db.log_file_operation(
                            operation_id,
                            op['action'],
                            op['path'],
                            status=op.get('status', 'completed'),
                            file_size=op.get('size'),
                            file_hash=op.get('hash'),
                            can_undo=False  # Delete is not undoable
                        )

                    print(f"\n✓ Removed {len(operations)} duplicate files")

                elif args.action == 'move':
                    if not args.target:
                        print("❌ Error: --target directory required for move action")
                        return 1

                    operations = duplicate_manager.move_duplicates(
                        duplicates, args.target, keep_strategy=args.keep
                    )

                    # Log operations
                    for op in operations:
                        db.log_file_operation(
                            operation_id,
                            op['action'],
                            op['source'],
                            destination_path=op.get('destination'),
                            status=op.get('status', 'completed'),
                            file_size=op.get('size'),
                            file_hash=op.get('hash'),
                            can_undo=True  # Move is undoable
                        )

                    print(f"\n✓ Moved {len(operations)} duplicate files to {args.target}")

        db.complete_operation(operation_id, 'completed')

    except Exception as e:
        logger.error(f"Duplicates command failed: {e}")
        db.complete_operation(operation_id, 'failed')
        if args.verbose:
            raise
        else:
            print(f"\n❌ Error: {e}")
            return 1

    return 0


def cmd_undo(args, db: Database):
    """Execute the undo command."""
    print_header("Undo Operation")

    undo_manager = UndoManager(db)

    if args.list:
        # List undoable operations
        operations = undo_manager.list_undoable()

        if not operations:
            print("No operations available to undo")
            return 0

        print("Undoable operations:")
        for op_str in operations:
            print(f"  {op_str}")

        return 0

    if args.operation_id:
        # Undo specific operation
        try:
            results = undo_manager.undo_operation(args.operation_id, dry_run=args.dry_run)

            if args.dry_run:
                print("[DRY RUN MODE]")

            print(f"\nOperation {results['operation_id']} ({results['operation_type']})")
            print(f"  Timestamp: {results['timestamp']}")
            print(f"  Undone: {len(results['undone'])} operations")
            print(f"  Failed: {len(results['failed'])} operations")

            if results['failed'] and args.verbose:
                print("\nFailed operations:")
                for failed in results['failed']:
                    print(f"  - {failed.get('reason')}")

        except Exception as e:
            print(f"❌ Error: {e}")
            return 1

    return 0


def cmd_config(args, config: Config):
    """Manage configuration."""
    if args.show:
        print_header("Current Configuration")
        print(json.dumps(config.config, indent=2))

    elif args.init:
        output_path = args.output or str(Path.home() / '.fileorganizer' / 'config.yaml')
        config.create_default_config(output_path)
        print(f"✓ Created default configuration: {output_path}")

    return 0


def main():
    """Main entry point for the improved CLI."""
    parser = argparse.ArgumentParser(
        description='Personal File Organization Assistant v2.0',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global options
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bars')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan directory with caching and smart detection')
    scan_parser.add_argument('directory', help='Directory to scan')
    scan_parser.add_argument('--exclude', nargs='+', help='Directories to exclude')
    scan_parser.add_argument('--include-hidden', action='store_true', help='Include hidden files')
    scan_parser.add_argument('--show-duplicates', action='store_true', help='Show duplicate files')
    scan_parser.add_argument('--output', '-o', help='Save results to JSON file')
    scan_parser.add_argument('--no-cache', dest='use_cache', action='store_false', help='Disable caching')
    scan_parser.add_argument('--no-parallel', dest='parallel', action='store_false', help='Disable parallel hashing')
    scan_parser.add_argument('--smart', action='store_true', help='Enable smart detection (EXIF, PDF, etc.)')
    scan_parser.add_argument('--quick', action='store_true', help='Use quick hash for large files')

    # Duplicates command
    dup_parser = subparsers.add_parser('duplicates', help='Find and manage duplicates with interactive mode')
    dup_parser.add_argument('directory', help='Directory to scan')
    dup_parser.add_argument('--action', choices=['report', 'remove', 'move'],
                           default='report', help='Action to perform')
    dup_parser.add_argument('--keep', choices=['newest', 'oldest', 'shortest_path', 'first'],
                           default='newest', help='Which file to keep')
    dup_parser.add_argument('--target', help='Target directory for move action')
    dup_parser.add_argument('--report', help='Report file name')
    dup_parser.add_argument('--exclude', nargs='+', help='Directories to exclude')
    dup_parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')
    dup_parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')

    # Undo command
    undo_parser = subparsers.add_parser('undo', help='Undo previous operations')
    undo_parser.add_argument('--list', action='store_true', help='List undoable operations')
    undo_parser.add_argument('--operation-id', type=int, help='Operation ID to undo')
    undo_parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')

    # Config command
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_parser.add_argument('--show', action='store_true', help='Show current configuration')
    config_parser.add_argument('--init', action='store_true', help='Create default configuration')
    config_parser.add_argument('--output', help='Output path for init')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')

    args = parser.parse_args()

    # Setup logging
    global logger
    setup_logging(log_level=args.log_level, verbose=args.verbose)
    logger = get_logger(__name__)

    # Load configuration
    config = Config(args.config) if args.config else Config()

    # Initialize database
    db = Database()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == 'scan':
            return cmd_scan(args, config, db)
        elif args.command == 'duplicates':
            return cmd_duplicates(args, config, db)
        elif args.command == 'undo':
            return cmd_undo(args, db)
        elif args.command == 'config':
            return cmd_config(args, config)
        elif args.command == 'stats':
            stats = db.get_statistics()
            print_header("Database Statistics")
            for key, value in stats.items():
                print(f"{key}: {value}")
            return 0

    except FileOrganizerError as e:
        print(str(e))
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            raise
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
