#!/bin/bash

# SoulseekDownloader Installer
# This script downloads and installs the latest version of SoulseekDownloader for macOS.

# --- Configuration ---
# Your GitHub repository in "username/repo" format
GITHUB_REPO="felixhj/sk"

# --- Style Functions ---
step() {
  echo -e "\033[1;34m==>\033[0m \033[1m$1\033[0m"
}

info() {
  echo "   $1"
}

success() {
  echo -e "\033[1;32m✅ $1\033[0m"
}

fail() {
  echo -e "\033[1;31m❌ $1\033[0m" >&2
  exit 1
}

# --- Main Script ---
main() {
  step "Starting SoulseekDownloader Installer"

  # 1. Detect Architecture
  info "Detecting system architecture..."
  ARCH=$(uname -m)
  if [ "$ARCH" = "x86_64" ]; then
    ARCH="x64"
  elif [ "$ARCH" = "arm64" ]; then
    ARCH="arm64"
  else
    fail "Unsupported architecture: $ARCH. This installer only supports x64 (Intel) and arm64 (Apple Silicon) Macs."
  fi
  info "Detected architecture: $ARCH"

  # 2. Install slsk-batchdl (sldl) dependency
  step "Installing slsk-batchdl dependency..."
  
  # Detect architecture for slsk-batchdl
  if [ "$ARCH" = "x64" ]; then
    SLDL_ARCH="x64"
  elif [ "$ARCH" = "arm64" ]; then
    SLDL_ARCH="arm64"
  fi
  
  # Download latest slsk-batchdl release
  info "Downloading latest slsk-batchdl..."
  SLDL_URL=$(curl -s https://api.github.com/repos/fiso64/slsk-batchdl/releases/latest | grep "browser_download_url.*osx-$SLDL_ARCH.zip" | cut -d'"' -f4)
  
  if [ -z "$SLDL_URL" ]; then
    fail "Could not find slsk-batchdl release for $SLDL_ARCH"
  fi
  
  info "Downloading slsk-batchdl from: $SLDL_URL"
  TEMP_SLDL=$(mktemp -u).zip
  curl -fL -o "$TEMP_SLDL" "$SLDL_URL" || fail "Failed to download slsk-batchdl"
  
  # Extract and install sldl
  info "Installing sldl to /usr/local/bin..."
  unzip -o "$TEMP_SLDL" -d /tmp/
  chmod +x /tmp/sldl
  sudo mv /tmp/sldl /usr/local/bin/ || fail "Failed to install sldl to /usr/local/bin"
  rm "$TEMP_SLDL"
  
  # Verify installation and add to PATH if needed
  info "Verifying sldl installation..."
  if ! command -v sldl &> /dev/null; then
    info "sldl not found in PATH, adding /usr/local/bin to PATH..."
    echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
    export PATH="/usr/local/bin:$PATH"
    info "Please restart your terminal or run: source ~/.zshrc"
  fi
  
  # Test sldl
  if sldl --version &> /dev/null; then
    success "slsk-batchdl installed successfully"
  else
    fail "sldl installation verification failed"
  fi

  # 3. Detect macOS Version and Find the Latest Release Asset
  step "Finding and downloading the latest release..."
  
  # Detect macOS version to choose the right build
  MACOS_VERSION=$(sw_vers -productVersion | cut -d. -f1,2)
  info "Detected macOS version: $MACOS_VERSION"
  
  # Determine which build to download based on macOS version
  if [[ "$MACOS_VERSION" == "12."* ]]; then
    OS_SUFFIX="monterey"
  elif [[ "$MACOS_VERSION" == "13."* ]]; then
    OS_SUFFIX="ventura"
  elif [[ "$MACOS_VERSION" == "14."* ]]; then
    OS_SUFFIX="sonoma"
  else
    # For future macOS versions, default to sonoma build
    OS_SUFFIX="sonoma"
  fi
  
  # Try the version-specific DMG naming pattern
  ASSET_NAME="SoulseekDownloader-${ARCH}-${OS_SUFFIX}.dmg"
  DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/releases/latest/download/${ASSET_NAME}"
  
  info "Downloading from: $DOWNLOAD_URL"

  # 4. Download and Mount
  TEMP_DMG=$(mktemp -u).dmg
  # Use curl with -f to fail fast on 404s and -L to follow redirects
  curl -fL -o "$TEMP_DMG" "$DOWNLOAD_URL" || fail "Download failed. Could not find asset '$ASSET_NAME' in the latest release."
  
  # 4. Install
  step "Installing..."
  info "Mounting the disk image..."
  MOUNT_OUTPUT=$(hdiutil attach "$TEMP_DMG" -nobrowse)
  MOUNT_POINT=$(echo "$MOUNT_OUTPUT" | grep "/Volumes/" | sed 's/.*\(\/Volumes\/.*\)/\1/' | head -1)
  
  if [ -z "$MOUNT_POINT" ]; then
    fail "Failed to mount the disk image."
  fi
  
  INSTALL_DIR="$HOME/Applications"
  info "Installing to $INSTALL_DIR"
  mkdir -p "$INSTALL_DIR"
  
  info "Copying the application..."
  # Copy the app from the mounted DMG to Applications
  cp -R "$MOUNT_POINT/SoulseekDownloader.app" "$INSTALL_DIR/" || fail "Failed to copy the application."
  
  # 5. Clean up
  info "Cleaning up..."
  hdiutil detach "$MOUNT_POINT" -quiet
  rm "$TEMP_DMG"
  rm -f /tmp/sldl  # Clean up any remaining slsk-batchdl files

  success "Installation complete!"
  echo ""
  echo "You can now find SoulseekDownloader in:"
  echo "$INSTALL_DIR/SoulseekDownloader.app"
  echo ""
  echo "To run it, you can double-click the app or use this command:"
  echo "open \"$INSTALL_DIR/SoulseekDownloader.app\""
}

# Run the main function
main 