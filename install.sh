#!/bin/bash

# sldl-gui for macOS Installer
# This script downloads and installs the latest version of sldl-gui for macOS.
# The app now bundles sldl internally, so no separate dependency installation is needed.

# --- Configuration ---
# Your GitHub repository in "username/repo" format
GITHUB_REPO="felixhj/sldl-gui-macos"

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
  step "Starting sldl-gui for macOS Installer"

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

  # 2. Detect macOS Version and Find the Latest Release Asset
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
  ASSET_NAME="sldl-gui-${ARCH}-${OS_SUFFIX}.dmg"
  DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/releases/latest/download/${ASSET_NAME}"
  
  info "Downloading from: $DOWNLOAD_URL"

  # 3. Download and Mount
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
  cp -R "$MOUNT_POINT/sldl-gui.app" "$INSTALL_DIR/" || fail "Failed to copy the application."
  
  # 5. Clean up
  info "Cleaning up..."
  hdiutil detach "$MOUNT_POINT" -quiet
  rm "$TEMP_DMG"

  success "Installation complete!"
  echo ""
  echo "You can now find sldl-gui in:"
echo "$INSTALL_DIR/sldl-gui.app"
  echo ""
  echo "To run it, you can double-click the app or use this command:"
  echo "open \"$INSTALL_DIR/sldl-gui.app\""
  echo ""
  echo "Note: The app now bundles sldl internally, so no additional dependencies are required."
}

# Run the main function
main 