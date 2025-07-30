#!/usr/bin/env python3
"""sldl-gui for macOS - PyObjC GUI version."""

import subprocess
import threading
import json
import sys
import re
from pathlib import Path

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

class AppDelegate(NSObject):
    
    def applicationDidFinishLaunching_(self, notification):
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            self.sldl_path = Path(sys._MEIPASS) / 'bin' / 'sldl'
        else:
            self.sldl_path = 'sldl'

        self.setup_menu()
        self.build_ui()
        self.load_settings()
        NSApp.activateIgnoringOtherApps_(True)

    def setup_menu(self):
        """Setup application menu with Edit menu for copy/paste support."""
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
            NSMakeRect(100.0, 100.0, 750.0, 600.0),
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

        # YouTube Playlist URL
        y -= CONTROL_HEIGHT
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

        # Start Button, Help, and Progress Bar
        self.start_button = NSButton.alloc().initWithFrame_(NSMakeRect(PADDING, y, 150, START_BUTTON_HEIGHT))
        self.start_button.setTitle_("Start Download")
        self.start_button.setBezelStyle_(NSBezelStyleRounded)
        self.start_button.setKeyEquivalent_("\r")
        self.start_button.setTarget_(self)
        self.start_button.setAction_("startDownload:")
        self.start_button.setAutoresizingMask_(NSViewMaxXMargin | NSViewMaxYMargin)
        view.addSubview_(self.start_button)

        help_button_x = PADDING + 150 + 10
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
        """Show help dialog for format options."""
        help_text = """Format & Bitrate Criteria Help:

PREFERRED CRITERIA (First Choice):
sldl will prioritize files matching these criteria, but will fall back to other options if none are found.

• Format: Your preferred audio format (mp3, flac, wav, etc.)
• Min/Max Bitrate: Your preferred quality range (e.g., 200-2500 kbps)

STRICT CRITERIA (Requirements):
sldl will ONLY download files that meet these requirements. Files not matching will be skipped entirely.

• Format: Only accept this specific format
• Min/Max Bitrate: Hard minimum/maximum limits

SUPPORTED AUDIO FORMATS:
• mp3 - MPEG Audio Layer III (most common)
• flac - Free Lossless Audio Codec (lossless)
• wav - Waveform Audio File Format (uncompressed)
• m4a - MPEG-4 Audio (AAC in MP4 container)
• aac - Advanced Audio Coding
• ogg - Ogg Vorbis (open source)
• opus - Modern low-latency codec
• wma - Windows Media Audio
• ape - Monkey's Audio (lossless)
• alac - Apple Lossless Audio Codec
• aiff - Audio Interchange File Format
• wv - WavPack (lossless)
• shn - Shorten (lossless)
• tak - Tom's lossless Audio Kompressor
• tta - True Audio (lossless)

EXAMPLES:
Scenario 1 - High Quality Preferred:
• Preferred: Format=flac, Min=1000 kbps
• Strict: (leave empty)
→ Prefers FLAC 1000+ kbps, but accepts lower quality if needed

Scenario 2 - MP3 Only:
• Preferred: (leave empty)  
• Strict: Format=mp3, Min=192 kbps
→ Only downloads MP3 files with at least 192 kbps

Scenario 3 - Best of Both:
• Preferred: Format=flac, Min=1000 kbps
• Strict: Min=192 kbps
→ Prefers high-quality FLAC, but accepts any format ≥192 kbps

Leave fields empty to use sldl defaults.

SECURITY NOTE:
When "Remember Password" is checked, your password will be stored in plain text in:
~/.soulseek_downloader_settings.json

Only enable this on your personal, secure computer."""
        
        self.showAlert_message_("Format Help", help_text)

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

        if self.total_steps > 0:
            status_text = f"Step {int(current_step)} of {self.total_steps} | {message}"
        else:
            status_text = message
            
        self.status_label.setStringValue_(status_text)

    def switchToDeterminateProgress_(self, max_value):
        """Switch the progress bar to determinate mode with a max value."""
        self.progress.stopAnimation_(None)
        self.progress.setIndeterminate_(False)
        self.total_steps = int(float(max_value))
        self.progress.setMaxValue_(float(self.total_steps))
        self.progress.setDoubleValue_(0.0)
        total_tracks = self.total_steps / 2
        self.status_label.setStringValue_(f"Found {int(total_tracks)} tracks ({self.total_steps} steps)")

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
        playlist_url = self.playlist_field.stringValue().strip()
        username = self.user_field.stringValue().strip()
        password = self.pass_field.stringValue().strip()
        
        if not playlist_url:
            self.showAlert_message_("Error", "Please enter a YouTube playlist URL.")
            return
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

        # Disable the start button and reset progress
        self.start_button.setEnabled_(False)
        self.output_view.setString_("")
        self.total_steps = 0
        
        # Start indeterminate progress immediately
        self.progress.setIndeterminate_(True)
        self.progress.startAnimation_(None)
        self.status_label.setStringValue_("Starting...")
        
        # Start download in background thread
        thread = threading.Thread(target=self.downloadThread, daemon=True)
        thread.start()

    def downloadThread(self):
        """Run the download process in a background thread."""
        try:
            playlist_url = self.playlist_field.stringValue().strip()
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

            total_tracks = 0
            succeeded_count = 0
            failed_count = 0
            searching_count = 0
            
            for line in process.stdout:
                # Update output on main thread
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "appendOutput:", line, False
                )
                
                # --- Final progress logic based on user feedback ---
                
                # Update status based on various log messages
                if "Loading YouTube playlist" in line:
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", "Loading playlist...", False)
                elif line.startswith("Login"):
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", "Logging in...", False)

                # Get total tracks and set the max progress bar value (tracks * 2)
                total_match = re.search(r'Downloading (\d+) tracks:', line)
                if total_match:
                    total_tracks = int(total_match.group(1))
                    if total_tracks > 0:
                        max_steps = float(total_tracks * 2)
                        self.performSelectorOnMainThread_withObject_waitUntilDone_("switchToDeterminateProgress:", max_steps, False)
                    continue

                # --- Count each "Searching" and "Succeeded/Failed" as one step ---
                step_made = False
                status_message = ""

                if line.startswith("Searching:"):
                    searching_count += 1
                    step_made = True
                    status_message = "Searching..."
                
                elif line.startswith("Succeeded:"):
                    succeeded_count += 1
                    step_made = True
                    status_message = "Download Succeeded"

                elif line.startswith("All downloads failed:"):
                    failed_count += 1
                    step_made = True
                    status_message = "Download Failed"
                
                if step_made:
                    current_step = float(searching_count + succeeded_count + failed_count)
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("updateProgressAndStatus:", (current_step, status_message), False)
                    continue
                
                # Get final completion summary from the log
                completed_match = re.search(r'Completed: (.*)', line)
                if completed_match:
                    summary = completed_match.group(1).strip()
                    self.performSelectorOnMainThread_withObject_waitUntilDone_("updateStatusText:", f"Finished: {summary}", False)
                    continue

            # Wait for process to complete
            return_code = process.wait()
            
            # Reset the progress indicator state
            self.performSelectorOnMainThread_withObject_waitUntilDone_("resetProgressIndicator", None, False)

            # The progress bar's final state is now accurate. No need to force it.
            
            if return_code == 0:
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
            # Re-enable the start button
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "enableStartButton:", True, False
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
                self.playlist_field.setStringValue_(data.get('playlist_url', ''))
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
            'playlist_url': self.playlist_field.stringValue(),
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
