#!/usr/bin/env python3
"""
Command-line interface for the File Organization Assistant.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .scanner import FileScanner
from .organizer import FileOrganizer
from .archiver import FileArchiver
from .duplicates import DuplicateManager


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


def cmd_scan(args):
    """Execute the scan command."""
    print_header(f"Scanning Directory: {args.directory}")

    scanner = FileScanner(args.directory, exclude_dirs=args.exclude)
    results = scanner.scan(include_hidden=args.include_hidden)

    print(f"Files scanned: {results['file_count']:,}")
    print(f"Total size: {format_size(results['total_size'])}")
    print(f"Scan completed: {results['scan_date']}")

    # Show file type distribution
    print_section("File Types Distribution")
    by_extension = results['by_extension']
    sorted_extensions = sorted(by_extension.items(), key=lambda x: len(x[1]), reverse=True)

    for ext, files in sorted_extensions[:10]:  # Show top 10
        count = len(files)
        total_size = sum(f['size'] for f in files)
        print(f"  {ext:20s} {count:6,} files  {format_size(total_size):>10s}")

    if len(sorted_extensions) > 10:
        print(f"  ... and {len(sorted_extensions) - 10} more types")

    # Show duplicates if found
    duplicates = results['duplicates']
    if duplicates:
        print_section("Duplicate Files Found")
        duplicate_manager = DuplicateManager()
        dup_analysis = duplicate_manager.analyze_duplicates(duplicates)

        print(f"  Duplicate groups: {dup_analysis['duplicate_groups']}")
        print(f"  Duplicate files: {dup_analysis['total_duplicate_files']}")
        print(f"  Wasted space: {format_size(dup_analysis['wasted_space'])}")

        if args.show_duplicates:
            print("\n  Top duplicate groups:")
            sorted_dups = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)
            for hash_val, files in sorted_dups[:5]:
                print(f"\n    {len(files)} copies ({format_size(files[0]['size'])} each):")
                for file_info in files[:3]:  # Show first 3
                    print(f"      - {file_info['path']}")
                if len(files) > 3:
                    print(f"      ... and {len(files) - 3} more")

    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")


def cmd_duplicates(args):
    """Execute the duplicates command."""
    print_header(f"Finding Duplicates in: {args.directory}")

    scanner = FileScanner(args.directory, exclude_dirs=args.exclude)
    results = scanner.scan()
    duplicates = results['duplicates']

    if not duplicates:
        print("No duplicate files found!")
        return

    duplicate_manager = DuplicateManager(dry_run=args.dry_run)
    analysis = duplicate_manager.analyze_duplicates(duplicates)

    print(f"Duplicate groups: {analysis['duplicate_groups']}")
    print(f"Duplicate files: {analysis['total_duplicate_files']}")
    print(f"Wasted space: {format_size(analysis['wasted_space'])}")

    if args.action == 'report':
        report_file = args.report or 'duplicate_report.txt'
        duplicate_manager.create_duplicate_report(duplicates, report_file)
        print(f"\nReport saved to: {report_file}")

    elif args.action == 'remove':
        if args.dry_run:
            print("\n[DRY RUN MODE - No files will be deleted]")

        operations = duplicate_manager.remove_duplicates(duplicates, keep_strategy=args.keep)
        print(f"\nRemoved {len(operations)} duplicate files")

        if args.verbose:
            for op in operations[:10]:  # Show first 10
                print(f"  {op['status'].upper()}: {op['path']}")
            if len(operations) > 10:
                print(f"  ... and {len(operations) - 10} more")

    elif args.action == 'move':
        if not args.target:
            print("Error: --target directory required for move action")
            return

        if args.dry_run:
            print("\n[DRY RUN MODE - No files will be moved]")

        operations = duplicate_manager.move_duplicates(
            duplicates, args.target, keep_strategy=args.keep
        )
        print(f"\nMoved {len(operations)} duplicate files to {args.target}")


def cmd_organize(args):
    """Execute the organize command."""
    print_header(f"Organizing Files in: {args.directory}")

    if args.dry_run:
        print("[DRY RUN MODE - No files will be modified]\n")

    organizer = FileOrganizer(dry_run=args.dry_run)

    if args.mode == 'type':
        target = args.target or f"{args.directory}_organized"
        operations = organizer.organize_by_type(args.directory, target)
        print(f"Organized {len(operations)} files by type into {target}")

        if args.verbose:
            # Show summary by category
            from collections import Counter
            categories = Counter(op['category'] for op in operations)
            print("\nFiles organized by category:")
            for category, count in categories.most_common():
                print(f"  {category:20s} {count:6,} files")

    elif args.mode == 'date':
        target = args.target or f"{args.directory}_by_date"
        date_format = args.date_format or "%Y/%m"
        operations = organizer.organize_by_date(args.directory, target, date_format)
        print(f"Organized {len(operations)} files by date into {target}")


def cmd_rename(args):
    """Execute the rename command."""
    print_header(f"Renaming Files in: {args.directory}")

    if args.dry_run:
        print("[DRY RUN MODE - No files will be renamed]\n")

    organizer = FileOrganizer(dry_run=args.dry_run)

    if args.template:
        operations = organizer.smart_rename(args.directory, args.template)
    else:
        operations = organizer.rename_files(
            args.directory, args.pattern, args.replacement, use_regex=args.regex
        )

    print(f"Renamed {len(operations)} files")

    if args.verbose and operations:
        print("\nExamples:")
        for op in operations[:10]:
            print(f"  {op['old_name']} -> {op['new_name']}")
        if len(operations) > 10:
            print(f"  ... and {len(operations) - 10} more")


def cmd_archive(args):
    """Execute the archive command."""
    print_header(f"Archiving Files in: {args.directory}")

    if args.dry_run:
        print("[DRY RUN MODE - No files will be archived]\n")

    archiver = FileArchiver(dry_run=args.dry_run)

    if args.mode == 'old':
        results = archiver.archive_old_files(
            args.directory,
            args.target,
            days_threshold=args.days,
            compress=not args.no_compress
        )
        print(f"Archived {results['files_archived']} old files")
        print(f"Total size: {format_size(results['total_size'])}")
        if results['archive_path']:
            print(f"Archive location: {results['archive_path']}")

    elif args.mode == 'extension':
        if not args.extensions:
            print("Error: --extensions required for extension mode")
            return

        extensions = [ext if ext.startswith('.') else f'.{ext}'
                     for ext in args.extensions]

        results = archiver.archive_by_extension(
            args.directory,
            args.target,
            extensions,
            compress=not args.no_compress
        )
        print(f"Archived {results['files_archived']} files")
        print(f"Total size: {format_size(results['total_size'])}")
        if results['archive_path']:
            print(f"Archive location: {results['archive_path']}")

    # Cleanup empty directories if requested
    if args.cleanup_empty:
        removed_dirs = archiver.cleanup_empty_dirs(args.directory)
        if removed_dirs:
            print(f"\nRemoved {len(removed_dirs)} empty directories")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Personal File Organization Assistant',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan a directory
  fileorganizer scan ~/Downloads

  # Find and remove duplicates
  fileorganizer duplicates ~/Documents --action remove --keep newest

  # Organize files by type
  fileorganizer organize ~/Downloads --mode type --target ~/Downloads_Organized

  # Archive old files
  fileorganizer archive ~/Documents --mode old --days 365 --target ~/Archive

  # Rename files with a template
  fileorganizer rename ~/Photos --template "{date}_{counter}"
        """
    )

    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan directory and analyze files')
    scan_parser.add_argument('directory', help='Directory to scan')
    scan_parser.add_argument('--exclude', nargs='+', help='Directories to exclude')
    scan_parser.add_argument('--include-hidden', action='store_true', help='Include hidden files')
    scan_parser.add_argument('--show-duplicates', action='store_true', help='Show duplicate files')
    scan_parser.add_argument('--output', '-o', help='Save results to JSON file')
    scan_parser.set_defaults(func=cmd_scan)

    # Duplicates command
    dup_parser = subparsers.add_parser('duplicates', help='Find and manage duplicate files')
    dup_parser.add_argument('directory', help='Directory to scan')
    dup_parser.add_argument('--action', choices=['report', 'remove', 'move'],
                           default='report', help='Action to perform')
    dup_parser.add_argument('--keep', choices=['newest', 'oldest', 'shortest_path', 'first'],
                           default='newest', help='Which file to keep')
    dup_parser.add_argument('--target', help='Target directory for move action')
    dup_parser.add_argument('--report', help='Report file name')
    dup_parser.add_argument('--exclude', nargs='+', help='Directories to exclude')
    dup_parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')
    dup_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    dup_parser.set_defaults(func=cmd_duplicates)

    # Organize command
    org_parser = subparsers.add_parser('organize', help='Organize files into structured folders')
    org_parser.add_argument('directory', help='Directory to organize')
    org_parser.add_argument('--mode', choices=['type', 'date'], default='type',
                           help='Organization mode')
    org_parser.add_argument('--target', help='Target directory for organized files')
    org_parser.add_argument('--date-format', help='Date format for date mode (e.g., %%Y/%%m)')
    org_parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')
    org_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    org_parser.set_defaults(func=cmd_organize)

    # Rename command
    ren_parser = subparsers.add_parser('rename', help='Batch rename files')
    ren_parser.add_argument('directory', help='Directory containing files to rename')
    ren_parser.add_argument('--pattern', help='Pattern to match')
    ren_parser.add_argument('--replacement', help='Replacement string')
    ren_parser.add_argument('--template', help='Template for smart rename (e.g., {date}_{name})')
    ren_parser.add_argument('--regex', action='store_true', help='Use regex matching')
    ren_parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')
    ren_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    ren_parser.set_defaults(func=cmd_rename)

    # Archive command
    arc_parser = subparsers.add_parser('archive', help='Archive old or specific files')
    arc_parser.add_argument('directory', help='Directory to archive files from')
    arc_parser.add_argument('--mode', choices=['old', 'extension'], default='old',
                           help='Archive mode')
    arc_parser.add_argument('--target', required=True, help='Archive target directory')
    arc_parser.add_argument('--days', type=int, default=365,
                           help='Days threshold for old mode')
    arc_parser.add_argument('--extensions', nargs='+', help='File extensions for extension mode')
    arc_parser.add_argument('--no-compress', action='store_true', help='Do not compress archive')
    arc_parser.add_argument('--cleanup-empty', action='store_true', help='Remove empty directories')
    arc_parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')
    arc_parser.set_defaults(func=cmd_archive)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        args.func(args)
        return 0
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
