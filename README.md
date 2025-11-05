# Personal File Organization Assistant

A comprehensive command-line tool that helps users organize their cluttered computer files and folders. This tool addresses the significant challenge of digital clutter by providing automated file scanning, duplicate detection, intelligent organization, archiving, and batch renaming capabilities.

## Features

### 1. File Scanning & Analysis
- Recursively scan directories and collect file metadata
- Analyze file type distribution
- Calculate total storage usage
- Export scan results to JSON for further analysis

### 2. Duplicate Detection
- Identify duplicate files using MD5 hash comparison
- Calculate wasted storage space
- Multiple strategies for keeping files (newest, oldest, shortest path, first)
- Generate detailed duplicate reports
- Remove or move duplicates safely

### 3. Intelligent Organization
- **Organize by Type**: Automatically categorize files into folders (Documents, Images, Videos, etc.)
- **Organize by Date**: Group files by modification date with customizable date formats
- Configurable file categories
- Handles name conflicts automatically
- Preserves file metadata

### 4. Archiving
- Archive old files based on last access date
- Archive specific file types by extension
- Compress archives into ZIP files
- Clean up empty directories after archiving
- Safe operations with dry-run mode

### 5. Batch Renaming
- Pattern-based renaming with search and replace
- Regular expression support
- Smart template-based renaming with variables:
  - `{date}` - Modification date
  - `{time}` - Modification time
  - `{name}` - Original filename
  - `{ext}` - File extension
  - `{counter}` - Sequential counter

### 6. Safety Features
- Dry-run mode for all operations
- Automatic conflict resolution
- Excluded directories (`.git`, `node_modules`, etc.)
- Verbose output for transparency

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/Data-Organization-File-Management-Tools.git
cd Data-Organization-File-Management-Tools

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Using pip (after publishing)

```bash
pip install fileorganizer
```

## Quick Start

### Scan a Directory

```bash
# Basic scan
fileorganizer scan ~/Downloads

# Scan with duplicate detection
fileorganizer scan ~/Downloads --show-duplicates

# Save results to JSON
fileorganizer scan ~/Downloads --output scan_results.json
```

### Find and Manage Duplicates

```bash
# Generate a duplicate report
fileorganizer duplicates ~/Documents --action report

# Remove duplicates (keep newest)
fileorganizer duplicates ~/Documents --action remove --keep newest

# Move duplicates to a folder
fileorganizer duplicates ~/Documents --action move --target ~/Duplicates

# Dry run to preview changes
fileorganizer duplicates ~/Documents --action remove --dry-run
```

### Organize Files

```bash
# Organize by file type
fileorganizer organize ~/Downloads --mode type --target ~/Downloads_Organized

# Organize by date (Year/Month)
fileorganizer organize ~/Photos --mode date --date-format "%Y/%m"

# Preview changes with dry run
fileorganizer organize ~/Downloads --mode type --dry-run --verbose
```

### Archive Old Files

```bash
# Archive files older than 1 year
fileorganizer archive ~/Documents --mode old --target ~/Archive --days 365

# Archive specific file types
fileorganizer archive ~/Downloads --mode extension --extensions tmp log cache --target ~/Archive

# Archive and compress
fileorganizer archive ~/Documents --mode old --target ~/Archive --days 365

# Archive without compression
fileorganizer archive ~/Documents --mode old --target ~/Archive --no-compress
```

### Batch Rename Files

```bash
# Simple pattern replacement
fileorganizer rename ~/Photos --pattern "IMG_" --replacement "Photo_"

# Using regex
fileorganizer rename ~/Documents --pattern "\\d{8}" --replacement "DATE" --regex

# Smart template-based renaming
fileorganizer rename ~/Photos --template "{date}_{counter}"
fileorganizer rename ~/Documents --template "{date}_{name}"

# Preview changes
fileorganizer rename ~/Photos --template "{date}_{counter}" --dry-run --verbose
```

## Use Cases

### Example 1: Organizing Downloads Folder

```bash
# Step 1: Scan and analyze
fileorganizer scan ~/Downloads --show-duplicates

# Step 2: Find and remove duplicates
fileorganizer duplicates ~/Downloads --action remove --keep newest

# Step 3: Organize by type
fileorganizer organize ~/Downloads --mode type --target ~/Downloads_Organized

# Step 4: Archive old files
fileorganizer archive ~/Downloads_Organized --mode old --target ~/Archive --days 180
```

### Example 2: Sorting Invoices by Date and Vendor

```bash
# First, rename invoices with consistent naming
fileorganizer rename ~/Invoices --template "{date}_{name}"

# Then organize by date
fileorganizer organize ~/Invoices --mode date --date-format "%Y/%m"
```

### Example 3: Cleaning Up Project Folders

```bash
# Remove temporary files
fileorganizer archive ~/Projects --mode extension --extensions tmp log cache bak --target ~/Trash

# Find duplicate code files
fileorganizer duplicates ~/Projects --action report --report project_duplicates.txt

# Clean up empty directories
fileorganizer archive ~/Projects --mode old --target ~/Archive --cleanup-empty --days 730
```

### Example 4: Photo Library Organization

```bash
# Organize photos by date taken
fileorganizer organize ~/Photos --mode date --date-format "%Y/%m/%d"

# Rename with date prefix
fileorganizer rename ~/Photos --template "{date}_{counter}"

# Find duplicate photos
fileorganizer duplicates ~/Photos --action move --target ~/Photos/Duplicates
```

## Configuration

You can create a configuration file to customize default behavior:

### Example Configuration (YAML)

```yaml
# config.yaml
exclude_dirs:
  - .git
  - node_modules
  - __pycache__
  - .venv

exclude_extensions:
  - .tmp
  - .cache

duplicate_detection:
  enabled: true
  keep_strategy: newest

organization:
  mode: type
  custom_categories:
    Projects:
      - .xcodeproj
      - .project

archiving:
  old_files_threshold_days: 365
  compress: true

naming:
  template: "{date}_{name}"
  replace_spaces: true
  space_replacement: "_"
```

See `examples/config.yaml` for a complete configuration example.

## Command Reference

### Global Options

- `--version` - Show version information
- `--help` - Show help message

### Scan Command

```bash
fileorganizer scan <directory> [options]
```

**Options:**
- `--exclude <dirs>` - Directories to exclude
- `--include-hidden` - Include hidden files
- `--show-duplicates` - Show duplicate file information
- `--output <file>` - Save results to JSON file

### Duplicates Command

```bash
fileorganizer duplicates <directory> [options]
```

**Options:**
- `--action <action>` - Action to perform: report, remove, move
- `--keep <strategy>` - Which file to keep: newest, oldest, shortest_path, first
- `--target <dir>` - Target directory for move action
- `--report <file>` - Report file name
- `--exclude <dirs>` - Directories to exclude
- `--dry-run` - Simulate without making changes
- `--verbose` - Verbose output

### Organize Command

```bash
fileorganizer organize <directory> [options]
```

**Options:**
- `--mode <mode>` - Organization mode: type, date
- `--target <dir>` - Target directory for organized files
- `--date-format <format>` - Date format for date mode (e.g., %Y/%m)
- `--dry-run` - Simulate without making changes
- `--verbose` - Verbose output

### Rename Command

```bash
fileorganizer rename <directory> [options]
```

**Options:**
- `--pattern <pattern>` - Pattern to match in filenames
- `--replacement <text>` - Replacement string
- `--template <template>` - Template for smart rename
- `--regex` - Use regex matching
- `--dry-run` - Simulate without making changes
- `--verbose` - Verbose output

### Archive Command

```bash
fileorganizer archive <directory> [options]
```

**Options:**
- `--mode <mode>` - Archive mode: old, extension
- `--target <dir>` - Archive target directory (required)
- `--days <number>` - Days threshold for old mode (default: 365)
- `--extensions <exts>` - File extensions for extension mode
- `--no-compress` - Do not compress archive
- `--cleanup-empty` - Remove empty directories
- `--dry-run` - Simulate without making changes

## File Categories

The tool automatically categorizes files into the following types:

- **Documents**: PDF, DOC, DOCX, TXT, RTF, ODT, TEX
- **Spreadsheets**: XLS, XLSX, CSV, ODS
- **Presentations**: PPT, PPTX, KEY, ODP
- **Images**: JPG, JPEG, PNG, GIF, BMP, SVG, ICO, WEBP, TIFF
- **Videos**: MP4, AVI, MKV, MOV, WMV, FLV, WEBM
- **Audio**: MP3, WAV, FLAC, AAC, OGG, M4A, WMA
- **Archives**: ZIP, RAR, 7Z, TAR, GZ, BZ2, XZ
- **Code**: PY, JS, JAVA, CPP, C, H, CS, PHP, RB, GO, RS, SWIFT
- **Web**: HTML, CSS, SCSS, SASS, LESS
- **Data**: JSON, XML, YAML, YML, SQL, DB, SQLITE
- **Executables**: EXE, MSI, APP, DEB, RPM, DMG
- **Fonts**: TTF, OTF, WOFF, WOFF2
- **Other**: Everything else

You can customize categories in the configuration file.

## Safety and Best Practices

1. **Always use dry-run first**: Test operations with `--dry-run` before executing
2. **Backup important data**: Make backups before running destructive operations
3. **Review duplicate reports**: Check duplicate reports before removing files
4. **Start small**: Test on a small directory first
5. **Use verbose mode**: Enable `--verbose` to see what's happening
6. **Exclude sensitive directories**: Add system and application directories to exclude list

## Examples Directory

The `examples/` directory contains:
- `config.yaml` - Example configuration file
- `organize_downloads.sh` - Script for organizing downloads folder
- Additional use case scripts

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

MIT License - See LICENSE file for details

## Troubleshooting

### Permission Errors

If you encounter permission errors, ensure you have read/write access to the directories:

```bash
# Check permissions
ls -la /path/to/directory

# Run with appropriate permissions or adjust directory ownership
```

### Large Directories

For very large directories, scanning may take time. You can:
- Exclude unnecessary subdirectories with `--exclude`
- Process subdirectories separately
- Save scan results to JSON and analyze offline

### Duplicate Detection Accuracy

The tool uses MD5 hashing for duplicate detection. While reliable for most use cases:
- Empty files are skipped
- Files with different names but identical content are detected
- Symbolic links are treated as regular files

## FAQ

**Q: Will this tool delete my files without confirmation?**
A: Only if you don't use `--dry-run`. Always test operations with dry-run mode first.

**Q: Can I undo operations?**
A: File moves can be reversed, but deletions cannot. Use `--action move` instead of `remove` for duplicates to be safe.

**Q: How does duplicate detection work?**
A: Files are compared using MD5 hash. Files with identical hashes are considered duplicates.

**Q: Can I customize file categories?**
A: Yes, use a configuration file with custom_categories to add or modify categories.

**Q: Is it safe to run on my entire home directory?**
A: While safe with dry-run, it's better to organize specific folders (Downloads, Documents, etc.) rather than your entire home directory.

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the examples directory for common use cases
- Review this README for detailed command reference

---

**Made with ❤️ to help organize digital clutter**
