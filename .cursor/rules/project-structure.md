# Project Structure and Architecture

## Overview

SLDL GUI for macOS is a Python-based desktop application that provides a graphical user interface for batch downloading music from Soulseek using YouTube playlist URLs. The application is built specifically for macOS using native Cocoa frameworks through PyObjC.

## Architecture

### Technology Stack

- **Language**: Python 3.x
- **GUI Framework**: PyObjC (Cocoa bindings for Python)
- **Core Tool**: `sldl` (slsk-batchdl command-line tool)
- **Platform**: macOS 12.0 (Monterey) or later
- **Architectures**: Intel (x64) and Apple Silicon (arm64)

### Design Approach

- **Native macOS Integration**: Uses Cocoa frameworks for a native look and feel
- **Thread-Safe Operations**: Downloads run in background threads to keep GUI responsive
- **Self-Contained**: Bundles the `sldl` dependency with the application
- **Settings Persistence**: Automatically saves and restores user preferences
- **Automated Processing**: Post-download CSV processing and cleanup

## Project Structure

```
sldl-gui-macos/
├── .cursor/                          # Cursor IDE configuration
│   ├── rules/                        # Project rules and guidelines
│   │   └── tracking.mdc              # Logging and tracking rules
│   └── logs/                         # Project logs
│       ├── changes.md                # Changes log
│       └── project-structure.md      # This file
├── .github/                          # GitHub configuration
│   └── workflows/
│       └── build.yml                 # CI/CD build workflow
├── .vscode/                          # VSCode configuration
│   └── settings.json                 # Editor settings
├── dist/                             # Build output directory
├── soulseek_downloader.py            # Main application (892 lines)
├── csv_processor.py                  # CSV processing module (218 lines)
├── requirements.txt                  # Python dependencies
├── install.sh                        # Installation script
├── build_monterey.sh                 # Monterey build script
├── uninstall.command                 # Uninstall script for users
├── BUILD_MONTEREY.md                 # Monterey build documentation
├── GITHUB_ACTIONS_UPDATE.md          # CI/CD documentation
├── README.md                         # Project documentation
├── entitlements.plist                # macOS app entitlements
├── icon.icns                         # Application icon
└── .gitignore                        # Git ignore patterns
```

## Core Components

### 1. Main Application (`soulseek_downloader.py`)

- **Size**: 892 lines
- **Purpose**: Main GUI application and business logic
- **Key Classes**:
  - `AppDelegate`: Main application delegate handling UI and lifecycle
- **Key Features**:
  - YouTube playlist URL processing
  - Soulseek authentication
  - Download progress tracking
  - Settings management
  - Thread-safe operations

### 2. CSV Processor (`csv_processor.py`)

- **Size**: 218 lines
- **Purpose**: Post-download CSV file processing
- **Key Classes**:
  - `SLDLCSVProcessor`: Handles CSV file processing and cleanup
- **Key Features**:
  - Converts numeric status codes to human-readable descriptions
  - Saves processed data to `log.csv`
  - Removes original `_index.csv` files

### 3. Build System

- **Installation**: `install.sh` - Automated installation script
- **Uninstallation**: `uninstall.command` - Comprehensive uninstall script
- **Monterey Builds**: `build_monterey.sh` - Local build process for macOS 12
- **CI/CD**: GitHub Actions workflow for automated builds
- **Distribution**: Multiple build variants for different macOS versions

## Dependencies

### Python Dependencies (`requirements.txt`)

```
pyobjc-framework-Cocoa>=9.0    # Cocoa GUI framework bindings
pyobjc-core>=9.0               # Core PyObjC functionality
```

### External Dependencies

- **sldl**: Command-line tool from slsk-batchdl (bundled with application)
- **macOS**: 12.0+ with native Cocoa frameworks

## Key Design Decisions

### 1. Native macOS Integration

- **Choice**: PyObjC over cross-platform frameworks (Tkinter, Qt, etc.)
- **Rationale**: Better performance, native look/feel, and macOS integration
- **Trade-offs**: Platform-specific, requires macOS-specific knowledge

### 2. Self-Contained Distribution

- **Choice**: Bundle `sldl` with the application
- **Rationale**: Simplifies installation, ensures compatibility
- **Trade-offs**: Larger application size, dependency on bundled version

### 3. Thread-Safe Architecture

- **Choice**: Background threads for downloads
- **Rationale**: Keeps GUI responsive during long-running operations
- **Implementation**: Threading module with proper synchronization

### 4. Settings Persistence

- **Choice**: JSON-based settings file
- **Location**: `~/.soulseek_downloader_settings.json`
- **Rationale**: Simple, human-readable, no database required

## Build and Distribution

### Build Variants

- **Monterey (macOS 12)**: Local builds due to GitHub Actions limitations
- **Ventura (macOS 13)**: Automated GitHub Actions builds
- **Sonoma (macOS 14)**: Automated GitHub Actions builds

### Installation Process

1. Architecture detection (Intel/Apple Silicon)
2. macOS version detection
3. Download appropriate build variant
4. Install to `~/Applications/SoulseekDownloader`

## Development Workflow

### Local Development

- Python 3.x with PyObjC installed
- Direct execution of `soulseek_downloader.py`
- VSCode configuration for development

### CI/CD Pipeline

- GitHub Actions for automated builds
- Multiple macOS versions and architectures
- Automated testing and distribution

## Future Considerations

### Potential Improvements

- Cross-platform support (Windows/Linux)
- Modern GUI framework migration (SwiftUI, etc.)
- Enhanced error handling and recovery
- Plugin system for additional features
- Cloud sync for settings and preferences

### Maintenance

- Regular dependency updates
- macOS compatibility testing
- User feedback integration
- Performance optimization

---

_Last Updated: 2024-12-19_
_Maintained by: Cursor AI Assistant_
