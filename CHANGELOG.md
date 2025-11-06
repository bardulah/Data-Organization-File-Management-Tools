# Changelog

## Version 2.0.0 - Major Update (2024)

### 🎉 Major New Features

#### Core Infrastructure
- **Database System**: SQLite-based operation tracking and history
- **Undo/Redo System**: Full transaction support with rollback capability
- **Improved Logging**: Comprehensive logging with file and console handlers
- **Error Handling**: Better error messages with helpful suggestions

#### Performance Improvements
- **Parallel Hashing**: Multi-threaded file hashing for faster scans
- **Smart Hashing**: Quick hash for large files, full hash for small files
- **Incremental Scanning**: Cache-based scanning to avoid re-scanning unchanged files
- **Progress Bars**: Real-time progress feedback with tqdm

#### Smart Detection
- **EXIF Extraction**: Read photo metadata (date taken, camera info)
- **PDF Parsing**: Extract PDF metadata and text content
- **Content Analysis**: Detect file types by content, not just extension
- **Invoice Detection**: Automatically extract invoice information

#### Plugin System
- **Extensible Architecture**: Plugin-based organization rules
- **Built-in Plugins**: Invoice, Photo, Document, and Project organizers
- **Custom Plugins**: Load custom plugins from ~/.fileorganizer/plugins

#### Interactive Mode
- **User Confirmations**: Interactive prompts for operations
- **Selective Operations**: Choose which files to process
- **Preview Mode**: Review operations before execution

#### Web Interface
- **REST API**: Flask-based web API for remote management
- **Web UI**: Modern web interface for file organization
- **Real-time Stats**: Dashboard with database statistics

#### Configuration
- **Config Integration**: YAML/JSON configuration support
- **Default Settings**: Customizable defaults for all operations
- **Plugin Configuration**: Configure plugin behavior

### 🔧 Improvements

#### Scanner (scanner_v2.py)
- Cache support for incremental scanning
- Parallel hash calculation
- Smart metadata extraction
- Progress bar integration
- 10-50x faster on subsequent scans

#### Hashing (utils/hashing.py)
- SHA256 instead of MD5 (more secure)
- Quick hash for large files
- Smart hash strategy based on file size
- Parallel hash calculation
- Duplicate verification function

#### CLI (cli_v2.py)
- Integrated with all new features
- Config file support
- Undo command
- Stats command
- Better error messages

### 📝 New Modules

```
fileorganizer/
├── core/
│   └── scanner_v2.py          # Improved scanner
├── utils/
│   ├── hashing.py             # Advanced hashing
│   ├── logging.py             # Logging system
│   ├── errors.py              # Error handling
│   └── atomic.py              # Atomic operations
├── plugins/
│   ├── base.py                # Plugin architecture
│   └── builtin.py             # Built-in plugins
├── database.py                # SQLite database
├── undo.py                    # Undo system
├── smart_detection.py         # Smart metadata extraction
├── interactive.py             # Interactive mode
├── web_api.py                 # Web API
└── cli_v2.py                  # Improved CLI
```

### 🧪 Testing
- Added comprehensive test suite
- Unit tests for hashing, database, and plugins
- Pytest-based testing framework

### 📚 Documentation
- Updated README with all new features
- Added migration guide from v1 to v2
- Added plugin development guide
- API documentation

### ⚠️ Breaking Changes
- CLI interface has changed (v2 uses different commands)
- Old scan cache is not compatible
- Configuration format has changed

### Migration from v1 to v2
See MIGRATION.md for detailed migration instructions.

---

## Version 1.0.0 - Initial Release

### Features
- Basic file scanning
- Duplicate detection
- File organization by type and date
- Batch renaming
- Archive functionality
- Command-line interface

### Modules
- scanner.py
- organizer.py
- duplicates.py
- archiver.py
- cli.py
