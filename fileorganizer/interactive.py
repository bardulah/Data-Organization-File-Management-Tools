"""
Interactive mode for user confirmations and selections.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class InteractiveMode:
    """Provides interactive prompts for user decisions."""

    @staticmethod
    def confirm(message: str, default: bool = True) -> bool:
        """
        Ask user for yes/no confirmation.

        Args:
            message: Question to ask
            default: Default answer if user just presses Enter

        Returns:
            True if user confirmed, False otherwise
        """
        suffix = " [Y/n]: " if default else " [y/N]: "
        prompt = message + suffix

        try:
            response = input(prompt).strip().lower()

            if not response:
                return default

            return response in ['y', 'yes']

        except (KeyboardInterrupt, EOFError):
            print()  # New line after Ctrl+C
            return False

    @staticmethod
    def choose(message: str, options: List[str], default: int = 0) -> int:
        """
        Let user choose from a list of options.

        Args:
            message: Question to ask
            options: List of option strings
            default: Default option index

        Returns:
            Index of chosen option
        """
        print(f"\n{message}")
        for i, option in enumerate(options, 1):
            marker = "*" if i-1 == default else " "
            print(f"  {marker} {i}. {option}")

        print(f"\nEnter choice (1-{len(options)}) [default={default+1}]: ", end='')

        try:
            response = input().strip()

            if not response:
                return default

            choice = int(response) - 1

            if 0 <= choice < len(options):
                return choice
            else:
                print(f"Invalid choice, using default: {default+1}")
                return default

        except ValueError:
            print(f"Invalid input, using default: {default+1}")
            return default
        except (KeyboardInterrupt, EOFError):
            print()
            return default

    @staticmethod
    def select_from_list(
        items: List[Dict],
        display_key: str,
        message: str = "Select items:",
        allow_multiple: bool = True
    ) -> List[int]:
        """
        Let user select items from a list.

        Args:
            items: List of items (dictionaries)
            display_key: Key to use for display
            message: Message to show
            allow_multiple: Allow selecting multiple items

        Returns:
            List of selected indices
        """
        print(f"\n{message}")
        print("=" * 60)

        for i, item in enumerate(items, 1):
            display = item.get(display_key, str(item))
            print(f"{i:3d}. {display}")

        print("=" * 60)

        if allow_multiple:
            print("Enter numbers separated by spaces (e.g., '1 3 5' or '1-5')")
            print("Enter 'all' to select all, or 'none' to skip: ", end='')
        else:
            print(f"Enter number (1-{len(items)}): ", end='')

        try:
            response = input().strip().lower()

            if not response or response == 'none':
                return []

            if response == 'all':
                return list(range(len(items)))

            # Parse selection
            selected = set()

            for part in response.split():
                if '-' in part:
                    # Range like "1-5"
                    try:
                        start, end = part.split('-')
                        start_idx = int(start) - 1
                        end_idx = int(end) - 1
                        selected.update(range(start_idx, end_idx + 1))
                    except ValueError:
                        logger.warning(f"Invalid range: {part}")
                else:
                    # Single number
                    try:
                        idx = int(part) - 1
                        selected.add(idx)
                    except ValueError:
                        logger.warning(f"Invalid number: {part}")

            # Filter valid indices
            valid = [i for i in selected if 0 <= i < len(items)]

            return sorted(valid)

        except (KeyboardInterrupt, EOFError):
            print()
            return []

    @staticmethod
    def input_text(message: str, default: str = "") -> str:
        """
        Get text input from user.

        Args:
            message: Prompt message
            default: Default value

        Returns:
            User input or default
        """
        default_text = f" [{default}]" if default else ""
        prompt = f"{message}{default_text}: "

        try:
            response = input(prompt).strip()
            return response if response else default

        except (KeyboardInterrupt, EOFError):
            print()
            return default

    @staticmethod
    def input_path(message: str, must_exist: bool = False) -> Optional[Path]:
        """
        Get path input from user with validation.

        Args:
            message: Prompt message
            must_exist: Whether path must exist

        Returns:
            Path object or None
        """
        while True:
            response = InteractiveMode.input_text(message)

            if not response:
                return None

            path = Path(response).expanduser()

            if must_exist and not path.exists():
                print(f"  ❌ Path does not exist: {path}")
                if not InteractiveMode.confirm("Try again?", default=True):
                    return None
                continue

            return path

    @staticmethod
    def show_preview(operations: List[Dict], limit: int = 10):
        """
        Show preview of operations to be performed.

        Args:
            operations: List of operation dictionaries
            limit: Maximum number to show
        """
        print(f"\nPreview of operations ({len(operations)} total):")
        print("=" * 80)

        for i, op in enumerate(operations[:limit], 1):
            action = op.get('action', 'operation')
            source = op.get('source', op.get('path', ''))
            dest = op.get('destination', op.get('target', ''))

            if dest:
                print(f"{i:3d}. {action}: {Path(source).name}")
                print(f"     {source}")
                print(f"  -> {dest}")
            else:
                print(f"{i:3d}. {action}: {source}")

        if len(operations) > limit:
            print(f"  ... and {len(operations) - limit} more operations")

        print("=" * 80)

    @staticmethod
    def review_and_confirm(
        operations: List[Dict],
        preview_limit: int = 10
    ) -> bool:
        """
        Show preview and ask for confirmation.

        Args:
            operations: List of operations
            preview_limit: Number of operations to preview

        Returns:
            True if user confirms
        """
        InteractiveMode.show_preview(operations, preview_limit)

        return InteractiveMode.confirm(
            f"\nProceed with {len(operations)} operations?",
            default=False
        )

    @staticmethod
    def interactive_duplicate_removal(duplicates: Dict) -> Dict:
        """
        Interactively choose which duplicates to remove.

        Args:
            duplicates: Dictionary of duplicate file groups

        Returns:
            Dictionary with user selections
        """
        print(f"\nFound {len(duplicates)} duplicate groups")

        selections = {
            'remove': [],
            'keep': [],
            'skip': []
        }

        for i, (hash_val, files) in enumerate(duplicates.items(), 1):
            print(f"\n{'='*80}")
            print(f"Duplicate Group {i}/{len(duplicates)}")
            print(f"{'='*80}")
            print(f"Files: {len(files)}")
            print(f"Size: {files[0]['size']:,} bytes each")
            print(f"Wasted space: {files[0]['size'] * (len(files) - 1):,} bytes")
            print()

            for j, file_info in enumerate(files, 1):
                print(f"  {j}. {file_info['path']}")
                print(f"     Modified: {file_info['modified']}")

            print()
            action = InteractiveMode.choose(
                "What would you like to do?",
                [
                    "Keep newest, remove others",
                    "Keep oldest, remove others",
                    "Select which to keep manually",
                    "Skip this group"
                ],
                default=0
            )

            if action == 0:  # Keep newest
                sorted_files = sorted(files, key=lambda x: x['modified'], reverse=True)
                selections['keep'].append(sorted_files[0])
                selections['remove'].extend(sorted_files[1:])

            elif action == 1:  # Keep oldest
                sorted_files = sorted(files, key=lambda x: x['modified'])
                selections['keep'].append(sorted_files[0])
                selections['remove'].extend(sorted_files[1:])

            elif action == 2:  # Manual selection
                keep_indices = InteractiveMode.select_from_list(
                    files,
                    'path',
                    "Select file(s) to KEEP:",
                    allow_multiple=False
                )

                if keep_indices:
                    keep_idx = keep_indices[0]
                    selections['keep'].append(files[keep_idx])
                    selections['remove'].extend(
                        [f for i, f in enumerate(files) if i != keep_idx]
                    )
                else:
                    selections['skip'].extend(files)

            else:  # Skip
                selections['skip'].extend(files)

        return selections

    @staticmethod
    def show_progress_summary(results: Dict):
        """
        Show summary of completed operations.

        Args:
            results: Results dictionary from operations
        """
        print("\n" + "="*80)
        print("OPERATION SUMMARY")
        print("="*80)

        if 'succeeded' in results:
            print(f"✓ Succeeded: {len(results['succeeded'])}")

        if 'failed' in results:
            print(f"✗ Failed: {len(results['failed'])}")
            if results['failed'] and InteractiveMode.confirm("Show failed operations?"):
                for failure in results['failed'][:10]:
                    print(f"  - {failure.get('path', 'unknown')}")
                    print(f"    Reason: {failure.get('reason', 'unknown')}")

        if 'undone' in results:
            print(f"↶ Undone: {len(results['undone'])}")

        if 'skipped' in results:
            print(f"⊘ Skipped: {len(results['skipped'])}")

        print("="*80)
