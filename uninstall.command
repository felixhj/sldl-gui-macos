#!/bin/bash

# sldl-gui Uninstaller for macOS
# This script removes the sldl-gui application and all associated files

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

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_error "This script should not be run as root. Please run it as a regular user."
        exit 1
    fi
}

# Confirm uninstallation
confirm_uninstall() {
    echo ""
    log_warning "This will completely remove sldl-gui and all associated files:"
    echo "  • sldl-gui.app from ~/Applications"
    echo "  • Settings file: ~/.soulseek_downloader_settings.json"
    echo "  • Any log.csv files in download directories"
    echo "  • Any _index.csv files in download directories"
    echo "  • Application cache and preferences"
    echo ""
    
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Uninstallation cancelled."
        exit 0
    fi
}

# Remove the application
remove_application() {
    log_info "Removing sldl-gui application..."
    
    APP_PATH="$HOME/Applications/sldl-gui.app"
    
    if [ -d "$APP_PATH" ]; then
        rm -rf "$APP_PATH"
        log_success "Removed sldl-gui.app"
    else
        log_warning "sldl-gui.app not found in ~/Applications"
    fi
    
    # Also check for any other possible locations
    OTHER_LOCATIONS=(
        "/Applications/sldl-gui.app"
        "$HOME/Applications/SoulseekDownloader.app"
        "/Applications/SoulseekDownloader.app"
    )
    
    for location in "${OTHER_LOCATIONS[@]}"; do
        if [ -d "$location" ]; then
            log_info "Found app in $location, removing..."
            rm -rf "$location"
            log_success "Removed app from $location"
        fi
    done
}

# Remove settings file
remove_settings() {
    log_info "Removing settings file..."
    
    SETTINGS_FILE="$HOME/.soulseek_downloader_settings.json"
    
    if [ -f "$SETTINGS_FILE" ]; then
        rm -f "$SETTINGS_FILE"
        log_success "Removed settings file: $SETTINGS_FILE"
    else
        log_info "No settings file found"
    fi
}

# Remove application preferences and cache
remove_preferences() {
    log_info "Removing application preferences and cache..."
    
    # Application preferences
    PREF_DIRS=(
        "$HOME/Library/Preferences/com.script.sldl-gui.plist"
        "$HOME/Library/Preferences/com.script.SoulseekDownloader.plist"
        "$HOME/Library/Caches/com.script.sldl-gui"
        "$HOME/Library/Caches/com.script.SoulseekDownloader"
        "$HOME/Library/Application Support/sldl-gui"
        "$HOME/Library/Application Support/SoulseekDownloader"
        "$HOME/Library/Saved Application State/com.script.sldl-gui.savedState"
        "$HOME/Library/Saved Application State/com.script.SoulseekDownloader.savedState"
    )
    
    for pref_dir in "${PREF_DIRS[@]}"; do
        if [ -e "$pref_dir" ]; then
            rm -rf "$pref_dir"
            log_success "Removed: $pref_dir"
        fi
    done
}

# Remove any log files in common download locations
remove_log_files() {
    log_info "Searching for and removing log files..."
    
    # Common download locations to search
    SEARCH_DIRS=(
        "$HOME/Downloads"
        "$HOME/Desktop"
        "$HOME/Documents"
        "$HOME/Music"
    )
    
    # File patterns to remove
    LOG_PATTERNS=(
        "log.csv"
        "*_index.csv"
    )
    
    for search_dir in "${SEARCH_DIRS[@]}"; do
        if [ -d "$search_dir" ]; then
            for pattern in "${LOG_PATTERNS[@]}"; do
                find "$search_dir" -name "$pattern" -type f 2>/dev/null | while read -r file; do
                    log_info "Removing log file: $file"
                    rm -f "$file"
                done
            done
        fi
    done
}

# Remove from Dock if present
remove_from_dock() {
    log_info "Checking if app is in Dock..."
    
    # Check if sldl-gui is in the Dock
    if defaults read com.apple.dock persistent-apps | grep -q "sldl-gui" 2>/dev/null; then
        log_info "Removing sldl-gui from Dock..."
        # This is a bit complex to do programmatically, so we'll just inform the user
        log_warning "sldl-gui may still appear in your Dock. You can remove it manually by dragging it out of the Dock."
    fi
}

# Clean up any remaining references
cleanup_references() {
    log_info "Cleaning up any remaining references..."
    
    # Remove any launchd entries
    LAUNCHD_PATTERNS=(
        "com.script.sldl-gui"
        "com.script.SoulseekDownloader"
    )
    
    for pattern in "${LAUNCHD_PATTERNS[@]}"; do
        if launchctl list | grep -q "$pattern" 2>/dev/null; then
            log_info "Removing launchd entry: $pattern"
            launchctl remove "$pattern" 2>/dev/null || true
        fi
    done
}

# Main uninstallation function
main() {
    echo ""
    echo "=========================================="
    echo "    sldl-gui Uninstaller for macOS"
    echo "=========================================="
    echo ""
    
    # Check if not running as root
    check_root
    
    # Confirm uninstallation
    confirm_uninstall
    
    # Perform uninstallation steps
    remove_application
    remove_settings
    remove_preferences
    remove_log_files
    remove_from_dock
    cleanup_references
    
    echo ""
    log_success "Uninstallation complete!"
    echo ""
    echo "sldl-gui has been completely removed from your system."
    echo ""
    echo "If you want to reinstall in the future, you can download it from:"
    echo "https://github.com/scriptit/sldl-gui-macos/releases"
    echo ""
    
    # Prompt to restart Dock to refresh
    read -p "Would you like to restart the Dock to refresh any remaining references? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restarting Dock..."
        killall Dock
        log_success "Dock restarted"
    fi
}

# Run the main function
main 