# Building SLDL GUI for macOS for macOS 12 (Monterey)

Since GitHub Actions no longer supports macOS 12 runners, the Monterey build needs to be created locally. This guide will walk you through the process.

## Prerequisites

1. **macOS 12 (Monterey)** - You must be running macOS 12 to build the Monterey-compatible version
2. **Homebrew** - For installing dependencies
3. **GitHub CLI** - For uploading releases (optional, for release management)

## Quick Start

If you have all prerequisites installed, you can simply run:

```bash
./build_monterey.sh
```

This will automatically:

- Detect your macOS version and architecture
- Install Python 3.9 and dependencies
- Download the latest slsk-batchdl
- Build the application
- Create a DMG installer
- Clean up build artifacts

## Manual Installation of Prerequisites

### 1. Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Python (if needed)

The script will automatically detect and use Python 3.9 or higher. If you don't have Python installed:

```bash
brew install python@3.12
```

### 3. Install GitHub CLI (for uploading releases)

```bash
brew install gh
gh auth login
```

## Building the Application

### Option 1: Automated Build Script

```bash
# Make the script executable (if not already)
chmod +x build_monterey.sh

# Run the build
./build_monterey.sh
```

### Option 2: Manual Build Process

If you prefer to run the steps manually:

```bash
# 1. Create virtual environment
python3 -m venv venv_monterey  # or python3.12, python3.11, etc.
source venv_monterey/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# 3. Download slsk-batchdl
# (The script will automatically detect your architecture)
curl -s https://api.github.com/repos/fiso64/slsk-batchdl/releases/latest | grep "browser_download_url.*osx-x64.zip" | cut -d'"' -f4 | xargs curl -L -o sldl_osx-x64.zip
unzip -o sldl_osx-x64.zip
chmod +x sldl

# 4. Build the application
pyinstaller --noconfirm --windowed --name="SoulseekDownloader" \
    --add-binary="sldl:." \
    --add-data="csv_processor.py:." \
    --icon=icon.icns \
    --osx-entitlements-file="entitlements.plist" \
    soulseek_downloader.py

# 5. Create DMG
brew install create-dmg
create-dmg \
    --volname "SoulseekDownloader Installer" \
    --window-pos 200 120 \
    --window-size 800 400 \
    --icon-size 100 \
    --icon "SoulseekDownloader.app" 200 190 \
    --hide-extension "SoulseekDownloader.app" \
    --app-drop-link 600 185 \
    "SoulseekDownloader-x64-monterey.dmg" \
    "dist/SoulseekDownloader.app"
```

## Uploading to GitHub Releases

After building, you can upload the DMG to a GitHub release:

```bash
# Upload to an existing release
./upload_release.sh v1.1.0
```

Or manually:

```bash
# Create a new release (if it doesn't exist)
gh release create v1.1.0 --draft --title "Release v1.1.0" --notes "Release v1.1.0 with Monterey support"

# Upload the DMG
gh release upload v1.1.0 SoulseekDownloader-x64-monterey.dmg
```

## Troubleshooting

### Python Not Found

If you get an error about Python not being found:

```bash
# Install Python via Homebrew
brew install python@3.12

# Add to PATH (add this to your ~/.zshrc or ~/.bash_profile)
export PATH="/opt/homebrew/bin:$PATH"
```

### Permission Denied

If you get permission errors:

```bash
# Make scripts executable
chmod +x build_monterey.sh
chmod +x upload_release.sh
```

### GitHub CLI Not Authenticated

If you get authentication errors:

```bash
# Login to GitHub
gh auth login
```

### Build Fails

If the build fails, check:

1. You're running macOS 12 (Monterey)
2. All dependencies are installed
3. You have sufficient disk space
4. Your internet connection is stable

## Output Files

After a successful build, you'll have:

- `SoulseekDownloader-x64-monterey.dmg` - The installer for Intel Macs
- `SoulseekDownloader-arm64-monterey.dmg` - The installer for Apple Silicon Macs (if built on M1/M2)

## Why Local Build for Monterey?

GitHub Actions removed support for macOS 12 runners in favor of newer versions. Since the app needs to be built on the target macOS version for compatibility (to avoid the `_mkfifoat` symbol error), we need to build Monterey versions locally.

The resulting DMG will be compatible with:

- macOS 12.0 (Monterey) and later
- Both Intel (x64) and Apple Silicon (arm64) architectures
