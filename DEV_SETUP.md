# Development Setup Guide

This guide explains how to set up the development environment for sldl-gui-macos.

## Quick Start

1. **Run the setup script:**

   ```bash
   ./setup_dev.sh
   ```

2. **Start development:**
   ```bash
   python3 sldl-gui-macos.py
   ```

That's it! The setup script will automatically:

- Detect your system architecture (Intel/Apple Silicon)
- Download the appropriate `sldl` binary
- Install Python dependencies
- Set up the development environment

## What the Setup Does

### 1. Downloads sldl Binary

- Automatically detects your macOS architecture (x64 or arm64)
- Downloads the latest `sldl` binary from GitHub releases
- Places it in `dev/bin/sldl` (gitignored)

### 2. Installs Dependencies

- Installs Python packages from `requirements.txt`
- Ensures PyObjC is available for GUI development

### 3. Smart Path Detection

The application now checks for `sldl` in this order:

1. **Frozen app mode**: `sys._MEIPASS/bin/sldl` (for built apps)
2. **Development mode**: `dev/bin/sldl` (local development)
3. **Fallback**: System `sldl` (if available in PATH)

## Development Workflow

### Before Making Changes

```bash
# Run the app directly (no rebuilding needed)
python3 sldl-gui-macos.py
```

### Testing Changes

- Make your changes to `sldl-gui-macos.py`
- Run the app directly to test
- No need to rebuild unless you're testing the final distribution

### Building for Distribution

When ready to build:

```bash
./build_monterey.sh
```

## File Structure

```
sldl-gui-macos/
├── dev/                    # Development files (gitignored)
│   └── bin/
│       └── sldl           # Local sldl binary
├── setup_dev.sh           # Development setup script
├── sldl-gui-macos.py      # Main application
└── ...                    # Other project files
```

## Benefits

- **Faster Development**: No rebuilding required for testing
- **Direct Execution**: Run `python3 sldl-gui-macos.py` directly
- **No Build Interference**: Development setup doesn't affect build process
- **Automatic Setup**: Single command sets up everything needed
- **Architecture Aware**: Automatically downloads correct binary for your system

## Troubleshooting

### If setup_dev.sh fails:

1. Check your internet connection
2. Ensure you have Python 3.9+ installed
3. Verify you have write permissions in the project directory

### If the app can't find sldl:

1. Run `./setup_dev.sh` again
2. Check that `dev/bin/sldl` exists and is executable
3. Verify the binary works: `dev/bin/sldl --version`

### If you get permission errors:

```bash
chmod +x setup_dev.sh
chmod +x dev/bin/sldl
```

## Notes

- The `dev/` directory is gitignored to prevent development files from being committed
- The setup script is idempotent - running it multiple times is safe
- The local `sldl` binary is the same version used in production builds
- This setup doesn't affect the existing build process or GitHub Actions
