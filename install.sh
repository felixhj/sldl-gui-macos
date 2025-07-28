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

  # 2. Install slsk-batchdl (sldl) dependency to user's home directory
  step "Installing slsk-batchdl dependency..."
  
  # Detect macOS version for security handling
  MACOS_MAJOR=$(sw_vers -productVersion | cut -d. -f1)
  MACOS_MINOR=$(sw_vers -productVersion | cut -d. -f2)
  
  # Detect architecture for slsk-batchdl
  if [ "$ARCH" = "x64" ]; then
    SLDL_ARCH="x64"
  elif [ "$ARCH" = "arm64" ]; then
    SLDL_ARCH="arm64"
  fi
  
  # macOS 15+ requires pre-approval to avoid "Killed: 9" errors
  if [ "$MACOS_MAJOR" -ge 15 ]; then
    info "Detected macOS $MACOS_MAJOR.$MACOS_MINOR - applying macOS 15+ security workflow..."
    
    # Download sldl to home directory for pre-approval
    info "Downloading slsk-batchdl for pre-approval..."
    SLDL_URL=$(curl -s https://api.github.com/repos/fiso64/slsk-batchdl/releases/latest | grep "browser_download_url.*osx-$SLDL_ARCH.zip" | cut -d'"' -f4)
    
    if [ -z "$SLDL_URL" ]; then
      fail "Could not find slsk-batchdl release for $SLDL_ARCH"
    fi
    
    info "Downloading slsk-batchdl from: $SLDL_URL"
    TEMP_SLDL=$(mktemp -u).zip
    curl -fL -o "$TEMP_SLDL" "$SLDL_URL" || fail "Failed to download slsk-batchdl"
    
    # Extract to home directory for pre-approval
    info "Extracting sldl to home directory for pre-approval..."
    unzip -o "$TEMP_SLDL" -d "$HOME/"
    chmod +x "$HOME/sldl"
    rm "$TEMP_SLDL"
    
    # Provide instructions for manual approval
    echo ""
    info "macOS 15+ detected - manual approval required before continuing"
    info "The sldl binary has been downloaded to: $HOME/sldl"
    echo ""
    info "To continue with the installation, please:"
    info "1. Go to System Settings > Privacy & Security > Developer Tools"
    info "2. Click the lock icon to unlock settings"
    info "3. Add $HOME/sldl to the allowed applications list"
    info "4. Or run this command to trigger a security dialog:"
    info "   $HOME/sldl --version"
    echo ""
    info "Once you've approved sldl in System Settings, type 'Y' and press Enter to continue:"
    
    # Wait for user confirmation
    read -r user_response
    if [ "$user_response" != "Y" ] && [ "$user_response" != "y" ]; then
      info "Installation cancelled by user"
      rm -f "$HOME/sldl"
      exit 0
    fi
    
    # Test the approved sldl
    info "Testing approved sldl..."
    if "$HOME/sldl" --version &> /dev/null; then
      success "sldl approved successfully"
    else
      fail "sldl still not working after approval. Please ensure it's properly added to Developer Tools."
    fi
    
    # Now move to final location and set up PATH
    USER_BIN_DIR="$HOME/.bin"
    info "Moving sldl to final location: $USER_BIN_DIR"
    mkdir -p "$USER_BIN_DIR"
    mv "$HOME/sldl" "$USER_BIN_DIR/" || fail "Failed to move sldl to $USER_BIN_DIR"
    
    # Add to PATH
    info "Adding $USER_BIN_DIR to PATH..."
    if ! echo "$PATH" | grep -q "$USER_BIN_DIR"; then
      echo "export PATH=\"$USER_BIN_DIR:\$PATH\"" >> ~/.zshrc
      export PATH="$USER_BIN_DIR:$PATH"
      info "Added $USER_BIN_DIR to PATH in ~/.zshrc"
    else
      info "$USER_BIN_DIR already in PATH"
    fi
    
    success "slsk-batchdl installed successfully to $USER_BIN_DIR"
    
  else
    # macOS 12-14: Standard installation process
    info "Detected macOS $MACOS_MAJOR.$MACOS_MINOR - applying standard installation..."
    
    # Create user's hidden bin directory
    USER_BIN_DIR="$HOME/.bin"
    info "Creating user bin directory: $USER_BIN_DIR"
    mkdir -p "$USER_BIN_DIR"
    
    # Download latest slsk-batchdl release
    info "Downloading latest slsk-batchdl..."
    SLDL_URL=$(curl -s https://api.github.com/repos/fiso64/slsk-batchdl/releases/latest | grep "browser_download_url.*osx-$SLDL_ARCH.zip" | cut -d'"' -f4)
    
    if [ -z "$SLDL_URL" ]; then
      fail "Could not find slsk-batchdl release for $SLDL_ARCH"
    fi
    
    info "Downloading slsk-batchdl from: $SLDL_URL"
    TEMP_SLDL=$(mktemp -u).zip
    curl -fL -o "$TEMP_SLDL" "$SLDL_URL" || fail "Failed to download slsk-batchdl"
    
    # Extract and install sldl to user's bin directory
    info "Installing sldl to $USER_BIN_DIR..."
    unzip -o "$TEMP_SLDL" -d /tmp/
    chmod +x /tmp/sldl
    mv /tmp/sldl "$USER_BIN_DIR/" || fail "Failed to install sldl to $USER_BIN_DIR"
    rm "$TEMP_SLDL"
    
    # Add user's hidden bin directory to PATH if not already there
    info "Adding $USER_BIN_DIR to PATH..."
    if ! echo "$PATH" | grep -q "$USER_BIN_DIR"; then
      echo "export PATH=\"$USER_BIN_DIR:\$PATH\"" >> ~/.zshrc
      export PATH="$USER_BIN_DIR:$PATH"
      info "Added $USER_BIN_DIR to PATH in ~/.zshrc"
    else
      info "$USER_BIN_DIR already in PATH"
    fi
    
    # Test sldl with version-specific security handling
    info "Testing sldl installation..."
    
    if "$USER_BIN_DIR/sldl" --version &> /dev/null; then
      success "slsk-batchdl installed successfully to $USER_BIN_DIR"
    else
      # Handle security restrictions based on macOS version
      if [ -f "$USER_BIN_DIR/sldl" ] && [ -x "$USER_BIN_DIR/sldl" ]; then
        info "sldl binary exists and is executable, but may be blocked by macOS security"
        
        # macOS 13+ (Ventura and later) have stricter security
        if [ "$MACOS_MAJOR" -ge 13 ]; then
          info "Detected macOS $MACOS_MAJOR.$MACOS_MINOR - applying advanced security handling..."
          
          # Remove quarantine attributes
          info "Removing quarantine attributes..."
          xattr -d com.apple.quarantine "$USER_BIN_DIR/sldl" 2>/dev/null || true
          
          # Try running again after quarantine removal
          info "Testing sldl after quarantine removal..."
          if "$USER_BIN_DIR/sldl" --version &> /dev/null; then
            success "slsk-batchdl installed successfully to $USER_BIN_DIR (quarantine removed)"
          else
            # Still blocked - provide manual approval instructions
            info "sldl still blocked after quarantine removal - manual approval required"
            info "The binary is installed at: $USER_BIN_DIR/sldl"
            info ""
            info "To complete the installation, you need to:"
            info "1. Go to System Settings > Privacy & Security > Developer Tools"
            info "2. Add ~/.bin/sldl to the allowed applications list"
            info "3. Or run this command to trigger a security dialog:"
            info "   ~/.bin/sldl --version"
            info ""
            success "slsk-batchdl installed to $USER_BIN_DIR (manual approval required)"
          fi
        else
          # macOS 12 and earlier - simpler handling
          info "Detected macOS $MACOS_MAJOR.$MACOS_MINOR - applying standard security handling..."
          info "Attempting to remove quarantine attributes..."
          xattr -d com.apple.quarantine "$USER_BIN_DIR/sldl" 2>/dev/null || true
          
          info "Testing sldl after quarantine removal..."
          if "$USER_BIN_DIR/sldl" --version &> /dev/null; then
            success "slsk-batchdl installed successfully to $USER_BIN_DIR (quarantine removed)"
          else
            info "sldl still blocked after quarantine removal"
            info "The binary is installed at: $USER_BIN_DIR/sldl"
            info "You may need to run: ~/.bin/sldl --version (to trigger security dialog)"
            success "slsk-batchdl installed to $USER_BIN_DIR (manual approval may be required)"
          fi
        fi
      else
        fail "sldl installation verification failed - binary not found or not executable"
      fi
    fi
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