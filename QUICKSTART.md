# Quick Start Guide - File Organization Assistant v1.5.1

## Installation

```bash
pip install -e .
```

## Basic Usage

### 1. Scan a Directory

Quick scan of your Downloads folder:

```bash
fileorganizer scan ~/Downloads
```

**Output:**
```
Scanning files: ██████████████████████████████ 100.0% (523/523) ETA: 0s

============================================================
SCAN RESULTS
============================================================
Files found: 523
Total size: 2.47 GB
Scan time: 0.82s

Duplicates found:
  Groups: 12
  Duplicate files: 28
  Wasted space: 145.23 MB
============================================================
```

### 2. Find Duplicate Files

Generate a detailed report of duplicates:

```bash
fileorganizer duplicates ~/Downloads --action report
```

**Output:**
```
Found 12 duplicate groups
Duplicate files: 28
Wasted space: 145.23 MB

✓ Report saved to: duplicate_report.txt
```

### 3. Remove Duplicates (Safely)

**Dry run first** (recommended):

```bash
fileorganizer duplicates ~/Downloads --action remove --dry-run
```

When ready, remove duplicates (keeps newest file):

```bash
fileorganizer duplicates ~/Downloads --action remove
```

Want to keep oldest instead?

```bash
fileorganizer duplicates ~/Downloads --action remove --keep oldest
```

### 4. Move Duplicates to Archive

Move duplicates to a separate folder instead of deleting:

```bash
fileorganizer duplicates ~/Downloads --action move --target ~/Duplicates
```

### 5. Undo Operations

List recent operations:

```bash
fileorganizer undo --list
```

**Output:**
```
============================================================
UNDOABLE OPERATIONS
============================================================

[15] 2025-01-15 14:23:45 - move
  From: /home/user/Downloads/photo.jpg
  To:   /home/user/Duplicates/photo.jpg

[14] 2025-01-15 14:22:10 - move
  From: /home/user/Downloads/doc.pdf
  To:   /home/user/Duplicates/doc.pdf

============================================================
To undo: fileorganizer undo <id>
```

Undo a specific operation:

```bash
fileorganizer undo 15
```

## Advanced Options

### Include Hidden Files

```bash
fileorganizer scan ~/Documents --include-hidden
```

### Exclude Specific Directories

```bash
fileorganizer scan ~/Projects --exclude node_modules __pycache__ .git
```

### Disable Cache (Force Fresh Scan)

```bash
fileorganizer scan ~/Downloads --no-cache
```

### Quiet Mode (No Progress Bar)

```bash
fileorganizer scan ~/Downloads --quiet
```

### Verbose Logging

```bash
fileorganizer scan ~/Downloads --verbose
```

Log files are saved to: `~/.fileorganizer/logs/`

## Common Workflows

### Weekly Downloads Cleanup

```bash
# 1. Scan for duplicates
fileorganizer duplicates ~/Downloads --action report

# 2. Review the report
cat duplicate_report.txt

# 3. Remove duplicates (keeping newest)
fileorganizer duplicates ~/Downloads --action remove --keep newest -y
```

### Before/After Archive

```bash
# 1. Dry run to see what would happen
fileorganizer duplicates ~/Documents --action move --target ~/Archive --dry-run

# 2. Execute the move
fileorganizer duplicates ~/Documents --action move --target ~/Archive

# 3. If you made a mistake, undo it
fileorganizer undo --list
fileorganizer undo <id>
```

### Large Directory Scan

For large directories (10,000+ files), the tool automatically:
- Shows progress bar with ETA
- Uses caching for faster subsequent scans
- Handles errors gracefully
- Logs all operations

```bash
fileorganizer scan /large/directory --verbose
```

**First scan:** ~1-2 seconds per 1,000 files
**Cached scan:** Nearly instant (0.01s)

## Tips

1. **Always dry-run first** when removing or moving files
2. **Check the logs** if something unexpected happens: `~/.fileorganizer/logs/`
3. **Cache is your friend** - second scans are 30-50x faster
4. **Undo is available** for all move operations
5. **Keep strategies:**
   - `newest` (default): Keep the most recently modified file
   - `oldest`: Keep the oldest file
   - `shortest_path`: Keep the file with the shortest path
   - `first`: Keep the first file encountered

## Troubleshooting

### Permission Errors

If you see permission errors, the tool will:
- Log the error
- Continue scanning other files
- Show error count in summary

Check logs: `tail -f ~/.fileorganizer/logs/fileorganizer.log`

### Slow Scans

First scan is always slower. Subsequent scans use cache:

```bash
# First scan: 2.3s
fileorganizer scan ~/large-dir

# Second scan: 0.01s (instant!)
fileorganizer scan ~/large-dir
```

To force fresh scan:

```bash
fileorganizer scan ~/large-dir --no-cache
```

### No Duplicates Found

The tool uses MD5 hashing to detect duplicates. Files are duplicates if:
- They have identical content (byte-for-byte)
- Even if filenames are different

Empty files (0 bytes) are not considered for duplicate detection.

## Getting Help

```bash
fileorganizer --help
fileorganizer scan --help
fileorganizer duplicates --help
fileorganizer undo --help
```

## What's New in v1.5.1

- Production-ready logging system
- Real-time progress indicators with ETA
- Robust error handling with helpful suggestions
- Tested on 10,000+ files
- Intelligent caching (30-50x speedup)
- Undo system for safe file operations
- No external dependencies (except PyYAML)

Enjoy organizing your files!
