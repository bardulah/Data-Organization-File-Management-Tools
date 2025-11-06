# Migration Guide: v1.0 to v2.0

This guide helps you migrate from File Organization Assistant v1.0 to v2.0.

## Overview of Changes

Version 2.0 is a major upgrade with significant new features and some breaking changes. The core functionality remains the same, but the implementation has been greatly improved.

## What's New in v2.0

### 1. Database and History Tracking
V2 now uses SQLite to track all operations, enabling undo/redo functionality.

**Location**: `~/.fileorganizer/fileorganizer.db`

### 2. Improved Scanner
The scanner now supports:
- Incremental scanning with caching
- Parallel hash calculation
- Smart metadata extraction (EXIF, PDF)
- Progress bars

### 3. Undo System
All operations are tracked and can be undone (except deletions).

### 4. Plugin System
Organization logic is now plugin-based for extensibility.

### 5. Web Interface
New web-based UI for remote management.

## Breaking Changes

### CLI Commands

**V1 Command Structure:**
```bash
python -m fileorganizer.cli scan /path
```

**V2 Command Structure:**
```bash
python -m fileorganizer.cli_v2 scan /path
```

Or after updating entry point:
```bash
fileorganizer scan /path
```

### Configuration

**V1**: No configuration file support

**V2**: YAML/JSON configuration files supported

**Migration**: Create a config file:
```bash
python -m fileorganizer.cli_v2 config --init
```

Edit `~/.fileorganizer/config.yaml` to customize settings.

### Scanner Import

**V1:**
```python
from fileorganizer.scanner import FileScanner
```

**V2:**
```python
from fileorganizer.core.scanner_v2 import ScannerV2
```

### Hashing

**V1**: MD5 hashing
**V2**: SHA256 hashing (more secure)

**Impact**: Cache from v1 is not compatible with v2. First scan with v2 will rebuild cache.

## Step-by-Step Migration

### 1. Backup Your Data

Before upgrading, backup any important data:

```bash
# Backup your files
cp -r /path/to/organize /path/to/organize.backup
```

### 2. Install V2

```bash
cd Data-Organization-File-Management-Tools
git pull
pip install -r requirements.txt --upgrade
pip install -e .
```

### 3. Initialize Configuration

Create default configuration:

```bash
fileorganizer config --init
```

Review and customize `~/.fileorganizer/config.yaml`

### 4. Test with Dry Run

Test the new version with dry-run mode:

```bash
fileorganizer scan ~/Downloads
fileorganizer duplicates ~/Downloads --action report
```

### 5. Migrate Scripts

If you have custom scripts using v1, update them:

**Before (v1):**
```python
from fileorganizer.scanner import FileScanner

scanner = FileScanner('/path')
results = scanner.scan()
```

**After (v2):**
```python
from fileorganizer.core.scanner_v2 import ScannerV2
from fileorganizer.database import Database

db = Database()
scanner = ScannerV2('/path', use_cache=True, parallel_hashing=True)
results = scanner.scan()
```

## New Features to Explore

### 1. Undo Operations

```bash
# List undoable operations
fileorganizer undo --list

# Undo a specific operation
fileorganizer undo --operation-id 123
```

### 2. Smart Scanning

```bash
# Enable smart detection (EXIF, PDF metadata)
fileorganizer scan ~/Photos --smart
```

### 3. Interactive Mode

```bash
# Interactive duplicate removal
fileorganizer duplicates ~/Documents --action remove --interactive
```

### 4. Web Interface

```bash
# Start web server
python -m fileorganizer.web_api
```

Then open http://localhost:5000 in your browser.

### 5. Plugins

Create custom plugins in `~/.fileorganizer/plugins/`:

```python
# ~/.fileorganizer/plugins/custom.py
from fileorganizer.plugins.base import Plugin
from pathlib import Path

class MyCustomPlugin(Plugin):
    def should_process(self, file_path: Path, metadata: dict) -> bool:
        # Your logic here
        return file_path.suffix == '.custom'

    def get_target_path(self, file_path: Path, metadata: dict, target_root: Path) -> Path:
        # Your organization logic
        return target_root / 'CustomFiles' / file_path.name
```

### 6. Configuration

Customize behavior in `~/.fileorganizer/config.yaml`:

```yaml
exclude_dirs:
  - .git
  - node_modules
  - custom_exclude

duplicate_detection:
  keep_strategy: newest

organization:
  mode: type

archiving:
  old_files_threshold_days: 180
  compress: true
```

## API Changes

### Scanner API

**V1:**
```python
scanner = FileScanner(root_path, exclude_dirs=['node_modules'])
results = scanner.scan(include_hidden=False)
```

**V2:**
```python
scanner = ScannerV2(
    root_path,
    exclude_dirs=['node_modules'],
    use_cache=True,                # NEW
    parallel_hashing=True,         # NEW
    smart_detection=False,         # NEW
    show_progress=True             # NEW
)
results = scanner.scan(
    include_hidden=False,
    quick_scan=False,              # NEW
    update_cache=True              # NEW
)
```

### Hashing API

**V1:**
```python
from fileorganizer.scanner import FileScanner
scanner = FileScanner('/path')
hash_val = scanner.calculate_hash(file_path)
```

**V2:**
```python
from fileorganizer.utils.hashing import calculate_hash, smart_hash

# Full hash (SHA256)
hash_val = calculate_hash(file_path, algorithm='sha256')

# Smart hash (quick for large files)
hash_val, is_quick = smart_hash(file_path, threshold_mb=100)
```

## Performance Comparison

### V1 Performance
- Scan 10,000 files: ~60 seconds
- No caching
- Sequential hashing

### V2 Performance
- First scan of 10,000 files: ~30 seconds (parallel hashing)
- Subsequent scans: ~5 seconds (with cache)
- Smart detection: +10-20% time

## Troubleshooting

### Cache Issues

If experiencing cache issues:

```bash
# Clear cache
rm ~/.fileorganizer/fileorganizer.db
```

### Import Errors

If getting import errors:

```bash
# Reinstall
pip uninstall fileorganizer
pip install -e .
```

### Permission Errors

V2 has better permission handling, but if issues persist:

```bash
# Check permissions
ls -la ~/.fileorganizer/

# Fix permissions
chmod -R u+rw ~/.fileorganizer/
```

## Compatibility Matrix

| Feature | V1 | V2 | Notes |
|---------|----|----|-------|
| Basic scanning | ✓ | ✓ | V2 is faster |
| Duplicate detection | ✓ | ✓ | Same functionality |
| File organization | ✓ | ✓ | V2 adds plugins |
| Batch renaming | ✓ | ✓ | Same |
| Archiving | ✓ | ✓ | Same |
| Configuration | ✗ | ✓ | NEW in V2 |
| Undo/Redo | ✗ | ✓ | NEW in V2 |
| Smart detection | ✗ | ✓ | NEW in V2 |
| Plugin system | ✗ | ✓ | NEW in V2 |
| Web interface | ✗ | ✓ | NEW in V2 |
| Database tracking | ✗ | ✓ | NEW in V2 |
| Progress bars | ✗ | ✓ | NEW in V2 |
| Parallel processing | ✗ | ✓ | NEW in V2 |

## Getting Help

If you encounter issues during migration:

1. Check the logs: `~/.fileorganizer/logs/`
2. Run with verbose mode: `fileorganizer scan /path --verbose`
3. Open an issue on GitHub
4. Check the updated README.md

## Rollback to V1

If you need to rollback:

```bash
git checkout v1.0.0
pip install -r requirements.txt
pip install -e .
```

Note: V2 database and cache will remain but won't affect V1.

## Recommended Migration Path

For production environments:

1. **Week 1**: Test v2 in a development environment
2. **Week 2**: Run v2 in parallel with v1
3. **Week 3**: Migrate scripts and workflows
4. **Week 4**: Full migration to v2

For personal use:

1. Backup your data
2. Install v2
3. Test with `--dry-run`
4. Start using v2

## Conclusion

Version 2.0 brings significant improvements in performance, functionality, and user experience. While there are some breaking changes, the core functionality remains intuitive and familiar.

The new features like undo, smart detection, and plugin system make v2 much more powerful and flexible than v1.

Happy organizing! 🗂️
