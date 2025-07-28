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

  # 2. Find the Latest Release Asset
  step "Finding the latest release..."
  ASSET_NAME="SoulseekDownloader-macOS-${ARCH}.zip"
  
  API_URL="https://api.github.com/repos/${GITHUB_REPO}/releases/latest"
  DOWNLOAD_URL=$(curl -s "$API_URL" | jq --arg name "$ASSET_NAME" -r '.assets[] | select(.name == $name) | .browser_download_url')

  if [ -z "$DOWNLOAD_URL" ]; then
    fail "Could not find a release asset named '$ASSET_NAME' for your architecture."
  fi
  info "Found release asset: $DOWNLOAD_URL"

  # 3. Download and Unpack
  step "Downloading the application..."
  TEMP_FILE=$(mktemp)
  curl -L -o "$TEMP_FILE" "$DOWNLOAD_URL" || fail "Download failed."
  
  # 4. Install
  step "Installing..."
  INSTALL_DIR="$HOME/Applications/SoulseekDownloader"
  info "Creating installation directory at $INSTALL_DIR"
  mkdir -p "$INSTALL_DIR"
  
  info "Unzipping the application..."
  # Unzip directly into the install directory, overwriting existing files
  unzip -o "$TEMP_FILE" -d "$INSTALL_DIR" || fail "Failed to unzip the application."
  
  # 5. Clean up
  info "Cleaning up temporary files..."
  rm "$TEMP_FILE"

  success "Installation complete!"
  echo ""
  echo "You can now find SoulseekDownloader in:"
  echo "$INSTALL_DIR"
  echo ""
  echo "To run it, you can double-click the app or use this command:"
  echo "open \"$INSTALL_DIR/SoulseekDownloader.app\""
}

# Run the main function
main 