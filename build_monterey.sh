#!/bin/bash

# sldl-gui for macOS Monterey Local Build Script
# This script builds the app locally on macOS 12 (Monterey) for distribution

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're on macOS 12
check_macos_version() {
    local version=$(sw_vers -productVersion)
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    
    if [ "$major" -eq 12 ]; then
        log_success "Detected macOS 12.$minor (Monterey)"
    else
        log_error "This script is designed for macOS 12 (Monterey). Detected: $version"
        exit 1
    fi
}

# Check architecture
check_architecture() {
    local arch=$(uname -m)
    if [ "$arch" = "x86_64" ]; then
        ARCH="x64"
        log_info "Detected Intel (x64) architecture"
    elif [ "$arch" = "arm64" ]; then
        ARCH="arm64"
        log_info "Detected Apple Silicon (arm64) architecture"
    else
        log_error "Unsupported architecture: $arch"
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Check for Python 3.x (any version 3.9 or higher)
    PYTHON_CMD=""
    for cmd in python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "$cmd" &> /dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    done
    
    if [ -z "$PYTHON_CMD" ]; then
        log_error "No Python 3.x found. Please install Python 3.9 or higher."
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version)
    log_info "Using $PYTHON_VERSION"
    
    # Create virtual environment
    log_info "Creating virtual environment..."
    $PYTHON_CMD -m venv venv_monterey
    
    # Upgrade pip
    ./venv_monterey/bin/pip install --upgrade pip
    
    # Install requirements
    log_info "Installing Python packages..."
    ./venv_monterey/bin/pip install -r requirements.txt
    ./venv_monterey/bin/pip install pyinstaller
    
    log_success "Dependencies installed"
}

# Download slsk-batchdl
download_slsk_batchdl() {
    log_info "Downloading slsk-batchdl..."
    
    # Get latest release URL
    local release_url=$(curl -s https://api.github.com/repos/fiso64/slsk-batchdl/releases/latest | grep "browser_download_url.*osx-$ARCH.zip" | cut -d'"' -f4)
    
    if [ -z "$release_url" ]; then
        log_error "Could not find slsk-batchdl release for $ARCH"
        exit 1
    fi
    
    log_info "Downloading from: $release_url"
    curl -L -o "sldl_osx-$ARCH.zip" "$release_url"
    
    # Extract
    log_info "Extracting slsk-batchdl..."
    unzip -o "sldl_osx-$ARCH.zip"
    mkdir -p bin
    mv sldl bin/
    chmod +x bin/sldl
    
    log_success "slsk-batchdl downloaded and extracted"
}

# Build the application
build_application() {
    log_info "Building sldl-gui application..."
    
    # Build with PyInstaller
    ./venv_monterey/bin/pyinstaller --noconfirm --windowed --name="sldl-gui" \
        --add-binary="bin/sldl:bin" \
        --icon=icon.icns \
        --osx-entitlements-file="entitlements.plist" \
        sldl-gui-macos.py
    
    log_success "Application built successfully"
}

# Create DMG
create_dmg() {
    log_info "Creating DMG installer..."
    
    # Install create-dmg if not available
    if ! command -v create-dmg &> /dev/null; then
        log_info "Installing create-dmg..."
        brew install create-dmg
    fi
    
    # Create a temporary directory for DMG contents
    DMG_TEMP_DIR=$(mktemp -d)
    
    # Copy the app to the temp directory
    cp -R "dist/sldl-gui.app" "$DMG_TEMP_DIR/"
    
    # Copy the uninstall script to the temp directory
    cp "uninstall.command" "$DMG_TEMP_DIR/"
    
    # Create DMG with both app and uninstall script
    create-dmg \
        --volname "sldl-gui Installer" \
        --window-pos 200 120 \
        --window-size 800 400 \
        --icon-size 100 \
        --icon "sldl-gui.app" 200 190 \
        --hide-extension "sldl-gui.app" \
        --icon "uninstall.command" 400 190 \
        --hide-extension "uninstall.command" \
        --app-drop-link 600 185 \
        --hdiutil-quiet \
        "sldl-gui-$ARCH-monterey.dmg" \
        "$DMG_TEMP_DIR"
    
    # Clean up temp directory
    rm -rf "$DMG_TEMP_DIR"
    
    log_success "DMG created: sldl-gui-$ARCH-monterey.dmg"
}

# Clean up
cleanup() {
    log_info "Cleaning up build artifacts..."
    
    # Remove build artifacts
    rm -rf build/
    rm -rf dist/sldl-gui/
    rm -f "sldl_osx-$ARCH.zip"
    rm -rf bin
    
    # Remove virtual environment
    rm -rf venv_monterey/
    
    # Remove Python cache files
    rm -rf __pycache__/
    find . -name "*.pyc" -delete
    find . -name "*.pyo" -delete
    
    # Remove PyInstaller spec file if it exists
    rm -f "sldl-gui.spec"
    
    # Remove any temporary files
    rm -f sldl.pdb
    
    log_success "Cleanup complete"
}

# Main execution
main() {
    log_info "Starting Monterey build process..."
    
    check_macos_version
    check_architecture
    install_dependencies
    download_slsk_batchdl
    build_application
    create_dmg
    cleanup
    
    log_success "Build complete! DMG file: sldl-gui-$ARCH-monterey.dmg"
    echo ""
    echo "You can now upload this DMG to your GitHub release."
    echo "To upload to GitHub releases, you can use:"
    echo "gh release upload <tag> sldl-gui-$ARCH-monterey.dmg"
}

# Run main function
main "$@" 