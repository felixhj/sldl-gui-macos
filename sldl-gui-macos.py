#!/usr/bin/env python3
"""sldl-gui for macOS - PyObjC GUI version."""

import subprocess
import threading
import json
import sys
import re
import urllib.request
import urllib.error
import ssl
from pathlib import Path

# Application version
APP_VERSION = "0.3.6"

from csv_processor import SLDLCSVProcessor

try:
    import objc
    from Cocoa import (
        NSApplication, NSApp, NSWindow, NSButton, NSTextField, NSSecureTextField,
        NSScrollView, NSTextView, NSProgressIndicator, NSMakeRect,
        NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
        NSWindowStyleMaskResizable, NSBackingStoreBuffered,
        NSOpenPanel, NSObject, NSApplicationActivationPolicyRegular,
        NSString, NSAlert, NSAlertFirstButtonReturn, NSPopUpButton,
        NSButtonTypeSwitch, NSMenu, NSMenuItem, NSColor,
        NSFontAttributeName, NSForegroundColorAttributeName,
        NSBezelStyleRounded, NSTextFieldRoundedBezel,
        NSViewWidthSizable, NSViewHeightSizable, NSViewMinXMargin,
        NSViewMaxXMargin, NSViewMinYMargin, NSViewMaxYMargin
    )
except ImportError as e:
    print(f"Error importing PyObjC: {e}")
    print("Please install PyObjC with: pip install pyobjc-framework-Cocoa")
    sys.exit(1)

SETTINGS_FILE = Path.home() / ".soulseek_downloader_settings.json"

def check_for_updates():
    """Check for updates by comparing current version with latest GitHub release."""
    try:
        # GitHub API endpoint for releases
        url = "https://api.github.com/repos/felixhj/sldl-gui-macos/releases/latest"
        
        # Create request with User-Agent to avoid rate limiting
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'sldl-gui-macos')
        
        # Create SSL context that doesn't verify certificates (for macOS compatibility)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Fetch latest release info
        with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
            data = json.loads(response.read().decode())
            latest_version = data['tag_name'].lstrip('v')  # Remove 'v' prefix if present
            
            # Compare versions
            if latest_version != APP_VERSION:
                return latest_version
            return None
            
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError, ValueError) as e:
        # Silently fail on network errors or parsing issues
        print(f"Update check failed: {e}")
        return None

class AppDelegate(NSObject):
    
    def applicationDidFinishLaunching_(self, notification):
        # Initialize process reference for stopping
        self.current_process = None
        self.download_running = False
        
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            self.sldl_path = Path(sys._MEIPASS) / 'bin' / 'sldl'
        else:
            # Check for local development sldl first
            local_sldl = Path(__file__).parent / 'dev' / 'bin' / 'sldl'
            if local_sldl.exists() and local_sldl.is_file():
                self.sldl_path = str(local_sldl)
            else:
                self.sldl_path = 'sldl'

        self.setup_menu()
        self.build_ui()
        self.load_settings()
        
        # Check for updates in background thread
        self.check_for_updates_async()
        
        NSApp.activateIgnoringOtherApps_(True)

    def setup_menu(self):
        """Setup application menu with Edit menu for copy/paste support and Extra Tools menu."""
        # Create main menu bar
        main_menu = NSMenu.alloc().init()
        
        # Create App menu
        app_menu_item = NSMenuItem.alloc().init()
        main_menu.addItem_(app_menu_item)
        app_menu = NSMenu.alloc().init()
        app_menu_item.setSubmenu_(app_menu)
        
        # Add Quit item to app menu
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit sldl-gui", "terminate:", "q"
        )
        app_menu.addItem_(quit_item)
        
        # Create Edit menu
        edit_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Edit", None, ""
        )
        main_menu.addItem_(edit_menu_item)
        edit_menu = NSMenu.alloc().initWithTitle_("Edit")
        edit_menu_item.setSubmenu_(edit_menu)
        
        # Add standard Edit menu items
        cut_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Cut", "cut:", "x"
        )
        edit_menu.addItem_(cut_item)
        
        copy_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Copy", "copy:", "c"
        )
        edit_menu.addItem_(copy_item)
        
        paste_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Paste", "paste:", "v"
        )
        edit_menu.addItem_(paste_item)
        
        edit_menu.addItem_(NSMenuItem.separatorItem())
        
        select_all_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Select All", "selectAll:", "a"
        )
        edit_menu.addItem_(select_all_item)
        
        # Create Extra Tools menu
        extra_tools_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Extra Tools", None, ""
        )
        main_menu.addItem_(extra_tools_menu_item)
        extra_tools_menu = NSMenu.alloc().initWithTitle_("Extra Tools")
        extra_tools_menu_item.setSubmenu_(extra_tools_menu)
        
        # Add Output to CSV item
        output_csv_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Output to .csv", "outputToCSV:", ""
        )
        extra_tools_menu.addItem_(output_csv_item)
        
        # Set the main menu
        NSApp.setMainMenu_(main_menu)

    def build_ui(self):
        # Create the main window (make it taller for new controls)
        style = (
            NSWindowStyleMaskTitled |
            NSWindowStyleMaskClosable |
            NSWindowStyleMaskResizable
        )
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(100.0, 100.0, 750.0, 650.0),  # Made window taller
            style,
            NSBackingStoreBuffered,
            False
        )
        self.window.setTitle_("sldl-gui")
        self.window.center()
        self.window.setMinSize_(self.window.frame().size)
        view = self.window.contentView()
        
        # --- Constants for layout ---
        PADDING = 20
        CONTROL_HEIGHT = 24
        BUTTON_HEIGHT = 24
        START_BUTTON_HEIGHT = 32
        LABEL_WIDTH = 200
        FIELD_Y_SPACING = 40
        SECTION_SPACING = 40
        
        # --- Top-Down Layout ---
        y = view.frame().size.height - PADDING

        # Source Selection (YouTube/Spotify)
        y -= CONTROL_HEIGHT
        self.source_label = NSTextField.labelWithString_("Source:")
        self.source_label.setFrame_(NSMakeRect(PADDING, y, LABEL_WIDTH, CONTROL_HEIGHT))
        self.source_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.source_label)
        
        source_field_x = PADDING + LABEL_WIDTH
        self.source_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(source_field_x, y, 150, CONTROL_HEIGHT))
        self.source_popup.addItemsWithTitles_(["YouTube Playlist", "Spotify Playlist"])
        self.source_popup.selectItemWithTitle_("YouTube Playlist")
        self.source_popup.setTarget_(self)
        self.source_popup.setAction_("sourceChanged:")
        self.source_popup.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.source_popup)

        # YouTube Playlist URL
        y -= FIELD_Y_SPACING
        self.playlist_label = NSTextField.labelWithString_("YouTube Playlist URL:")
        self.playlist_label.setFrame_(NSMakeRect(PADDING, y, LABEL_WIDTH, CONTROL_HEIGHT))
        self.playlist_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.playlist_label)
        
        playlist_field_x = PADDING + LABEL_WIDTH
        playlist_field_width = view.frame().size.width - playlist_field_x - PADDING
        self.playlist_field = NSTextField.alloc().initWithFrame_(NSMakeRect(playlist_field_x, y, playlist_field_width, CONTROL_HEIGHT))
        self.playlist_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.playlist_field.setEditable_(True)
        self.playlist_field.setSelectable_(True)
        self.playlist_field.cell().setScrollable_(True)
        self.playlist_field.cell().setWraps_(False)
        self.playlist_field.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        view.addSubview_(self.playlist_field)

        # Spotify Playlist URL (initially hidden)
        self.spotify_label = NSTextField.labelWithString_("Spotify Playlist URL:")
        self.spotify_label.setFrame_(NSMakeRect(PADDING, y, LABEL_WIDTH, CONTROL_HEIGHT))
        self.spotify_label.setAutoresizingMask_(NSViewMinYMargin)
        self.spotify_label.setHidden_(True)
        view.addSubview_(self.spotify_label)
        
        self.spotify_field = NSTextField.alloc().initWithFrame_(NSMakeRect(playlist_field_x, y, playlist_field_width, CONTROL_HEIGHT))
        self.spotify_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.spotify_field.setEditable_(True)
        self.spotify_field.setSelectable_(True)
        self.spotify_field.cell().setScrollable_(True)
        self.spotify_field.cell().setWraps_(False)
        self.spotify_field.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        self.spotify_field.setHidden_(True)
        view.addSubview_(self.spotify_field)

        # Soulseek Username
        y -= FIELD_Y_SPACING
        self.user_label = NSTextField.labelWithString_("Soulseek Username:")
        self.user_label.setFrame_(NSMakeRect(PADDING, y, LABEL_WIDTH, CONTROL_HEIGHT))
        self.user_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.user_label)
        self.user_field = NSTextField.alloc().initWithFrame_(NSMakeRect(playlist_field_x, y, 200, CONTROL_HEIGHT))
        self.user_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.user_field.setEditable_(True)
        self.user_field.setSelectable_(True)
        self.user_field.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.user_field)

        # Soulseek Password
        y -= FIELD_Y_SPACING
        self.pass_label = NSTextField.labelWithString_("Soulseek Password:")
        self.pass_label.setFrame_(NSMakeRect(PADDING, y, LABEL_WIDTH, CONTROL_HEIGHT))
        self.pass_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.pass_label)
        self.pass_field = NSSecureTextField.alloc().initWithFrame_(NSMakeRect(playlist_field_x, y, 200, CONTROL_HEIGHT))
        self.pass_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.pass_field.setEditable_(True)
        self.pass_field.setSelectable_(True)
        self.pass_field.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.pass_field)
        
        # Remember Password checkbox
        self.remember_password_checkbox = NSButton.alloc().initWithFrame_(NSMakeRect(playlist_field_x + 210, y, 150, CONTROL_HEIGHT))
        self.remember_password_checkbox.setButtonType_(NSButtonTypeSwitch)
        self.remember_password_checkbox.setTitle_("Remember Password")
        self.remember_password_checkbox.setState_(False)
        self.remember_password_checkbox.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.remember_password_checkbox)

        # Listen Port
        y -= FIELD_Y_SPACING
        self.port_label = NSTextField.labelWithString_("Listen Port (optional):")
        self.port_label.setFrame_(NSMakeRect(PADDING, y, LABEL_WIDTH, CONTROL_HEIGHT))
        self.port_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.port_label)
        self.port_field = NSTextField.alloc().initWithFrame_(NSMakeRect(playlist_field_x, y, 100, CONTROL_HEIGHT))
        self.port_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.port_field.setPlaceholderString_("49998")
        self.port_field.setEditable_(True)
        self.port_field.setSelectable_(True)
        self.port_field.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.port_field)

        # Download Path
        y -= FIELD_Y_SPACING
        self.path_label = NSTextField.labelWithString_("Download Path:")
        self.path_label.setFrame_(NSMakeRect(PADDING, y, LABEL_WIDTH, CONTROL_HEIGHT))
        self.path_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.path_label)
        
        browse_button_width = 80
        path_field_width = view.frame().size.width - playlist_field_x - browse_button_width - PADDING - 10
        self.path_field = NSTextField.alloc().initWithFrame_(NSMakeRect(playlist_field_x, y, path_field_width, CONTROL_HEIGHT))
        self.path_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.path_field.setEditable_(True)
        self.path_field.setSelectable_(True)
        self.path_field.cell().setScrollable_(True)
        self.path_field.cell().setWraps_(False)
        self.path_field.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        view.addSubview_(self.path_field)
        
        browse_button_x = playlist_field_x + path_field_width + 10
        self.browse_button = NSButton.alloc().initWithFrame_(NSMakeRect(browse_button_x, y, browse_button_width, BUTTON_HEIGHT))
        self.browse_button.setTitle_("Browse")
        self.browse_button.setBezelStyle_(NSBezelStyleRounded)
        self.browse_button.setTarget_(self)
        self.browse_button.setAction_("browseDirectory:")
        self.browse_button.setAutoresizingMask_(NSViewMinXMargin | NSViewMinYMargin)
        view.addSubview_(self.browse_button)

        # --- Audio Format Section ---
        y -= SECTION_SPACING
        format_section_label = NSTextField.labelWithString_("Audio Format & Quality Criteria")
        format_section_label.setFrame_(NSMakeRect(PADDING, y, 300, CONTROL_HEIGHT))
        format_section_label.setFont_(objc.lookUpClass("NSFont").boldSystemFontOfSize_(13))
        format_section_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(format_section_label)

        y -= FIELD_Y_SPACING
        preferred_header = NSTextField.labelWithString_("Preferred (First Choice)")
        preferred_header.setFrame_(NSMakeRect(PADDING, y, 200, CONTROL_HEIGHT))
        preferred_header.setFont_(objc.lookUpClass("NSFont").boldSystemFontOfSize_(12))
        preferred_header.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(preferred_header)

        strict_header = NSTextField.labelWithString_("Strict (Requirements)")
        strict_header.setFrame_(NSMakeRect(350, y, 200, CONTROL_HEIGHT))
        strict_header.setFont_(objc.lookUpClass("NSFont").boldSystemFontOfSize_(12))
        strict_header.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(strict_header)

        y -= FIELD_Y_SPACING
        pref_format_label = NSTextField.labelWithString_("Format:")
        pref_format_label.setFrame_(NSMakeRect(PADDING, y, 60, CONTROL_HEIGHT))
        pref_format_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(pref_format_label)
        
        self.pref_format_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(80, y, 120, CONTROL_HEIGHT))
        self.pref_format_popup.addItemsWithTitles_([
            "Any", "mp3", "flac", "wav", "m4a", "aac", "ogg", "opus", 
            "wma", "ape", "alac", "aiff", "wv", "shn", "tak", "tta"
        ])
        self.pref_format_popup.selectItemWithTitle_("Any")
        self.pref_format_popup.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.pref_format_popup)

        strict_format_label = NSTextField.labelWithString_("Format:")
        strict_format_label.setFrame_(NSMakeRect(350, y, 60, CONTROL_HEIGHT))
        strict_format_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(strict_format_label)
        
        self.strict_format_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(410, y, 120, CONTROL_HEIGHT))
        self.strict_format_popup.addItemsWithTitles_([
            "Any", "mp3", "flac", "wav", "m4a", "aac", "ogg", "opus", 
            "wma", "ape", "alac", "aiff", "wv", "shn", "tak", "tta"
        ])
        self.strict_format_popup.selectItemWithTitle_("Any")
        self.strict_format_popup.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.strict_format_popup)

        y -= FIELD_Y_SPACING
        pref_min_bitrate_label = NSTextField.labelWithString_("Min Bitrate:")
        pref_min_bitrate_label.setFrame_(NSMakeRect(PADDING, y, 80, CONTROL_HEIGHT))
        pref_min_bitrate_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(pref_min_bitrate_label)
        
        self.pref_min_bitrate_field = NSTextField.alloc().initWithFrame_(NSMakeRect(100, y, 70, CONTROL_HEIGHT))
        self.pref_min_bitrate_field.setPlaceholderString_("200")
        self.pref_min_bitrate_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.pref_min_bitrate_field.setEditable_(True)
        self.pref_min_bitrate_field.setSelectable_(True)
        self.pref_min_bitrate_field.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.pref_min_bitrate_field)
        
        pref_kbps1 = NSTextField.labelWithString_("kbps")
        pref_kbps1.setFrame_(NSMakeRect(175, y, 35, CONTROL_HEIGHT))
        pref_kbps1.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(pref_kbps1)

        pref_max_bitrate_label = NSTextField.labelWithString_("Max:")
        pref_max_bitrate_label.setFrame_(NSMakeRect(220, y, 35, CONTROL_HEIGHT))
        pref_max_bitrate_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(pref_max_bitrate_label)
        
        self.pref_max_bitrate_field = NSTextField.alloc().initWithFrame_(NSMakeRect(255, y, 70, CONTROL_HEIGHT))
        self.pref_max_bitrate_field.setPlaceholderString_("2500")
        self.pref_max_bitrate_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.pref_max_bitrate_field.setEditable_(True)
        self.pref_max_bitrate_field.setSelectable_(True)
        self.pref_max_bitrate_field.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.pref_max_bitrate_field)

        strict_min_bitrate_label = NSTextField.labelWithString_("Min Bitrate:")
        strict_min_bitrate_label.setFrame_(NSMakeRect(350, y, 80, CONTROL_HEIGHT))
        strict_min_bitrate_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(strict_min_bitrate_label)
        
        self.strict_min_bitrate_field = NSTextField.alloc().initWithFrame_(NSMakeRect(430, y, 70, CONTROL_HEIGHT))
        self.strict_min_bitrate_field.setPlaceholderString_("128")
        self.strict_min_bitrate_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.strict_min_bitrate_field.setEditable_(True)
        self.strict_min_bitrate_field.setSelectable_(True)
        self.strict_min_bitrate_field.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.strict_min_bitrate_field)
        
        strict_kbps1 = NSTextField.labelWithString_("kbps")
        strict_kbps1.setFrame_(NSMakeRect(505, y, 35, CONTROL_HEIGHT))
        strict_kbps1.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(strict_kbps1)

        strict_max_bitrate_label = NSTextField.labelWithString_("Max:")
        strict_max_bitrate_label.setFrame_(NSMakeRect(550, y, 35, CONTROL_HEIGHT))
        strict_max_bitrate_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(strict_max_bitrate_label)
        
        self.strict_max_bitrate_field = NSTextField.alloc().initWithFrame_(NSMakeRect(585, y, 70, CONTROL_HEIGHT))
        self.strict_max_bitrate_field.setPlaceholderString_("320")
        self.strict_max_bitrate_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.strict_max_bitrate_field.setEditable_(True)
        self.strict_max_bitrate_field.setSelectable_(True)
        self.strict_max_bitrate_field.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.strict_max_bitrate_field)

        top_section_bottom_y = y - PADDING

        # --- Bottom-Up Layout ---
        y = PADDING

        # Status Label
        self.status_label = NSTextField.labelWithString_("Waiting for download to start...")
        status_label_width = view.frame().size.width - (PADDING * 2)
        self.status_label.setFrame_(NSMakeRect(PADDING, y, status_label_width, CONTROL_HEIGHT))
        self.status_label.setAutoresizingMask_(NSViewWidthSizable | NSViewMaxYMargin)
        view.addSubview_(self.status_label)
        
        y += CONTROL_HEIGHT + 10

        # Start Button, Stop Button, Help, and Progress Bar
        self.start_button = NSButton.alloc().initWithFrame_(NSMakeRect(PADDING, y, 150, START_BUTTON_HEIGHT))
        self.start_button.setTitle_("Start Download")
        self.start_button.setBezelStyle_(NSBezelStyleRounded)
        self.start_button.setKeyEquivalent_("\r")
        self.start_button.setTarget_(self)
        self.start_button.setAction_("startDownload:")
        self.start_button.setAutoresizingMask_(NSViewMaxXMargin | NSViewMaxYMargin)
        view.addSubview_(self.start_button)

        # Stop button (initially disabled)
        stop_button_x = PADDING + 150 + 10
        self.stop_button = NSButton.alloc().initWithFrame_(NSMakeRect(stop_button_x, y, 150, START_BUTTON_HEIGHT))
        self.stop_button.setTitle_("Stop Download")
        self.stop_button.setBezelStyle_(NSBezelStyleRounded)
        self.stop_button.setEnabled_(False)
        self.stop_button.setTarget_(self)
        self.stop_button.setAction_("stopDownload:")
        self.stop_button.setAutoresizingMask_(NSViewMaxXMargin | NSViewMaxYMargin)
        view.addSubview_(self.stop_button)

        help_button_x = stop_button_x + 150 + 10
        help_button = NSButton.alloc().initWithFrame_(NSMakeRect(help_button_x, y + 4, 120, BUTTON_HEIGHT))
        help_button.setTitle_("Show Help")
        help_button.setBezelStyle_(NSBezelStyleRounded)
        help_button.setTarget_(self)
        help_button.setAction_("showFormatHelp:")
        help_button.setAutoresizingMask_(NSViewMaxXMargin | NSViewMaxYMargin)
        view.addSubview_(help_button)

        progress_x = help_button_x + 120 + 20
        progress_width = view.frame().size.width - progress_x - PADDING
        self.progress = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(progress_x, y + 4, progress_width, 20))
        self.progress.setIndeterminate_(False)
        self.progress.setMinValue_(0)
        self.progress.setMaxValue_(100)
        self.progress.setDoubleValue_(0)
        self.progress.setAutoresizingMask_(NSViewWidthSizable | NSViewMaxYMargin)
        view.addSubview_(self.progress)
        
        bottom_section_top_y = y + START_BUTTON_HEIGHT

        # --- Middle Scroll View (fills the gap) ---
        scroll_y = bottom_section_top_y + PADDING
        scroll_height = top_section_bottom_y - scroll_y
        scroll_width = view.frame().size.width - (PADDING * 2)
        
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(PADDING, scroll_y, scroll_width, scroll_height))
        scroll.setHasVerticalScroller_(True)
        scroll.setHasHorizontalScroller_(False)
        scroll.setAutohidesScrollers_(True)
        scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        self.output_view = NSTextView.alloc().initWithFrame_(scroll.bounds())
        self.output_view.setEditable_(False)
        self.output_view.setSelectable_(True)

        font = objc.lookUpClass("NSFont").fontWithName_size_("Monaco", 12.0)
        if font is None:
            font = objc.lookUpClass("NSFont").systemFontOfSize_(12.0)

        self.output_view.setBackgroundColor_(NSColor.textBackgroundColor())
        attributes = {
            NSFontAttributeName: font,
            NSForegroundColorAttributeName: NSColor.labelColor()
        }
        self.output_view.setTypingAttributes_(attributes)
        self.output_view.setFont_(font)
        
        scroll.setDocumentView_(self.output_view)
        view.addSubview_(scroll)

        self.window.makeKeyAndOrderFront_(None)

    def showFormatHelp_(self, sender):
        """Show help dialog for format and quality settings."""
        help_text = """Audio Format & Quality Help

PREFERRED (First Choice):
These are your preferred settings. The downloader will try to find files matching these criteria first.

STRICT (Requirements):
These are hard requirements that must be met. Files that don't meet these criteria will be rejected.

FORMATS:
• Any: Accept any audio format
• mp3: MP3 files
• flac: FLAC lossless files
• wav: WAV files
• m4a: AAC in MP4 container
• aac: AAC files
• ogg: Ogg Vorbis files
• opus: Opus files
• wma: Windows Media Audio
• ape: Monkey's Audio
• alac: Apple Lossless
• aiff: AIFF files
• wv: WavPack files
• shn: Shorten files
• tak: TAK files
• tta: True Audio files

BITRATE:
• Min: Minimum acceptable bitrate in kbps
• Max: Maximum acceptable bitrate in kbps
• Leave empty to accept any bitrate

Example:
Preferred: FLAC, 1000-2500 kbps
Strict: MP3, 320 kbps
This means: Try to find FLAC files first, but accept MP3 files if they're at least 320 kbps."""
        
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Format & Quality Help")
        alert.setInformativeText_(help_text)
        alert.addButtonWithTitle_("OK")
        alert.runModal()

    def sourceChanged_(self, sender):
        """Handle source selection change between YouTube and Spotify."""
        selected_source = self.source_popup.titleOfSelectedItem()
        
        if selected_source == "YouTube Playlist":
            # Show YouTube fields, hide Spotify fields
            self.playlist_label.setHidden_(False)
            self.playlist_field.setHidden_(False)
            self.spotify_label.setHidden_(True)
            self.spotify_field.setHidden_(True)
        else:  # Spotify Playlist
            # Show Spotify fields, hide YouTube fields
            self.playlist_label.setHidden_(True)
            self.playlist_field.setHidden_(True)
            self.spotify_label.setHidden_(False)
            self.spotify_field.setHidden_(False)

    def appendOutput_(self, text):
        """Safely append text to the output view on the main thread."""
        if not isinstance(text, NSString):
            text = NSString.stringWithString_(str(text))
        
        # Use the theme-aware typing attributes set on the text view
        attributes = self.output_view.typingAttributes()
        attr_string = objc.lookUpClass("NSAttributedString").alloc().initWithString_attributes_(text, attributes)
        
        storage = self.output_view.textStorage()
        storage.appendAttributedString_(attr_string)
        
        # Scroll to bottom
        length = len(self.output_view.string())
        if length > 0:
            self.output_view.scrollRangeToVisible_((length, 0))

    def updateProgressAndStatus_(self, status_info):
        """Safely update progress bar and status label on the main thread."""
        current_step, message = status_info
        self.progress.setDoubleValue_(float(current_step))

        # Just show the message directly without step information
        self.status_label.setStringValue_(message)

    def switchToDeterminateProgress_(self, max_value):
        """Switch the progress bar to determinate mode with a max value."""
        self.progress.stopAnimation_(None)
        self.progress.setIndeterminate_(False)
        self.total_steps = int(float(max_value))
        self.progress.setMaxValue_(float(self.total_steps))
        self.progress.setDoubleValue_(0.0)
        self.status_label.setStringValue_(f"Found {self.total_steps} tracks")

    def resetProgressIndicator(self):
        """Reset the progress bar to its initial state."""
        self.progress.stopAnimation_(None)
        self.progress.setIndeterminate_(False)
        self.progress.setDoubleValue_(0)

    def updateStatusText_(self, text):
        """Safely update the status label on the main thread."""
        if not isinstance(text, NSString):
            text = NSString.stringWithString_(str(text))
        self.status_label.setStringValue_(text)

    def enableStartButton_(self, enabled):
        """Safely enable/disable start button on the main thread."""
        self.start_button.setEnabled_(bool(enabled))

    def enableStopButton_(self, enabled):
        """Safely enable/disable stop button on the main thread."""
        self.stop_button.setEnabled_(bool(enabled))

    def browseDirectory_(self, sender):
        """Handle browse button click."""
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(False)
        panel.setCanChooseDirectories_(True)
        panel.setAllowsMultipleSelection_(False)
        panel.setTitle_("Select Download Directory")
        
        if panel.runModal() == NSAlertFirstButtonReturn:
            url = panel.URL()
            if url:
                self.path_field.setStringValue_(url.path())

    def startDownload_(self, sender):
        """Handle start download button click."""
        # Validate inputs
        selected_source = self.source_popup.titleOfSelectedItem()
        
        if selected_source == "YouTube Playlist":
            playlist_url = self.playlist_field.stringValue().strip()
            if not playlist_url:
                self.showAlert_message_("Error", "Please enter a YouTube playlist URL.")
                return
            # Basic YouTube URL validation
            if not any(pattern in playlist_url.lower() for pattern in ['youtube.com', 'youtu.be']):
                self.showAlert_message_("Error", "Please enter a valid YouTube playlist URL.")
                return
        else:  # Spotify Playlist
            spotify_url = self.spotify_field.stringValue().strip()
            if not spotify_url:
                self.showAlert_message_("Error", "Please enter a Spotify playlist URL.")
                return
            # Basic Spotify URL validation
            if not any(pattern in spotify_url.lower() for pattern in ['spotify.com', 'open.spotify.com']):
                self.showAlert_message_("Error", "Please enter a valid Spotify playlist URL.")
                return
        
        username = self.user_field.stringValue().strip()
        password = self.pass_field.stringValue().strip()
        
        if not username:
            self.showAlert_message_("Error", "Please enter your Soulseek username.")
            return
        if not password:
            self.showAlert_message_("Error", "Please enter your Soulseek password.")
            return

        # Check if sldl is available
        try:
            subprocess.run([str(self.sldl_path), '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.showAlert_message_("Error", "sldl command not found. Please install slsk-batchdl first.")
            return

        # Disable the start button, enable stop button, and reset progress
        self.start_button.setEnabled_(False)
        self.stop_button.setEnabled_(True)
        self.download_running = True
        self.output_view.setString_("")
        self.total_steps = 0
        
        # Start indeterminate progress immediately
        self.progress.setIndeterminate_(True)
        self.progress.startAnimation_(None)
        self.status_label.setStringValue_("Starting...")
        
        # Start download in background thread
        thread = threading.Thread(target=self.downloadThread, daemon=True)
        thread.start()

    def stopDownload_(self, sender):
        """Handle stop download button click."""
        if self.current_process and self.download_running:
            try:
                # Terminate the process
                self.current_process.terminate()
                
                # Wait a bit for graceful termination
                try:
                    self.current_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    self.current_process.kill()
                    self.current_process.wait()
                
                # Update UI
                self.appendOutput_("🛑 Download stopped by user.\n")
                self.updateStatusText_("Download stopped")
                
            except Exception as e:
                self.appendOutput_(f"❌ Error stopping download: {str(e)}\n")
            finally:
                # Reset process reference and UI state
                self.current_process = None
                self.download_running = False
                self.start_button.setEnabled_(True)
                self.stop_button.setEnabled_(False)
                self.resetProgressIndicator()

    def downloadThread(self):
        """Run the download process in a background thread."""
        try:
            selected_source = self.source_popup.titleOfSelectedItem()
            
            if selected_source == "YouTube Playlist":
                playlist_url = self.playlist_field.stringValue().strip()
            else:  # Spotify Playlist
                playlist_url = self.spotify_field.stringValue().strip()
                
            username = self.user_field.stringValue().strip()
            password = self.pass_field.stringValue().strip()
            path = self.path_field.stringValue().strip()

            # Build base command
            cmd = [str(self.sldl_path), playlist_url, '--user', username, '--pass', password]
            if path:
                cmd.extend(['--path', path])

            port = self.port_field.stringValue().strip()
            if port and port.isdigit():
                cmd.extend(['--listen-port', port])

            # Add format/quality parameters
            # Preferred parameters
            pref_format = self.pref_format_popup.titleOfSelectedItem()
            if pref_format and pref_format != "Any":
                cmd.extend(['--pref-format', pref_format])

            pref_min_bitrate = self.pref_min_bitrate_field.stringValue().strip()
            if pref_min_bitrate and pref_min_bitrate.isdigit():
                cmd.extend(['--pref-min-bitrate', pref_min_bitrate])

            pref_max_bitrate = self.pref_max_bitrate_field.stringValue().strip()
            if pref_max_bitrate and pref_max_bitrate.isdigit():
                cmd.extend(['--pref-max-bitrate', pref_max_bitrate])

            # Strict parameters
            strict_format = self.strict_format_popup.titleOfSelectedItem()
            if strict_format and strict_format != "Any":
                cmd.extend(['--format', strict_format])

            strict_min_bitrate = self.strict_min_bitrate_field.stringValue().strip()
            if strict_min_bitrate and strict_min_bitrate.isdigit():
                cmd.extend(['--min-bitrate', strict_min_bitrate])

            strict_max_bitrate = self.strict_max_bitrate_field.stringValue().strip()
            if strict_max_bitrate and strict_max_bitrate.isdigit():
                cmd.extend(['--max-bitrate', strict_max_bitrate])

            # Show the command being executed
            cmd_str = " ".join(cmd).replace(password, "***")  # Hide password
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "appendOutput:", f"Executing: {cmd_str}\n\n", False
            )

            # Run the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Store process reference for stopping
            self.current_process = process

            total_tracks = 0
            succeeded_count = 0
            failed_count = 0
            searching_count = 0
            
            for line in process.stdout:
                # Check if download was stopped
                if not self.download_running:
                    break
                    
                # Update output on main thread
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", line, False
                )
                
                # --- Final progress logic based on user feedback ---
                
                # Update status based on various log messages
                if "Loading YouTube playlist" in line or "Loading Spotify playlist" in line:
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", "Loading playlist...", False)
                elif line.startswith("Login"):
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", "Logging in...", False)

                # Get total tracks and set the max progress bar value
                total_match = re.search(r'Downloading (\d+) tracks:', line)
                if total_match:
                    total_tracks = int(total_match.group(1))
                    if total_tracks > 0:
                        max_steps = float(total_tracks)
                        self.performSelectorOnMainThread_withObject_waitUntilDone_("switchToDeterminateProgress:", max_steps, False)
                    continue

                # --- Track successful downloads for progress ---
                if line.startswith("Searching:"):
                    searching_count += 1
                    # Don't update progress bar during searching phase
                    continue
                
                elif line.startswith("Succeeded:"):
                    succeeded_count += 1
                    # Update progress bar and status with successful downloads
                    if total_tracks > 0:
                        current_step = float(succeeded_count)
                        status_message = f"{succeeded_count}/{total_tracks} downloaded"
                        self.performSelectorOnMainThread_withObject_waitUntilDone_("updateProgressAndStatus:", (current_step, status_message), False)
                    continue

                elif line.startswith("All downloads failed:"):
                    failed_count += 1
                    # Don't update progress bar for failed downloads, just count them
                    continue
                
                # Get final completion summary from the log
                completed_match = re.search(r'Completed: (.*)', line)
                if completed_match:
                    summary = completed_match.group(1).strip()
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", f"Finished: {summary}", False)
                    continue

            # Wait for process to complete (only if not stopped)
            if self.download_running:
                return_code = process.wait()
            else:
                return_code = -1  # Indicate stopped by user
            
            # Reset the progress indicator state
            self.performSelectorOnMainThread_withObject_waitUntilDone_("resetProgressIndicator", None, False)

            # The progress bar's final state is now accurate. No need to force it.
            
            if return_code == -1:
                # Download was stopped by user
                self.performSelectorOnMainThread_withObject_waitUntilDone_("appendOutput:", "\n🛑 Download stopped by user.\n", False)
                self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", "Download stopped", False)
            elif return_code == 0:
                if failed_count == 0 and total_tracks > 0:
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("appendOutput:", "\n✅ Download completed successfully!\n", False)
                elif total_tracks > 0:
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("appendOutput:", f"\nℹ️ Download finished: {succeeded_count} succeeded, {failed_count} failed.\n", False)
                # Handle cases where no tracks were found
            else:
                self.performSelectorOnMainThread_withObject_waitUntilDone_("appendOutput:", f"\n❌ Download failed with code {return_code}\n", False)
                self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", "Download failed", False)

        except Exception as e:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "appendOutput:", f"\n❌ Error: {str(e)}\n", False
            )
            self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", "An error occurred", False)
        
        finally:
            # Reset process reference and UI state
            self.current_process = None
            self.download_running = False
            
            # Re-enable the start button and disable stop button
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "enableStartButton:", True, False
            )
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "enableStopButton:", False, False
            )
            
            # Save settings
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "saveSettings", None, False
            )

            # Run CSV processor in the same thread
            self.run_csv_processor()

    def showAlert_message_(self, title, message):
        """Show an alert dialog."""
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_("OK")
        alert.runModal()

    def loadSettings(self):
        """Load saved settings from file."""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                
                # Load source selection
                selected_source = data.get('selected_source', 'YouTube Playlist')
                self.source_popup.selectItemWithTitle_(selected_source)
                self.sourceChanged_(None)  # Update UI visibility
                
                # Load URLs
                self.playlist_field.setStringValue_(data.get('playlist_url', ''))
                self.spotify_field.setStringValue_(data.get('spotify_url', ''))
                
                self.user_field.setStringValue_(data.get('username', ''))
                self.path_field.setStringValue_(data.get('download_path', ''))
                
                # Load remember password checkbox state
                remember_password = data.get('remember_password', False)
                self.remember_password_checkbox.setState_(remember_password)
                
                # Only load password if remember password was checked
                if remember_password:
                    self.pass_field.setStringValue_(data.get('password', ''))
                
                # Load port
                self.port_field.setStringValue_(data.get('listen_port', ''))

                # Load format/quality settings
                if 'pref_format' in data:
                    self.pref_format_popup.selectItemWithTitle_(data['pref_format'])
                if 'strict_format' in data:
                    self.strict_format_popup.selectItemWithTitle_(data['strict_format'])
                if 'pref_min_bitrate' in data:
                    self.pref_min_bitrate_field.setStringValue_(str(data['pref_min_bitrate']))
                if 'pref_max_bitrate' in data:
                    self.pref_max_bitrate_field.setStringValue_(str(data['pref_max_bitrate']))
                if 'strict_min_bitrate' in data:
                    self.strict_min_bitrate_field.setStringValue_(str(data['strict_min_bitrate']))
                if 'strict_max_bitrate' in data:
                    self.strict_max_bitrate_field.setStringValue_(str(data['strict_max_bitrate']))
            except Exception:
                pass

    def load_settings(self):
        """Public method to load settings."""
        self.loadSettings()

    def saveSettings(self):
        """Save current settings to file."""
        remember_password = bool(self.remember_password_checkbox.state())
        
        data = {
            'selected_source': self.source_popup.titleOfSelectedItem(),
            'playlist_url': self.playlist_field.stringValue(),
            'spotify_url': self.spotify_field.stringValue(),
            'username': self.user_field.stringValue(),
            'download_path': self.path_field.stringValue(),
            'remember_password': remember_password,
            'listen_port': self.port_field.stringValue(),
            'pref_format': self.pref_format_popup.titleOfSelectedItem(),
            'strict_format': self.strict_format_popup.titleOfSelectedItem(),
            'pref_min_bitrate': self.pref_min_bitrate_field.stringValue(),
            'pref_max_bitrate': self.pref_max_bitrate_field.stringValue(),
            'strict_min_bitrate': self.strict_min_bitrate_field.stringValue(),
            'strict_max_bitrate': self.strict_max_bitrate_field.stringValue(),
        }
        
        # Only save password if remember password is checked
        if remember_password:
            data['password'] = self.pass_field.stringValue()
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def save_settings(self):
        """Public method to save settings."""
        self.saveSettings()

    def run_csv_processor(self):
        """Find the latest _index.csv and process it."""
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "updateStatusText:", "Processing CSV output...", False
        )

        try:
            download_path_str = self.path_field.stringValue().strip()
            if not download_path_str:
                download_path = Path.cwd()
            else:
                download_path = Path(download_path_str)

            if not download_path.is_dir():
                print(f"CSV processor: Download directory '{download_path}' not found.")
                return

            latest_csv = None
            latest_mtime = 0

            for csv_file in download_path.rglob('_index.csv'):
                try:
                    mtime = csv_file.stat().st_mtime
                    if mtime > latest_mtime:
                        latest_mtime = mtime
                        latest_csv = csv_file
                except FileNotFoundError:
                    continue

            if not latest_csv:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "updateStatusText:", "CSV to process not found", False
                )
                return

            processor = SLDLCSVProcessor()
            success = processor.process_csv_file(str(latest_csv))

            if success:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "updateStatusText:", "CSV processing complete.", False
                )
            else:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "updateStatusText:", "CSV processing failed.", False
                )

        except Exception as e:
            print(f"An error occurred during CSV processing: {e}")
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "updateStatusText:", "CSV processing error.", False
            )

    def outputToCSV_(self, sender):
        """Handle 'Output to .csv' menu item click."""
        # Get the current playlist URL
        selected_source = self.source_popup.titleOfSelectedItem()
        
        if selected_source == "YouTube Playlist":
            playlist_url = self.playlist_field.stringValue().strip()
            if not playlist_url:
                self.showAlert_message_("Error", "Please enter a YouTube playlist URL.")
                return
            # Basic YouTube URL validation
            if not any(pattern in playlist_url.lower() for pattern in ['youtube.com', 'youtu.be']):
                self.showAlert_message_("Error", "Please enter a valid YouTube playlist URL.")
                return
        else:  # Spotify Playlist
            playlist_url = self.spotify_field.stringValue().strip()
            if not playlist_url:
                self.showAlert_message_("Error", "Please enter a Spotify playlist URL.")
                return
            # Basic Spotify URL validation
            if not any(pattern in playlist_url.lower() for pattern in ['spotify.com', 'open.spotify.com']):
                self.showAlert_message_("Error", "Please enter a valid Spotify playlist URL.")
                return
        
        # Get target directory
        download_path_str = self.path_field.stringValue().strip()
        if not download_path_str:
            download_path = Path.cwd()
        else:
            download_path = Path(download_path_str)
        
        if not download_path.is_dir():
            self.showAlert_message_("Error", f"Target directory '{download_path}' does not exist.")
            return
        
        # Start the CSV export process in a background thread
        thread = threading.Thread(target=self.__exportPlaylistToCSV, args=(playlist_url, selected_source, download_path), daemon=True)
        thread.start()

    def __exportPlaylistToCSV(self, playlist_url, source_type, target_directory):
        """Export playlist to CSV file in background thread."""
        try:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "updateStatusText:", f"Exporting {source_type} to CSV...", False
            )
            
            # Generate filename based on source type and current timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            if source_type == "YouTube Playlist":
                filename = f"youtube_playlist_{timestamp}.csv"
            else:
                filename = f"spotify_playlist_{timestamp}.csv"
            
            csv_path = target_directory / filename
            
            # Use sldl for both YouTube and Spotify playlists
            if source_type == "YouTube Playlist":
                success = self.__exportYouTubePlaylistToCSV(playlist_url, csv_path)
            else:
                # Note: Spotify playlists may require authentication for private playlists
                success = self.__exportSpotifyPlaylistToCSV(playlist_url, csv_path)
            
            if success:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "updateStatusText:", f"CSV exported to: {csv_path}", False
                )
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", f"\n✅ CSV exported successfully to: {csv_path}\n", False
                )
            else:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "updateStatusText:", "CSV export failed", False
                )
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", f"\n❌ Failed to export CSV\n", False
                )
                
        except Exception as e:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "updateStatusText:", f"CSV export error: {str(e)}", False
            )
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "appendOutput:", f"\n❌ CSV export error: {str(e)}\n", False
            )

    def __exportYouTubePlaylistToCSV(self, playlist_url, csv_path):
        """Export YouTube playlist to CSV using sldl."""
        try:
            # Use sldl to get playlist tracks without downloading
            cmd = [str(self.sldl_path), playlist_url, '--print', 'tracks']
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse the output and create CSV
            import csv
            tracks = []
            
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # sldl output format: "Artist - Title (duration)"
                    # Example: "Yes Theory - I Explored A $200,000,000 Forgotten Space Colony (969s)"
                    if ' - ' in line and '(' in line and ')' in line:
                        # Extract artist and title
                        artist_title_part = line.split(' (')[0]
                        if ' - ' in artist_title_part:
                            artist, title = artist_title_part.split(' - ', 1)
                            
                            # Extract duration (remove 's' suffix and convert to MM:SS)
                            duration_match = re.search(r'\((\d+)s\)', line)
                            duration_formatted = ""
                            if duration_match:
                                duration_seconds = int(duration_match.group(1))
                                duration_minutes = duration_seconds // 60
                                duration_remaining_seconds = duration_seconds % 60
                                duration_formatted = f"{duration_minutes}:{duration_remaining_seconds:02d}"
                            
                            tracks.append({
                                'title': title.strip(),
                                'artist': artist.strip(),
                                'duration': duration_formatted,
                                'url': playlist_url,  # Use the playlist URL as the source
                                'uploader': artist.strip()  # Use artist as uploader
                            })
            
            # Write to CSV
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['title', 'artist', 'duration', 'url', 'uploader']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(tracks)
            
            return True
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "appendOutput:", f"❌ sldl error: {error_msg}\n", False
            )
            return False
        except Exception as e:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "appendOutput:", f"❌ YouTube export error: {str(e)}\n", False
            )
            return False

    def __exportSpotifyPlaylistToCSV(self, playlist_url, csv_path):
        """Export Spotify playlist to CSV using sldl."""
        try:
            # Use sldl to get playlist tracks without downloading
            cmd = [str(self.sldl_path), playlist_url, '--print', 'tracks']
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse the output and create CSV
            import csv
            tracks = []
            
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # sldl output format: "Artist - Title" or "Title - Artist"
                    # We'll parse this as best we can
                    if ' - ' in line:
                        parts = line.split(' - ', 1)
                        if len(parts) == 2:
                            # Try to determine which is artist and which is title
                            # This is a simple heuristic - could be improved
                            artist, title = parts[0].strip(), parts[1].strip()
                            
                            # Strip duration from title (e.g., "Song Name (148s)" -> "Song Name")
                            title_clean = re.sub(r'\s*\(\d+s\)$', '', title)
                            
                            tracks.append({
                                'title': title_clean,
                                'artist': artist,
                                'album': '',  # sldl doesn't provide album info in track listing
                                'duration': '',  # sldl doesn't provide duration in track listing
                                'url': playlist_url  # Use the playlist URL as the source
                            })
            
            # Write to CSV
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['title', 'artist', 'album', 'duration', 'url']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(tracks)
            
            return True
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            
            # Check for specific Spotify authentication errors
            if "not found" in error_msg.lower() and "private" in error_msg.lower():
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", "❌ Spotify playlist not found or is private. Spotify playlists require authentication.\n", False
                )
            elif "invalid_client" in error_msg.lower():
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", "❌ Spotify authentication failed. The playlist may be private or require valid credentials.\n", False
                )
            else:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", f"❌ sldl error: {error_msg}\n", False
                )
            return False
        except Exception as e:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "appendOutput:", f"❌ Spotify export error: {str(e)}\n", False
            )
            return False

    def check_for_updates_async(self):
        """Check for updates in a background thread to avoid blocking the UI."""
        def update_check_thread():
            latest_version = check_for_updates()
            if latest_version:
                # Show update alert on main thread
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "showUpdateAlert:", latest_version, False
                )
        
        # Start update check in background thread
        threading.Thread(target=update_check_thread, daemon=True).start()

    def showUpdateAlert_(self, latest_version):
        """Show update alert dialog on main thread."""
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Update Available")
        alert.setInformativeText_(f"You are using an old version ({APP_VERSION}). Run the install command again to update to the newest version ({latest_version}).")
        alert.addButtonWithTitle_("OK")
        alert.runModal()


def main():
    """Main application entry point."""
    try:
        app = NSApplication.sharedApplication()

        # Give the app a unique identifier to prevent saved state errors on quit.
        # This makes macOS treat it as a distinct app.
        bundle = objc.lookUpClass("NSBundle").mainBundle()
        info = bundle.infoDictionary()
        info["CFBundleIdentifier"] = "com.script.sldl-gui"

        delegate = AppDelegate.alloc().init()
        app.setDelegate_(delegate)
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        app.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
