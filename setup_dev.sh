#!/bin/bash

# Development Setup Script for sldl-gui-macos
# This script downloads sldl locally for development use

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

# Download slsk-batchdl for development
download_slsk_batchdl() {
    log_info "Downloading slsk-batchdl for development..."
    
    # Check if dev/bin directory exists
    if [ ! -d "dev/bin" ]; then
        log_info "Creating dev/bin directory..."
        mkdir -p dev/bin
    fi
    
    # Check if sldl already exists
    if [ -f "dev/bin/sldl" ]; then
        log_warning "sldl already exists in dev/bin. Skipping download."
        return 0
    fi
    
    # Get latest release URL
    local release_url=$(curl -s https://api.github.com/repos/fiso64/slsk-batchdl/releases/latest | grep "browser_download_url.*osx-$ARCH.zip" | cut -d'"' -f4)
    
    if [ -z "$release_url" ]; then
        log_error "Could not find slsk-batchdl release for $ARCH"
        exit 1
    fi
    
    log_info "Downloading from: $release_url"
    curl -L -o "dev/sldl_osx-$ARCH.zip" "$release_url"
    
    # Extract
    log_info "Extracting slsk-batchdl..."
    cd dev
    unzip -o "sldl_osx-$ARCH.zip"
    mv sldl bin/
    chmod +x bin/sldl
    
    # Clean up zip file
    rm -f "sldl_osx-$ARCH.zip"
    cd ..
    
    log_success "slsk-batchdl downloaded and extracted to dev/bin/sldl"
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Check for Python 3.x
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
    
    # Install requirements
    log_info "Installing Python packages..."
    $PYTHON_CMD -m pip install -r requirements.txt
    
    log_success "Dependencies installed"
}

# Main execution
main() {
    log_info "Setting up development environment for sldl-gui-macos..."
    
    check_architecture
    install_dependencies
    download_slsk_batchdl
    
    log_success "Development setup complete!"
    log_info "You can now run: python3 sldl-gui-macos.py"
    log_info "The app will use the local sldl binary in dev/bin/sldl"
}

# Run main function
main "$@" 