#!/usr/bin/env python3
"""sldl-gui for macOS - PyObjC GUI version."""

import subprocess
import threading
import json
import sys
import re
import urllib.request
import urllib.error
import urllib.parse
import ssl
import datetime
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
        NSOpenPanel, NSSavePanel, NSObject, NSApplicationActivationPolicyRegular,
        NSString, NSAlert, NSAlertFirstButtonReturn, NSAlertSecondButtonReturn, NSModalResponseOK, NSPopUpButton,
        NSButtonTypeSwitch, NSMenu, NSMenuItem, NSColor,
        NSFontAttributeName, NSForegroundColorAttributeName,
        NSBezelStyleRounded, NSTextFieldRoundedBezel,
        NSViewWidthSizable, NSViewHeightSizable, NSViewMinXMargin,
        NSViewMaxXMargin, NSViewMinYMargin, NSViewMaxYMargin, NSThread
    )
except ImportError as e:
    print(f"Error importing PyObjC: {e}")
    print("Please install PyObjC with: pip install pyobjc-framework-Cocoa")
    sys.exit(1)

SETTINGS_FILE = Path.home() / ".soulseek_downloader_settings.json"
WISHLIST_FILE = Path.home() / ".soulseek_downloader_wishlist.csv"

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
        self.user_stopped = False
        self.download_target_dir = None

        
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
        
        # Create Bugs menu
        bugs_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Bugs", None, ""
        )
        main_menu.addItem_(bugs_menu_item)
        bugs_menu = NSMenu.alloc().initWithTitle_("Bugs")
        bugs_menu_item.setSubmenu_(bugs_menu)
        
        # Add Known bugs item
        known_bugs_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Known bugs", "showKnownBugs:", ""
        )
        bugs_menu.addItem_(known_bugs_item)
        
        # Add Report bug item
        report_bug_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Report bug", "reportBug:", ""
        )
        bugs_menu.addItem_(report_bug_item)
        
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
            NSMakeRect(100.0, 100.0, 750.0, 680.0),  # Increased height for wishlist controls
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
        SECTION_SPACING = 60
        
        # --- Top-Down Layout ---
        y = view.frame().size.height - PADDING

        # Source Selection and URL on same line
        y -= CONTROL_HEIGHT
        self.source_label = NSTextField.labelWithString_("Source:")
        self.source_label.setFrame_(NSMakeRect(PADDING, y, 60, CONTROL_HEIGHT))
        self.source_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.source_label)
        
        source_field_x = PADDING + 60
        self.source_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(source_field_x, y, 150, CONTROL_HEIGHT))
        self.source_popup.addItemsWithTitles_(["YouTube Playlist", "Spotify Playlist", "Wishlist", "CSV File"])
        self.source_popup.selectItemWithTitle_("YouTube Playlist")
        self.source_popup.setTarget_(self)
        self.source_popup.setAction_("sourceChanged:")
        self.source_popup.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.source_popup)

        # URL field on same line as source
        url_label_x = source_field_x + 160
        self.url_label = NSTextField.labelWithString_("URL:")
        self.url_label.setFrame_(NSMakeRect(url_label_x, y, 40, CONTROL_HEIGHT))
        self.url_label.setAutoresizingMask_(NSViewMinYMargin)
        self.url_label.setHidden_(True)  # Hide by default, will be shown only when needed
        view.addSubview_(self.url_label)
        
        url_field_x = url_label_x + 40
        url_field_width = view.frame().size.width - url_field_x - PADDING
        self.playlist_field = NSTextField.alloc().initWithFrame_(NSMakeRect(url_field_x, y, url_field_width, CONTROL_HEIGHT))
        self.playlist_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.playlist_field.setEditable_(True)
        self.playlist_field.setSelectable_(True)
        self.playlist_field.cell().setScrollable_(True)
        self.playlist_field.cell().setWraps_(False)
        self.playlist_field.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        self.playlist_field.setPlaceholderString_("https://www.youtube.com/playlist?list=...")
        view.addSubview_(self.playlist_field)

        # Spotify Playlist URL (initially hidden)
        self.spotify_label = NSTextField.labelWithString_("Spotify Playlist URL:")
        self.spotify_label.setFrame_(NSMakeRect(url_label_x, y, 40, CONTROL_HEIGHT))
        self.spotify_label.setAutoresizingMask_(NSViewMinYMargin)
        self.spotify_label.setHidden_(True)
        view.addSubview_(self.spotify_label)
        
        self.spotify_field = NSTextField.alloc().initWithFrame_(NSMakeRect(url_field_x, y, url_field_width, CONTROL_HEIGHT))
        self.spotify_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.spotify_field.setEditable_(True)
        self.spotify_field.setSelectable_(True)
        self.spotify_field.cell().setScrollable_(True)
        self.spotify_field.cell().setWraps_(False)
        self.spotify_field.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        self.spotify_field.setHidden_(True)
        self.spotify_field.setPlaceholderString_("https://open.spotify.com/playlist/...")
        view.addSubview_(self.spotify_field)

        # Wishlist File (initially hidden)
        self.wishlist_label = NSTextField.labelWithString_("Wishlist File:")
        self.wishlist_label.setFrame_(NSMakeRect(url_label_x, y, 40, CONTROL_HEIGHT))
        self.wishlist_label.setAutoresizingMask_(NSViewMinYMargin)
        self.wishlist_label.setHidden_(True)
        view.addSubview_(self.wishlist_label)
        
        self.wishlist_field = NSTextField.alloc().initWithFrame_(NSMakeRect(url_field_x, y, url_field_width, CONTROL_HEIGHT))
        self.wishlist_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.wishlist_field.setEditable_(True)
        self.wishlist_field.setSelectable_(True)
        self.wishlist_field.cell().setScrollable_(True)
        self.wishlist_field.cell().setWraps_(False)
        self.wishlist_field.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        self.wishlist_field.setHidden_(True)
        self.wishlist_field.setPlaceholderString_("~/sldl/wishlist.txt")
        view.addSubview_(self.wishlist_field)
        
        wishlist_browse_button_x = url_field_x + url_field_width + 10
        self.wishlist_browse_button = NSButton.alloc().initWithFrame_(NSMakeRect(wishlist_browse_button_x, y, 80, BUTTON_HEIGHT))
        self.wishlist_browse_button.setTitle_("Browse")
        self.wishlist_browse_button.setBezelStyle_(NSBezelStyleRounded)
        self.wishlist_browse_button.setTarget_(self)
        self.wishlist_browse_button.setAction_("browseWishlistFile:")
        self.wishlist_browse_button.setAutoresizingMask_(NSViewMinXMargin | NSViewMinYMargin)
        self.wishlist_browse_button.setHidden_(True)
        view.addSubview_(self.wishlist_browse_button)

        # CSV File (initially hidden)
        csv_field_width = url_field_width - 90  # Make room for browse button
        self.csv_field = NSTextField.alloc().initWithFrame_(NSMakeRect(url_field_x, y, csv_field_width, CONTROL_HEIGHT))
        self.csv_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.csv_field.setEditable_(True)
        self.csv_field.setSelectable_(True)
        self.csv_field.cell().setScrollable_(True)
        self.csv_field.cell().setWraps_(False)
        self.csv_field.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        self.csv_field.setHidden_(True)
        self.csv_field.setPlaceholderString_("Select a CSV file with artist and title columns")
        view.addSubview_(self.csv_field)
        
        csv_browse_button_x = url_field_x + csv_field_width + 10
        self.csv_browse_button = NSButton.alloc().initWithFrame_(NSMakeRect(csv_browse_button_x, y, 80, BUTTON_HEIGHT))
        self.csv_browse_button.setTitle_("Browse")
        self.csv_browse_button.setBezelStyle_(NSBezelStyleRounded)
        self.csv_browse_button.setTarget_(self)
        self.csv_browse_button.setAction_("browseCSVFile:")
        self.csv_browse_button.setAutoresizingMask_(NSViewMinXMargin | NSViewMinYMargin)
        self.csv_browse_button.setHidden_(True)
        view.addSubview_(self.csv_browse_button)

        # Soulseek Username, Password, and Remember Password on same line
        y -= FIELD_Y_SPACING
        self.user_label = NSTextField.labelWithString_("Username:")
        self.user_label.setFrame_(NSMakeRect(PADDING, y, 80, CONTROL_HEIGHT))
        self.user_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.user_label)
        self.user_field = NSTextField.alloc().initWithFrame_(NSMakeRect(PADDING + 80, y, 150, CONTROL_HEIGHT))
        self.user_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.user_field.setEditable_(True)
        self.user_field.setSelectable_(True)
        self.user_field.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.user_field)

        # Password field on same line
        pass_label_x = PADDING + 240
        self.pass_label = NSTextField.labelWithString_("Password:")
        self.pass_label.setFrame_(NSMakeRect(pass_label_x, y, 70, CONTROL_HEIGHT))
        self.pass_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.pass_label)
        self.pass_field = NSSecureTextField.alloc().initWithFrame_(NSMakeRect(pass_label_x + 70, y, 150, CONTROL_HEIGHT))
        self.pass_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.pass_field.setEditable_(True)
        self.pass_field.setSelectable_(True)
        self.pass_field.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.pass_field)
        
        # Remember Password checkbox on same line
        checkbox_x = pass_label_x + 230
        self.remember_password_checkbox = NSButton.alloc().initWithFrame_(NSMakeRect(checkbox_x, y, 150, CONTROL_HEIGHT))
        self.remember_password_checkbox.setButtonType_(NSButtonTypeSwitch)
        self.remember_password_checkbox.setTitle_("Remember Password")
        self.remember_password_checkbox.setState_(False)
        self.remember_password_checkbox.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.remember_password_checkbox)

        # Listen Port
        y -= FIELD_Y_SPACING
        self.port_label = NSTextField.labelWithString_("Listen Port (optional):")
        self.port_label.setFrame_(NSMakeRect(PADDING, y, 140, CONTROL_HEIGHT))
        self.port_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.port_label)
        self.port_field = NSTextField.alloc().initWithFrame_(NSMakeRect(PADDING + 150, y, 100, CONTROL_HEIGHT))
        self.port_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.port_field.setPlaceholderString_("49998")
        self.port_field.setEditable_(True)
        self.port_field.setSelectable_(True)
        self.port_field.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.port_field)

        # Concurrent Downloads
        y -= FIELD_Y_SPACING
        self.concurrent_label = NSTextField.labelWithString_("Concurrent Downloads:")
        self.concurrent_label.setFrame_(NSMakeRect(PADDING, y, 140, CONTROL_HEIGHT))
        self.concurrent_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.concurrent_label)
        self.concurrent_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(PADDING + 150, y, 100, CONTROL_HEIGHT))
        self.concurrent_popup.addItemsWithTitles_(["1", "2", "3", "4"])
        self.concurrent_popup.selectItemWithTitle_("2")  # Default to 2
        self.concurrent_popup.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.concurrent_popup)

        # Download Path
        y -= FIELD_Y_SPACING
        self.path_label = NSTextField.labelWithString_("Download Path:")
        self.path_label.setFrame_(NSMakeRect(PADDING, y, 140, CONTROL_HEIGHT))
        self.path_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.path_label)
        
        browse_button_width = 80
        path_field_width = view.frame().size.width - (PADDING + 150) - browse_button_width - PADDING - 10
        self.path_field = NSTextField.alloc().initWithFrame_(NSMakeRect(PADDING + 150, y, path_field_width, CONTROL_HEIGHT))
        self.path_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.path_field.setEditable_(True)
        self.path_field.setSelectable_(True)
        self.path_field.cell().setScrollable_(True)
        self.path_field.cell().setWraps_(False)
        self.path_field.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        view.addSubview_(self.path_field)
        
        browse_button_x = (PADDING + 150) + path_field_width + 10
        self.browse_button = NSButton.alloc().initWithFrame_(NSMakeRect(browse_button_x, y, browse_button_width, BUTTON_HEIGHT))
        self.browse_button.setTitle_("Browse")
        self.browse_button.setBezelStyle_(NSBezelStyleRounded)
        self.browse_button.setTarget_(self)
        self.browse_button.setAction_("browseDirectory:")
        self.browse_button.setAutoresizingMask_(NSViewMinXMargin | NSViewMinYMargin)
        view.addSubview_(self.browse_button)

        # --- Wishlist Management Section ---
        y -= SECTION_SPACING
        wishlist_section_label = NSTextField.labelWithString_("Wishlist Management")
        wishlist_section_label.setFrame_(NSMakeRect(PADDING, y, 200, CONTROL_HEIGHT))
        wishlist_section_label.setFont_(objc.lookUpClass("NSFont").systemFontOfSize_(13))
        wishlist_section_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(wishlist_section_label)

        y -= FIELD_Y_SPACING
        # Wishlist Mode checkbox
        self.wishlist_mode_checkbox = NSButton.alloc().initWithFrame_(NSMakeRect(PADDING, y, 150, CONTROL_HEIGHT))
        self.wishlist_mode_checkbox.setButtonType_(NSButtonTypeSwitch)
        self.wishlist_mode_checkbox.setTitle_("Wishlist Mode")
        self.wishlist_mode_checkbox.setState_(False)
        self.wishlist_mode_checkbox.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.wishlist_mode_checkbox)

        # View Wishlist button
        view_wishlist_x = PADDING + 150
        self.view_wishlist_button = NSButton.alloc().initWithFrame_(NSMakeRect(view_wishlist_x, y, 100, BUTTON_HEIGHT))
        self.view_wishlist_button.setTitle_("View")
        self.view_wishlist_button.setBezelStyle_(NSBezelStyleRounded)
        self.view_wishlist_button.setTarget_(self)
        self.view_wishlist_button.setAction_("viewWishlist:")
        self.view_wishlist_button.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.view_wishlist_button)

        # Import Wishlist button
        import_wishlist_x = view_wishlist_x + 110
        self.import_wishlist_button = NSButton.alloc().initWithFrame_(NSMakeRect(import_wishlist_x, y, 100, BUTTON_HEIGHT))
        self.import_wishlist_button.setTitle_("Import")
        self.import_wishlist_button.setBezelStyle_(NSBezelStyleRounded)
        self.import_wishlist_button.setTarget_(self)
        self.import_wishlist_button.setAction_("importWishlist:")
        self.import_wishlist_button.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.import_wishlist_button)

        # Export Wishlist button
        export_wishlist_x = import_wishlist_x + 110
        self.export_wishlist_button = NSButton.alloc().initWithFrame_(NSMakeRect(export_wishlist_x, y, 100, BUTTON_HEIGHT))
        self.export_wishlist_button.setTitle_("Export")
        self.export_wishlist_button.setBezelStyle_(NSBezelStyleRounded)
        self.export_wishlist_button.setTarget_(self)
        self.export_wishlist_button.setAction_("exportWishlist:")
        self.export_wishlist_button.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.export_wishlist_button)

        # Clear Wishlist button
        clear_wishlist_x = export_wishlist_x + 110
        self.clear_wishlist_button = NSButton.alloc().initWithFrame_(NSMakeRect(clear_wishlist_x, y, 100, BUTTON_HEIGHT))
        self.clear_wishlist_button.setTitle_("Clear")
        self.clear_wishlist_button.setBezelStyle_(NSBezelStyleRounded)
        self.clear_wishlist_button.setTarget_(self)
        self.clear_wishlist_button.setAction_("clearWishlist:")
        self.clear_wishlist_button.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(self.clear_wishlist_button)

        # --- Audio Format Section ---
        y -= SECTION_SPACING
        format_section_label = NSTextField.labelWithString_("Audio Format & Quality Criteria")
        format_section_label.setFrame_(NSMakeRect(PADDING, y, 300, CONTROL_HEIGHT))
        format_section_label.setFont_(objc.lookUpClass("NSFont").systemFontOfSize_(13))
        format_section_label.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(format_section_label)

        y -= FIELD_Y_SPACING
        preferred_header = NSTextField.labelWithString_("Preferred")
        preferred_header.setFrame_(NSMakeRect(PADDING, y, 200, CONTROL_HEIGHT))
        preferred_header.setFont_(objc.lookUpClass("NSFont").systemFontOfSize_(13))
        preferred_header.setAutoresizingMask_(NSViewMinYMargin)
        view.addSubview_(preferred_header)

        strict_header = NSTextField.labelWithString_("Mandatory")
        strict_header.setFrame_(NSMakeRect(350, y, 200, CONTROL_HEIGHT))
        strict_header.setFont_(objc.lookUpClass("NSFont").systemFontOfSize_(13))
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
        help_button.setTitle_("Guides")
        help_button.setBezelStyle_(NSBezelStyleRounded)
        help_button.setTarget_(self)
        help_button.setAction_("showGuides:")
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

    def showGuides_(self, sender):
        """Open guides file in the user's default text editor."""
        import os
        import subprocess
        
        try:
            # Get the script directory and guides file path
            script_dir = os.path.dirname(os.path.abspath(__file__))
            guides_path = os.path.join(script_dir, "guides.txt")
            
            # Always try to fetch the latest version from GitHub first
            import urllib.request
            import urllib.error
            
            guides_url = "https://raw.githubusercontent.com/felixb/sldl-gui-macos/main/guides.txt"
            
            try:
                # Fetch guides from GitHub
                with urllib.request.urlopen(guides_url) as response:
                    guides_text = response.read().decode('utf-8')
                
                # Save to local file (overwrite if exists)
                with open(guides_path, 'w', encoding='utf-8') as f:
                    f.write(guides_text)
                
                # Open the downloaded file
                subprocess.run(["open", guides_path], check=True)
                
            except (urllib.error.URLError, Exception) as e:
                # If GitHub fails, try to use local file if it exists
                if os.path.exists(guides_path):
                    subprocess.run(["open", guides_path], check=True)
                else:
                    # Show error if both GitHub and local file fail
                    self.showAlert_message_("Error", f"Unable to load guides: {str(e)}\n\nPlease check your internet connection or visit the GitHub repository.")
                    
        except subprocess.CalledProcessError as e:
            self.showAlert_message_("Error", f"Failed to open guides file: {str(e)}")
        except Exception as e:
            self.showAlert_message_("Error", f"Unexpected error: {str(e)}")

    def showKnownBugs_(self, sender):
        """Open bugs-to-fix.txt file in the user's default text editor."""
        import os
        import subprocess
        
        try:
            # Get the script directory and bugs file path
            script_dir = os.path.dirname(os.path.abspath(__file__))
            bugs_path = os.path.join(script_dir, "bugs-to-fix.txt")
            
            # Always try to fetch the latest version from GitHub first
            import urllib.request
            import urllib.error
            
            bugs_url = "https://raw.githubusercontent.com/felixb/sldl-gui-macos/main/bugs-to-fix.txt"
            
            try:
                # Fetch bugs from GitHub
                with urllib.request.urlopen(bugs_url) as response:
                    bugs_text = response.read().decode('utf-8')
                
                # Save to local file (overwrite if exists)
                with open(bugs_path, 'w', encoding='utf-8') as f:
                    f.write(bugs_text)
                
                # Open the downloaded file
                subprocess.run(["open", bugs_path], check=True)
                
            except (urllib.error.URLError, Exception) as e:
                # If GitHub fails, try to use local file if it exists
                if os.path.exists(bugs_path):
                    subprocess.run(["open", bugs_path], check=True)
                else:
                    # Show error if both GitHub and local file fail
                    self.showAlert_message_("Error", f"Unable to load bugs file: {str(e)}\n\nPlease check your internet connection or visit the GitHub repository.")
                    
        except subprocess.CalledProcessError as e:
            self.showAlert_message_("Error", f"Failed to open bugs file: {str(e)}")
        except Exception as e:
            self.showAlert_message_("Error", f"Unexpected error: {str(e)}")

    def reportBug_(self, sender):
        """Open user's email client with pre-populated bug report fields."""
        import subprocess
        import platform
        import datetime
        
        try:
            # Get current date/time
            now = datetime.datetime.now()
            date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
            
            # Get system information
            system_info = platform.system()
            system_version = platform.mac_ver()[0] if system_info == "Darwin" else platform.platform()
            
            # Create email content
            subject = f"Bug report {date_time_str}"
            body = f"""[Your system]
{system_info} {system_version}

[Your version]
{APP_VERSION}

Please write your description here and add screenshots

"""
            
            # Create mailto URL
            mailto_url = f"mailto:a@whorl.cc?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
            
            # Open default email client
            subprocess.run(["open", mailto_url], check=True)
            
        except subprocess.CalledProcessError as e:
            self.showAlert_message_("Error", f"Failed to open email client: {str(e)}")
        except Exception as e:
            self.showAlert_message_("Error", f"Unexpected error: {str(e)}")

    def sourceChanged_(self, sender):
        """Handle source selection change between YouTube, Spotify, Wishlist, and CSV File."""
        selected_source = self.source_popup.titleOfSelectedItem()
        
        # Calculate positions
        source_field_x = 20 + 60  # PADDING + source label width
        direct_field_x = source_field_x + 160  # Position after source dropdown
        label_field_x = direct_field_x + 40   # Position after label (original)
        
        if selected_source == "YouTube Playlist":
            # Show YouTube fields, hide others
            self.url_label.setHidden_(True)  # Hide URL label since placeholder serves purpose
            self.playlist_field.setHidden_(False)
            # Reposition field to eliminate gap
            self.playlist_field.setFrame_(NSMakeRect(direct_field_x, self.playlist_field.frame().origin.y, 
                                                    self.window.contentView().frame().size.width - direct_field_x - 20, 24))
            self.spotify_label.setHidden_(True)
            self.spotify_field.setHidden_(True)
            self.wishlist_label.setHidden_(True)
            self.wishlist_field.setHidden_(True)
            self.wishlist_browse_button.setHidden_(True)
            self.csv_field.setHidden_(True)
            self.csv_browse_button.setHidden_(True)
        elif selected_source == "Spotify Playlist":
            # Show Spotify fields, hide others
            self.url_label.setHidden_(True)
            self.playlist_field.setHidden_(True)
            self.spotify_label.setHidden_(True)  # Hide Spotify label since placeholder serves purpose
            self.spotify_field.setHidden_(False)
            # Reposition field to eliminate gap
            self.spotify_field.setFrame_(NSMakeRect(direct_field_x, self.spotify_field.frame().origin.y, 
                                                   self.window.contentView().frame().size.width - direct_field_x - 20, 24))
            self.wishlist_label.setHidden_(True)
            self.wishlist_field.setHidden_(True)
            self.wishlist_browse_button.setHidden_(True)
            self.csv_field.setHidden_(True)
            self.csv_browse_button.setHidden_(True)
        elif selected_source == "CSV File":
            # Show CSV fields, hide others
            self.url_label.setHidden_(True)
            self.playlist_field.setHidden_(True)
            self.spotify_label.setHidden_(True)
            self.spotify_field.setHidden_(True)
            self.wishlist_label.setHidden_(True)
            self.wishlist_field.setHidden_(True)
            self.wishlist_browse_button.setHidden_(True)
            self.csv_field.setHidden_(False)
            self.csv_browse_button.setHidden_(False)
            # Reposition CSV field to eliminate gap
            csv_field_width = self.window.contentView().frame().size.width - direct_field_x - 20 - 90  # Make room for browse button
            self.csv_field.setFrame_(NSMakeRect(direct_field_x, self.csv_field.frame().origin.y, csv_field_width, 24))
            # Reposition browse button
            csv_browse_button_x = direct_field_x + csv_field_width + 10
            self.csv_browse_button.setFrame_(NSMakeRect(csv_browse_button_x, self.csv_browse_button.frame().origin.y, 80, 24))
        else:  # Wishlist
            # Hide all input fields for wishlist since we use internal wishlist
            self.url_label.setHidden_(True)
            self.playlist_field.setHidden_(True)
            self.spotify_label.setHidden_(True)
            self.spotify_field.setHidden_(True)
            self.wishlist_label.setHidden_(True)
            self.wishlist_field.setHidden_(True)
            self.wishlist_browse_button.setHidden_(True)
            self.csv_field.setHidden_(True)
            self.csv_browse_button.setHidden_(True)

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
        """Handle browse button click with New Folder option."""
        # Use the most reliable approach for directory selection
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(False)
        panel.setCanChooseDirectories_(True)
        panel.setAllowsMultipleSelection_(False)
        panel.setTitle_("Select Download Directory")
        panel.setCanCreateDirectories_(True)
        
        # Run modally - this blocks until user makes a choice
        result = panel.runModal()
        
        if result == NSModalResponseOK:
            urls = panel.URLs()
            
            if urls and len(urls) > 0:
                folder_path = urls[0].path()
                self.path_field.setStringValue_(folder_path)

    def browseWishlistFile_(self, sender):
        """Open file browser for wishlist file."""
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setTitle_("Select Wishlist File")
        panel.setAllowedFileTypes_(["txt"])
        
        if panel.runModal() == NSAlertFirstButtonReturn:
            url = panel.URL()
            if url:
                self.wishlist_field.setStringValue_(url.path())

    def browseCSVFile_(self, sender):
        """Open file browser for CSV file."""
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setTitle_("Select CSV File")
        panel.setAllowedFileTypes_(["csv"])
        
        if panel.runModal() == NSModalResponseOK:
            url = panel.URL()
            if url:
                self.csv_field.setStringValue_(url.path())

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
        elif selected_source == "Spotify Playlist":
            spotify_url = self.spotify_field.stringValue().strip()
            if not spotify_url:
                self.showAlert_message_("Error", "Please enter a Spotify playlist URL.")
                return
            # Basic Spotify URL validation
            if not any(pattern in spotify_url.lower() for pattern in ['spotify.com', 'open.spotify.com']):
                self.showAlert_message_("Error", "Please enter a valid Spotify playlist URL.")
                return
        elif selected_source == "CSV File":
            csv_path = self.csv_field.stringValue().strip()
            if not csv_path:
                self.showAlert_message_("Error", "Please select a CSV file.")
                return
            # Check if file exists
            if not Path(csv_path).exists():
                self.showAlert_message_("Error", "The selected CSV file does not exist.")
                return
            # Validate CSV format
            try:
                import csv
                with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    if not reader.fieldnames:
                        self.showAlert_message_("Error", "The CSV file appears to be empty or invalid.")
                        return
                    # Check if it has the required columns (artist and title, or track)
                    has_artist_title = 'artist' in reader.fieldnames and 'title' in reader.fieldnames
                    has_track = 'track' in reader.fieldnames
                    if not (has_artist_title or has_track):
                        self.showAlert_message_("Error", "The CSV file must have either 'artist' and 'title' columns, or a 'track' column.")
                        return
            except Exception as e:
                self.showAlert_message_("Error", f"Failed to read CSV file: {str(e)}")
                return
        else:  # Wishlist
            # Check if internal wishlist has items
            wishlist_items = self.__loadWishlistItems()
            if not wishlist_items:
                self.showAlert_message_("Error", "Your wishlist is empty. Please add some tracks to your wishlist first.")
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
        self.user_stopped = False
        
        # Set download target directory
        path_str = self.path_field.stringValue().strip()
        if path_str:
            self.download_target_dir = Path(path_str).expanduser()
        else:
            self.download_target_dir = Path.cwd()  # Use current working directory if no path specified

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
            self.user_stopped = True  # Mark that the user initiated the stop
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
                
            except Exception as e:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", f"❌ Error stopping download: {str(e)}\n", False
                )
            finally:
                # UI updates are now handled in the downloadThread's finally block
                self.download_running = False
                self.stop_button.setEnabled_(False)

    def downloadThread(self):
        """Run the download process in a background thread."""
        try:
            selected_source = self.source_popup.titleOfSelectedItem()
            username = self.user_field.stringValue().strip()
            password = self.pass_field.stringValue().strip()
            path = self.path_field.stringValue().strip()
            
            # Generate timestamp for folder naming
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if selected_source == "YouTube Playlist":
                input_source = self.playlist_field.stringValue().strip()
                # Build base command for YouTube
                cmd = [str(self.sldl_path), input_source, '--user', username, '--pass', password]
                if path:
                    cmd.extend(['--path', path])
            elif selected_source == "Spotify Playlist":
                input_source = self.spotify_field.stringValue().strip()
                # Build base command for Spotify
                cmd = [str(self.sldl_path), input_source, '--user', username, '--pass', password]
                if path:
                    cmd.extend(['--path', path])
            elif selected_source == "CSV File":
                # Create temporary wishlist file from CSV in sldl format
                temp_wishlist_file = self.__createSldlWishlistFileFromCSV()
                if not temp_wishlist_file:
                    self.performSelectorOnMainThread_withObject_waitUntilDone_(
                        "appendOutput:", "❌ Failed to create wishlist file from CSV for sldl.\n", False
                    )
                    return
                
                input_source = temp_wishlist_file
                # Build base command for CSV with input-type parameter (same as wishlist)
                cmd = [str(self.sldl_path), input_source, '--input-type', 'list', '--user', username, '--pass', password]
                if path:
                    # Create custom folder name for CSV: csv_YYYYMMDD_HHMMSS
                    csv_folder = Path(path) / f"csv_{timestamp}"
                    cmd.extend(['--path', str(csv_folder)])
                else:
                    # If no path specified, create in current directory
                    csv_folder = Path.cwd() / f"csv_{timestamp}"
                    cmd.extend(['--path', str(csv_folder)])
            else:  # Wishlist
                # Create temporary wishlist file in sldl format
                temp_wishlist_file = self.__createSldlWishlistFile()
                if not temp_wishlist_file:
                    self.performSelectorOnMainThread_withObject_waitUntilDone_(
                        "appendOutput:", "❌ Failed to create wishlist file for sldl.\n", False
                    )
                    return
                
                input_source = temp_wishlist_file
                # Build base command for wishlist with input-type parameter
                cmd = [str(self.sldl_path), input_source, '--input-type', 'list', '--user', username, '--pass', password]
                if path:
                    # Create custom folder name for wishlist: wishlist_YYYYMMDD_HHMMSS
                    wishlist_folder = Path(path) / f"wishlist_{timestamp}"
                    cmd.extend(['--path', str(wishlist_folder)])
                else:
                    # If no path specified, create in current directory
                    wishlist_folder = Path.cwd() / f"wishlist_{timestamp}"
                    cmd.extend(['--path', str(wishlist_folder)])

            port = self.port_field.stringValue().strip()
            if port and port.isdigit():
                cmd.extend(['--listen-port', port])

            # Add concurrent downloads parameter
            concurrent_downloads = self.concurrent_popup.titleOfSelectedItem()
            if concurrent_downloads:
                cmd.extend(['--concurrent-downloads', concurrent_downloads])

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
            
            # Store temp file for cleanup (if wishlist source)
            temp_file_to_cleanup = None
            initial_total_tracks = 0
            if selected_source == "Wishlist":
                temp_file_to_cleanup = input_source
                # For wishlist, we can estimate total tracks from wishlist items
                try:
                    wishlist_items = self.__loadWishlistItems()
                    initial_total_tracks = len(wishlist_items)
                    if initial_total_tracks > 0:
                        # Set initial progress for wishlist
                        self.performSelectorOnMainThread_withObject_waitUntilDone_("switchToDeterminateProgress:", float(initial_total_tracks), False)
                        self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", f"Processing {initial_total_tracks} wishlist items...", False)
                except:
                    pass  # Fall back to dynamic detection
            elif selected_source == "CSV File":
                temp_file_to_cleanup = input_source
                # For CSV file, we can estimate total tracks from CSV items
                try:
                    csv_path = self.csv_field.stringValue().strip()
                    import csv
                    csv_items = []
                    with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            if 'title' in row and 'artist' in row and row['artist'] and row['title']:
                                csv_items.append(f"{row['artist']} - {row['title']}")
                            elif 'track' in row and row['track']:
                                csv_items.append(row['track'])
                    initial_total_tracks = len(csv_items)
                    if initial_total_tracks > 0:
                        # Set initial progress for CSV file
                        self.performSelectorOnMainThread_withObject_waitUntilDone_("switchToDeterminateProgress:", float(initial_total_tracks), False)
                        self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", f"Processing {initial_total_tracks} CSV items...", False)
                except:
                    pass  # Fall back to dynamic detection

            total_tracks = initial_total_tracks
            succeeded_count = 0
            failed_count = 0
            searching_count = 0
            
            for line in process.stdout:
                # Check if download was stopped
                if not self.download_running:
                    break
                    
                # Filter out verbose logs that aren't useful to the user
                # Skip very verbose download-related logs that clutter the output
                if (line.startswith("Downloading") and "tracks:" not in line) or \
                   line.strip() == "":
                    # Still count these for progress tracking but don't display them
                    pass
                else:
                    # Update output on main thread for important messages
                    self.performSelectorOnMainThread_withObject_waitUntilDone_(
                        "appendOutput:", line, False
                    )
                
                # --- Final progress logic based on user feedback ---
                
                # Update status based on various log messages
                if "Loading YouTube playlist" in line or "Loading Spotify playlist" in line:
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", "Loading playlist...", False)
                elif line.startswith("Login"):
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", "Logging in...", False)
                elif selected_source == "Wishlist" and "Loading" in line:
                    # For wishlist, show loading status when processing the list
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", "Loading wishlist...", False)
                elif selected_source == "CSV File" and "Processing" in line:
                    # For CSV file, show processing status
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", "Processing CSV items...", False)

                # Get total tracks and set the max progress bar value
                # Handle both playlist and wishlist formats
                total_match = re.search(r'Downloading (\d+) tracks:', line)
                if total_match:
                    total_tracks = int(total_match.group(1))
                    if total_tracks > 0:
                        max_steps = float(total_tracks)
                        self.performSelectorOnMainThread_withObject_waitUntilDone_("switchToDeterminateProgress:", max_steps, False)
                    continue
                
                # For wishlist, if we haven't found total tracks yet, try to estimate from wishlist items
                if selected_source == "Wishlist" and total_tracks == 0:
                    # Try to get total tracks from wishlist processing messages
                    wishlist_total_match = re.search(r'Processing (\d+) items', line)
                    if wishlist_total_match:
                        total_tracks = int(wishlist_total_match.group(1))
                        if total_tracks > 0:
                            max_steps = float(total_tracks)
                            self.performSelectorOnMainThread_withObject_waitUntilDone_("switchToDeterminateProgress:", max_steps, False)
                        continue

                # --- Track successful downloads for progress ---
                if line.startswith("Searching:"):
                    searching_count += 1
                    # Don't update progress bar during searching phase
                    continue
                elif (selected_source == "Wishlist" or selected_source == "CSV File") and "Searching for" in line:
                    # For wishlist and CSV file, show when we start searching for individual items
                    if total_tracks > 0:
                        current_step = float(searching_count + 1)
                        status_message = f"Searching item {searching_count + 1}/{total_tracks}"
                        self.performSelectorOnMainThread_withObject_waitUntilDone_("updateProgressAndStatus:", (current_step, status_message), False)
                    searching_count += 1
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
            
            if return_code == -1 or self.user_stopped:
                # Download was stopped by user
                self.performSelectorOnMainThread_withObject_waitUntilDone_("appendOutput:", "\n🛑 User stopped download.\n", False)
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
            
            # Clean up temporary wishlist file if it exists
            if 'temp_file_to_cleanup' in locals() and temp_file_to_cleanup:
                try:
                    import os
                    os.unlink(temp_file_to_cleanup)
                except Exception as e:
                    print(f"Error cleaning up temp file: {e}")
            
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

            # Handle CSV processing and stopped download logic
            if self.user_stopped:
                # For stopped downloads: process CSV first, then append missing tracks
                self.run_csv_processor()
                self.generate_manual_index_file()
            else:
                # For normal downloads: just process CSV
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
                if selected_source in ["YouTube Playlist", "Spotify Playlist", "Wishlist", "CSV File"]:
                    self.source_popup.selectItemWithTitle_(selected_source)
                    self.sourceChanged_(None)  # Update UI visibility
                
                # Load URLs
                self.playlist_field.setStringValue_(data.get('playlist_url', ''))
                self.spotify_field.setStringValue_(data.get('spotify_url', ''))
                self.csv_field.setStringValue_(data.get('csv_file_path', ''))
                
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
                
                # Load concurrent downloads
                concurrent_downloads = data.get('concurrent_downloads', '2')
                if concurrent_downloads in ["1", "2", "3", "4"]:
                    self.concurrent_popup.selectItemWithTitle_(concurrent_downloads)

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
                
                # Load wishlist mode
                wishlist_mode = data.get('wishlist_mode', False)
                self.wishlist_mode_checkbox.setState_(wishlist_mode)
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
            'csv_file_path': self.csv_field.stringValue(),
            'username': self.user_field.stringValue(),
            'download_path': self.path_field.stringValue(),
            'remember_password': remember_password,
            'listen_port': self.port_field.stringValue(),
            'concurrent_downloads': self.concurrent_popup.titleOfSelectedItem(),
            'pref_format': self.pref_format_popup.titleOfSelectedItem(),
            'strict_format': self.strict_format_popup.titleOfSelectedItem(),
            'pref_min_bitrate': self.pref_min_bitrate_field.stringValue(),
            'pref_max_bitrate': self.pref_max_bitrate_field.stringValue(),
            'strict_min_bitrate': self.strict_min_bitrate_field.stringValue(),
            'strict_max_bitrate': self.strict_max_bitrate_field.stringValue(),
            'wishlist_mode': bool(self.wishlist_mode_checkbox.state()),
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

            # Find the most recent sldl index file
            index_files = list(download_path.rglob("_index.csv"))
            if not index_files:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "updateStatusText:", "CSV to process not found", False
                )
                return
            
            # Use the most recent one
            index_file = max(index_files, key=lambda f: f.stat().st_mtime)

            processor = SLDLCSVProcessor()
            success = processor.process_csv_file(str(index_file))

            if success:
                # Process wishlist if mode is enabled
                if self.wishlist_mode_checkbox.state():
                    log_path = index_file.parent / 'log.csv'
                    if log_path.exists():
                        # Add failed downloads to wishlist
                        self.__processFailedDownloadsToWishlist(str(log_path))
                        # Remove successful downloads from wishlist
                        self.__removeSuccessfulDownloadsFromWishlist(str(log_path))
                
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "updateStatusText:", "Complete", False
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

    def generate_manual_index_file(self):
        """Generate an index file manually when a download is stopped prematurely."""
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "updateStatusText:", "Generating index for stopped download...", False
        )
        
        try:
            if not self.download_target_dir:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", f"\n❌ Download target directory not set.\n", False
                )
                return



            # Find the most recent processed CSV file (created by CSV processor)
            csv_files = list(self.download_target_dir.rglob("*.csv"))
            if not csv_files:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", f"\n❌ No processed CSV file found to append to.\n", False
                )
                return
            
            # Use the most recent one
            log_file = max(csv_files, key=lambda f: f.stat().st_mtime)
            
            # Get all tracks that should have been downloaded
            all_tracks = self.__get_playlist_tracks()
            if not all_tracks:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", "\n❌ Could not retrieve playlist tracks.\n", False
                )
                return
            
            # Get successfully downloaded tracks from existing processed log
            successful_tracks = self.__get_successful_tracks_from_processed_log(log_file)
            
            # Find missing tracks
            missing_tracks = [track for track in all_tracks if track not in successful_tracks]
            
            if not missing_tracks:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", "\n✅ All tracks were successfully downloaded.\n", False
                )
                return
            
            # Append missing tracks to the processed log file
            self.__append_missing_tracks_to_processed_log(log_file, missing_tracks)
            
            # Process wishlist if mode is enabled
            if self.wishlist_mode_checkbox.state():
                if log_file.exists():
                    # Add failed downloads to wishlist
                    self.__processFailedDownloadsToWishlist(str(log_file))
                    # Remove successful downloads from wishlist
                    self.__removeSuccessfulDownloadsFromWishlist(str(log_file))
            
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "updateStatusText:", "Stopped", False
            )

        except Exception as e:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "appendOutput:", f"\n❌ Error generating manual index file: {str(e)}\n", False
            )

    def __get_playlist_tracks(self):
        """Get all tracks from the current playlist source."""
        try:
            selected_source = self.source_popup.titleOfSelectedItem()
            
            if selected_source == "YouTube Playlist":
                playlist_url = self.playlist_field.stringValue().strip()
                cmd = [str(self.sldl_path), playlist_url, '--print', 'tracks']
            elif selected_source == "Spotify Playlist":
                playlist_url = self.spotify_field.stringValue().strip()
                cmd = [str(self.sldl_path), playlist_url, '--print', 'tracks']
            else:  # Wishlist
                # Create temporary wishlist file in sldl format
                temp_wishlist_file = self.__createSldlWishlistFile()
                if not temp_wishlist_file:
                    return []
                
                wishlist_file = temp_wishlist_file
                cmd = [str(self.sldl_path), wishlist_file, '--input-type', 'list', '--print', 'tracks']
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            
            tracks = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # Extract track name from sldl output
                    if ' - ' in line:
                        # Remove duration if present (e.g., "Artist - Title (123s)" -> "Artist - Title")
                        track_name = re.sub(r'\s*\(\d+s\)$', '', line.strip())
                        tracks.append(track_name)
            
            return tracks
            
        except Exception as e:
            print(f"Error getting playlist tracks: {e}")
            return []

    def __get_successful_tracks_from_index(self, index_path):
        """Extract successfully downloaded tracks from sldl index file."""
        successful_tracks = []
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse the index line format
                    parts = []
                    current_part = ""
                    in_quotes = False
                    for char in line:
                        if char == '"':
                            in_quotes = not in_quotes
                        elif char == ',' and not in_quotes:
                            parts.append(current_part.strip())
                            current_part = ""
                        else:
                            current_part += char
                    parts.append(current_part.strip())
                    
                    if len(parts) >= 4:
                        input_part = parts[0].strip('"')
                        state = parts[3].strip('"')
                        
                        # Check if this is a successful download
                        if state == "succeeded":
                            # Extract the track name from the input
                            if 'artist=' in input_part and 'title=' in input_part:
                                # Parse structured input
                                artist = ""
                                title = ""
                                for param in input_part.split(','):
                                    if param.startswith('artist='):
                                        artist = param.split('=', 1)[1].strip()
                                    elif param.startswith('title='):
                                        title = param.split('=', 1)[1].strip()
                                
                                if artist and title:
                                    successful_tracks.append(f"{artist} - {title}")
                            else:
                                # Use the input as-is
                                successful_tracks.append(input_part)
                                
        except Exception as e:
            print(f"Error parsing index file: {e}")
        
        return successful_tracks

    def __append_missing_tracks_to_index(self, index_path, missing_tracks):
        """Append missing tracks to the existing index file."""
        try:
            with open(index_path, 'a', encoding='utf-8') as f:
                for track in missing_tracks:
                    # Parse artist and title from the track string
                    artist = ""
                    title = ""
                    
                    if ' - ' in track:
                        # Format: "Artist - Title"
                        artist, title = track.split(' - ', 1)
                    elif 'artist=' in track and 'title=' in track:
                        # Format: "artist=Artist,title=Title"
                        for param in track.split(','):
                            if param.startswith('artist='):
                                artist = param.split('=', 1)[1].strip()
                            elif param.startswith('title='):
                                title = param.split('=', 1)[1].strip()
                    else:
                        # Fallback: use the whole track as title
                        title = track
                    
                    # Write the missing track entry in the correct CSV format
                    # Columns: filepath, artist, album, title, length, tracktype, state, failurereason
                    f.write(f'"{artist} - {title}.mp3","{artist}","","{title}","","","failed","Download cancelled by user"\n')
                    
        except Exception as e:
            print(f"Error appending to index file: {e}")
            raise

    def __get_successful_tracks_from_processed_log(self, log_path):
        """Extract successfully downloaded tracks from processed log.csv file."""
        successful_tracks = []
        try:
            import csv
            with open(log_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Check if this is a successful download
                    if row.get('state') == '1' or row.get('state_description') == 'Downloaded':
                        # Extract the track name from the title column
                        artist = row.get('artist', '').strip()
                        title = row.get('title', '').strip()
                        
                        if artist and title:
                            successful_tracks.append(f"{artist} - {title}")
                        elif title:
                            successful_tracks.append(title)
                                
        except Exception as e:
            print(f"Error parsing processed log file: {e}")
        
        return successful_tracks

    def __append_missing_tracks_to_processed_log(self, log_path, missing_tracks):
        """Append missing tracks to the processed log.csv file with proper human-readable codes."""
        try:
            import csv
            # Read existing data to get fieldnames
            with open(log_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
            
            # Append missing tracks
            with open(log_path, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                for track in missing_tracks:
                    # Parse artist and title from the track string
                    artist = ""
                    title = ""
                    
                    if ' - ' in track:
                        # Format: "Artist - Title"
                        artist, title = track.split(' - ', 1)
                    elif 'artist=' in track and 'title=' in track:
                        # Format: "artist=Artist,title=Title"
                        for param in track.split(','):
                            if param.startswith('artist='):
                                artist = param.split('=', 1)[1].strip()
                            elif param.startswith('title='):
                                title = param.split('=', 1)[1].strip()
                    else:
                        # Fallback: use the whole track as title
                        title = track
                    
                    # Create row with proper human-readable codes
                    row = {
                        'filepath': f"{artist} - {title}.mp3",
                        'artist': artist,
                        'album': '',
                        'title': title,
                        'length': '',
                        'tracktype': '',
                        'state': '2',  # Failed state code
                        'failurereason': 'Download cancelled by user',
                        'state_description': 'Failed',
                        'failure_description': 'Download cancelled by user'
                    }
                    
                    writer.writerow(row)
                    
        except Exception as e:
            print(f"Error appending to processed log file: {e}")
            raise


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







    def viewWishlist_(self, sender):
        """Show wishlist contents in a popup dialog."""
        try:
            # Ensure we're on the main thread
            if not NSThread.isMainThread():
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "viewWishlist:", sender, False
                )
                return
            
            wishlist_items = self.__loadWishlistItems()
            if not wishlist_items:
                self.showAlert_message_("Wishlist", "Your wishlist is empty.")
                return
            
            # Create content
            content = ""
            for item in wishlist_items:
                content += f"{item}\n"
            
            # Create alert with scrollable text
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Wishlist Contents")
            alert.setInformativeText_(content)
            alert.addButtonWithTitle_("Close")
            
            # Set alert style to informational
            alert.setAlertStyle_(1)  # NSAlertStyleInformational
            
            alert.runModal()
                
        except Exception as e:
            self.showAlert_message_("Error", f"Failed to view wishlist: {str(e)}")

    def exportWishlist_(self, sender):
        """Handle export button click from main wishlist controls."""
        self.__exportWishlistToCSV()

    def clearWishlist_(self, sender):
        """Handle clear button click with confirmation dialog."""
        try:
            # Show confirmation dialog
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Clear Wishlist")
            alert.setInformativeText_("Are you sure? This will irreversibly delete all entries from your wishlist.")
            alert.addButtonWithTitle_("Cancel")
            alert.addButtonWithTitle_("Clear")
            
            # Set alert style to warning
            alert.setAlertStyle_(2)  # NSAlertStyleWarning
            
            response = alert.runModal()
            if response == NSAlertSecondButtonReturn:  # Clear button
                # Clear the wishlist
                self.__saveWishlistItems([])
                self.showAlert_message_("Success", "Wishlist has been cleared.")
                
        except Exception as e:
            self.showAlert_message_("Error", f"Failed to clear wishlist: {str(e)}")

    def importWishlist_(self, sender):
        """Import tracks from a CSV file to the wishlist."""
        try:
            # Ask user to select CSV file
            panel = NSOpenPanel.openPanel()
            panel.setCanChooseFiles_(True)
            panel.setCanChooseDirectories_(False)
            panel.setAllowsMultipleSelection_(False)
            panel.setTitle_("Import Wishlist from CSV")
            panel.setAllowedFileTypes_(["csv"])
            
            if panel.runModal() == NSModalResponseOK:
                csv_path = panel.URL().path()
                imported_count = self.__importWishlistFromCSV(csv_path)
                self.showAlert_message_("Success", f"{imported_count} songs imported to wishlist")
                
        except Exception as e:
            self.showAlert_message_("Error", f"Failed to import wishlist: {str(e)}")

    def __loadWishlistItems(self):
        """Load wishlist items from CSV file."""
        items = []
        if WISHLIST_FILE.exists():
            try:
                import csv
                with open(WISHLIST_FILE, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        if 'title' in row and 'artist' in row:
                            items.append(f"{row['artist']} - {row['title']}")
                        elif 'track' in row:
                            items.append(row['track'])
            except Exception as e:
                print(f"Error loading wishlist: {e}")
        return items

    def __createSldlWishlistFile(self):
        """Create a temporary wishlist file in the format sldl expects."""
        try:
            wishlist_items = self.__loadWishlistItems()
            if not wishlist_items:
                return None
            
            # Create a temporary file with proper sldl list format
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            
            for item in wishlist_items:
                if ' - ' in item:
                    artist, title = item.split(' - ', 1)
                    # Format: "artist=Artist,title=Title"     ""     ""
                    formatted_line = f'"artist={artist},title={title}"\t""\t""\n'
                else:
                    # For items without artist-title format, use as search string
                    formatted_line = f'"{item}"\t""\t""\n'
                
                temp_file.write(formatted_line)
            
            temp_file.close()
            return temp_file.name
            
        except Exception as e:
            print(f"Error creating sldl wishlist file: {e}")
            return None

    def __createSldlWishlistFileFromCSV(self):
        """Create a temporary wishlist file from CSV in the format sldl expects."""
        try:
            csv_path = self.csv_field.stringValue().strip()
            if not csv_path:
                return None
            
            # Read CSV file and extract items
            import csv
            items = []
            
            with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'title' in row and 'artist' in row and row['artist'] and row['title']:
                        items.append(f"{row['artist']} - {row['title']}")
                    elif 'track' in row and row['track']:
                        items.append(row['track'])
            
            if not items:
                return None
            
            # Create a temporary file with proper sldl list format
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            
            for item in items:
                if ' - ' in item:
                    artist, title = item.split(' - ', 1)
                    # Format: "artist=Artist,title=Title"     ""     ""
                    formatted_line = f'"artist={artist},title={title}"\t""\t""\n'
                else:
                    # For items without artist-title format, use as search string
                    formatted_line = f'"{item}"\t""\t""\n'
                
                temp_file.write(formatted_line)
            
            temp_file.close()
            return temp_file.name
            
        except Exception as e:
            print(f"Error creating sldl wishlist file from CSV: {e}")
            return None

    def __saveWishlistItems(self, items):
        """Save wishlist items to CSV file."""
        try:
            import csv
            with open(WISHLIST_FILE, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['artist', 'title']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for item in items:
                    if ' - ' in item:
                        artist, title = item.split(' - ', 1)
                        writer.writerow({'artist': artist, 'title': title})
                    else:
                        writer.writerow({'artist': '', 'title': item})
        except Exception as e:
            raise Exception(f"Failed to save wishlist: {e}")

    def __addToWishlist(self, items):
        """Add items to wishlist without duplicates."""
        try:
            existing_items = set(self.__loadWishlistItems())
            new_items = set(items)
            
            # Add new items that aren't already in the wishlist
            items_to_add = new_items - existing_items
            if items_to_add:
                all_items = list(existing_items) + list(items_to_add)
                self.__saveWishlistItems(all_items)
                return len(items_to_add)
            return 0
        except Exception as e:
            print(f"Error adding to wishlist: {e}")
            return 0

    def __removeFromWishlist(self, items):
        """Remove items from wishlist."""
        try:
            existing_items = self.__loadWishlistItems()
            items_to_remove = set(items)
            
            # Remove items that match
            remaining_items = [item for item in existing_items if item not in items_to_remove]
            
            if len(remaining_items) != len(existing_items):
                self.__saveWishlistItems(remaining_items)
                return len(existing_items) - len(remaining_items)
            return 0
        except Exception as e:
            print(f"Error removing from wishlist: {e}")
            return 0

    def __exportWishlistToCSV(self):
        """Export wishlist to a user-selected CSV file."""
        try:
            wishlist_items = self.__loadWishlistItems()
            if not wishlist_items:
                self.showAlert_message_("Error", "No items in wishlist to export.")
                return
            
            # Ask user for export location using save panel
            panel = NSSavePanel.savePanel()
            panel.setTitle_("Export Wishlist")
            panel.setAllowedFileTypes_(["csv"])
            panel.setNameFieldStringValue_("wishlist_export.csv")
            
            if panel.runModal() == NSModalResponseOK:
                export_path = panel.URL().path()
                
                # Save directly to user-selected location
                try:
                    import csv
                    with open(export_path, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = ['artist', 'title']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        
                        for item in wishlist_items:
                            if ' - ' in item:
                                artist, title = item.split(' - ', 1)
                                writer.writerow({'artist': artist, 'title': title})
                            else:
                                writer.writerow({'artist': '', 'title': item})
                    
                    self.showAlert_message_("Success", f"Exported {len(wishlist_items)} items to wishlist file.")
                except Exception as e:
                    self.showAlert_message_("Error", f"Failed to export wishlist: {str(e)}")
                
        except Exception as e:
            self.showAlert_message_("Error", f"Failed to export wishlist: {str(e)}")

    def __importWishlistFromCSV(self, csv_path):
        """Import tracks from CSV file to wishlist."""
        try:
            import csv
            items_to_import = []
            
            with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'title' in row and 'artist' in row and row['artist'] and row['title']:
                        items_to_import.append(f"{row['artist']} - {row['title']}")
                    elif 'track' in row and row['track']:
                        items_to_import.append(row['track'])
            
            if items_to_import:
                return self.__addToWishlist(items_to_import)
            return 0
            
        except Exception as e:
            raise Exception(f"Failed to import CSV: {e}")

    def __processFailedDownloadsToWishlist(self, log_path):
        """Process failed downloads from log.csv and add to wishlist."""
        try:
            import csv
            failed_items = []
            
            with open(log_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Check if this is a failed download
                    state = row.get('state', '')
                    state_desc = row.get('state_description', '')
                    failure_desc = row.get('failure_description', '')
                    
                    if (state == '2' or state_desc == 'Failed' or 
                        'Failed' in failure_desc or 'cancelled' in failure_desc.lower()):
                        
                        # Extract artist and title
                        artist = row.get('artist', '')
                        title = row.get('title', '')
                        
                        if artist and title:
                            failed_items.append(f"{artist} - {title}")
            
            if failed_items:
                added_count = self.__addToWishlist(failed_items)
                if added_count > 0:
                    self.performSelectorOnMainThread_withObject_waitUntilDone_(
                        "appendOutput:", f"\n📝 Added {added_count} failed downloads to wishlist.\n", False
                    )
                    
        except Exception as e:
            print(f"Error processing failed downloads to wishlist: {e}")

    def __removeSuccessfulDownloadsFromWishlist(self, log_path):
        """Remove successfully downloaded tracks from wishlist."""
        try:
            import csv
            successful_items = []
            
            with open(log_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Check if this is a successful download
                    state = row.get('state', '')
                    state_desc = row.get('state_description', '')
                    
                    if (state == '1' or state_desc == 'Downloaded'):
                        artist = row.get('artist', '')
                        title = row.get('title', '')
                        
                        if artist and title:
                            successful_items.append(f"{artist} - {title}")
            
            if successful_items:
                removed_count = self.__removeFromWishlist(successful_items)
                if removed_count > 0:
                    self.performSelectorOnMainThread_withObject_waitUntilDone_(
                        "appendOutput:", f"\n✅ Removed {removed_count} successful downloads from wishlist.\n", False
                    )
                    
        except Exception as e:
            print(f"Error removing successful downloads from wishlist: {e}")

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
