#!/usr/bin/env python3
"""
SoulseekDownloader - A Python GUI application for batch downloading music from Soulseek
using YouTube playlist URLs and the slsk-batchdl tool.
"""

import sys
import os
import subprocess
import threading
import json
import base64
import queue
import re
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QProgressBar, QFileDialog, QMessageBox,
    QCheckBox, QComboBox, QFrame, QScrollArea
)
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import pyqtSignal, QObject, QThread, QTimer

from csv_processor import SLDLCSVProcessor


class Communicate(QObject):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int, str)
    status_signal = pyqtSignal(str)
    gui_update_signal = pyqtSignal()


class SoulseekDownloader(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize GUI queue for thread safety - MUST be set up before init_ui
        self.gui_queue = queue.Queue()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Soulseek Downloader")
        self.setGeometry(100, 100, 1200, 900)

        # Modern color palette
        self.colors = {
            'primary': '#1a365d',
            'primary_light': '#2d3748',
            'secondary': '#4299e1',
            'accent': '#38b2ac',
            'success': '#38a169',
            'warning': '#ed8936',
            'danger': '#e53e3e',
            'bg_primary': '#ffffff',
            'bg_secondary': '#f7fafc',
            'bg_tertiary': '#edf2f7',
            'text_primary': '#1a202c',
            'text_secondary': '#4a5568',
            'text_muted': '#718096',
            'border': '#e2e8f0'
        }

        self.setup_modern_styles()

        # Create main layout - set this on the widget directly
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)

        # Create scrollable main frame
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.scrollable_layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)

        # Main content
        self.create_header()
        self.create_connection_section()
        self.create_quality_section()
        self.create_action_section()
        self.create_progress_section()
        self.create_output_section()

        main_layout.addWidget(scroll)

        # Thread-safe GUI updates
        self.comm = Communicate()
        self.comm.log_signal.connect(self.log_output)
        self.comm.progress_signal.connect(self.update_progress)
        self.comm.status_signal.connect(self.update_status)
        self.comm.gui_update_signal.connect(self.process_gui_updates)

        # Set up GUI update timer
        self.setup_gui_updates()

        # Initialize
        self.check_sldl_availability()
        self.csv_processor = SLDLCSVProcessor()
        
        # Settings management
        self.settings_file = Path.home() / ".soulseek_downloader_settings.json"
        self.loading_settings = True
        self.load_settings()
        self.loading_settings = False

        self.show()

    def get_font(self, font_family, size, weight='normal'):
        """Get font with fallbacks for cross-platform compatibility"""
        # Use platform-appropriate fallback fonts
        import platform
        system = platform.system()
        
        if system == "Darwin":  # macOS
            font_families = {
                'SF Pro Display': ['Helvetica Neue', 'Helvetica', 'Arial'],
                'SF Pro Text': ['Helvetica Neue', 'Helvetica', 'Arial'],
                'SF Mono': ['Monaco', 'Menlo', 'Courier New']
            }
        elif system == "Windows":
            font_families = {
                'SF Pro Display': ['Segoe UI', 'Arial', 'sans-serif'],
                'SF Pro Text': ['Segoe UI', 'Arial', 'sans-serif'],
                'SF Mono': ['Consolas', 'Courier New', 'monospace']
            }
        else:  # Linux and others
            font_families = {
                'SF Pro Display': ['Ubuntu', 'Liberation Sans', 'Arial', 'sans-serif'],
                'SF Pro Text': ['Ubuntu', 'Liberation Sans', 'Arial', 'sans-serif'],
                'SF Mono': ['Ubuntu Mono', 'Liberation Mono', 'Courier New', 'monospace']
            }

        fallbacks = font_families.get(font_family, [font_family])
        for font in fallbacks:
            try:
                if weight == 'bold':
                    return QFont(font, size, QFont.Bold)
                else:
                    return QFont(font, size)
            except:
                continue
        # Ultimate fallback
        return QFont('Arial', size)

    def setup_modern_styles(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.colors['bg_secondary']};
            }}
            QLabel {{
                color: {self.colors['text_secondary']};
            }}
            
            /* Text Input Fields - Light gray background for visibility */
            QLineEdit {{
                padding: 12px 16px;
                border: 2px solid #9ca3af;
                border-radius: 8px;
                font-size: 14px;
                background-color: #f8f9fa;
                color: {self.colors['text_primary']};
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.colors['secondary']};
                background-color: #ffffff;
            }}
            QLineEdit::placeholder {{
                color: {self.colors['text_muted']};
                font-style: italic;
            }}
            
            /* Dropdown/ComboBox - Light gray background for visibility */
            QComboBox {{
                padding: 12px 16px;
                padding-right: 40px;
                border: 2px solid #9ca3af;
                border-radius: 8px;
                font-size: 14px;
                background-color: #f8f9fa;
                color: {self.colors['text_primary']};
                min-height: 20px;
            }}
            QComboBox:focus {{
                border: 2px solid {self.colors['secondary']};
                background-color: #ffffff;
            }}
            QComboBox::drop-down {{
                border: none;
                background: transparent;
                width: 30px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {self.colors['text_secondary']};
                width: 0px;
                height: 0px;
            }}
            QComboBox::down-arrow:on {{
                border-top: 6px solid {self.colors['secondary']};
            }}
            
            /* Dropdown List - Clean styling without black headers */
            QComboBox QAbstractItemView {{
                border: 2px solid #9ca3af;
                border-radius: 6px;
                background-color: #ffffff;
                selection-background-color: {self.colors['secondary']};
                selection-color: white;
                outline: none;
                padding: 4px;
                margin: 0px;
                show-decoration-selected: 1;
            }}
            QComboBox QAbstractItemView::item {{
                height: 32px;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                margin: 1px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {self.colors['bg_tertiary']};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {self.colors['secondary']};
                color: white;
            }}
            
            /* Buttons */
            QPushButton {{
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                color: white;
                background-color: {self.colors['primary']};
            }}
            QPushButton:hover {{
                background-color: {self.colors['primary_light']};
            }}
            QPushButton:disabled {{
                background-color: {self.colors['text_muted']};
            }}
            
            /* Text Output Area */
            QTextEdit {{
                background-color: #1a1a1a;
                color: #e0e0e0;
                border: none;
                border-radius: 8px;
                font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
                font-size: 12px;
                padding: 15px;
            }}
            
            /* Progress Bar */
            QProgressBar {{
                border: none;
                border-radius: 6px;
                background-color: {self.colors['bg_tertiary']};
                text-align: center;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {self.colors['secondary']};
                border-radius: 6px;
            }}
            
            /* Card Frames */
            QFrame {{
                background-color: {self.colors['bg_primary']};
                border: 1px solid {self.colors['border']};
                border-radius: 12px;
            }}
            
            /* Checkbox - Remove blue background */
            QCheckBox {{
                color: {self.colors['text_secondary']};
                background-color: transparent;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #9ca3af;
                background-color: #f8f9fa;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['secondary']};
                border: 2px solid {self.colors['secondary']};
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {self.colors['secondary']};
            }}
            
            /* Scrollbars - Rounded and Modern */
            QScrollBar:vertical {{
                background-color: {self.colors['bg_tertiary']};
                width: 12px;
                border-radius: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.colors['text_muted']};
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.colors['secondary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            
            QScrollBar:horizontal {{
                background-color: {self.colors['bg_tertiary']};
                height: 12px;
                border-radius: 6px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {self.colors['text_muted']};
                border-radius: 6px;
                min-width: 20px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {self.colors['secondary']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """)

    def create_header(self):
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        
        title_label = QLabel("Soulseek Downloader")
        title_label.setFont(self.get_font("SF Pro Display", 28, "bold"))
        title_label.setStyleSheet(f"color: {self.colors['text_primary']}; border: none;")
        
        subtitle_label = QLabel("Download music collections from YouTube playlists via Soulseek")
        subtitle_label.setFont(self.get_font("SF Pro Text", 12))
        subtitle_label.setStyleSheet(f"color: {self.colors['text_secondary']}; border: none;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        self.scrollable_layout.addWidget(header_frame)

    def create_connection_section(self):
        section_frame = self.create_card_section("Connection Settings", "Configure your Soulseek credentials and download preferences")
        content_frame = QFrame()
        content_frame.setStyleSheet("border: none;")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 15, 20, 20)
        content_layout.setSpacing(12)

        # YouTube URL - full width
        self.playlist_url = self.create_input_field(content_layout, "YouTube Playlist URL", placeholder="https://www.youtube.com/playlist?list=...")
        
        # Credentials section with proper alignment
        # Add space before credentials section
        content_layout.addSpacing(8)
        
        # Username and password labels row
        labels_frame = QFrame()
        labels_frame.setStyleSheet("border: none;")
        labels_layout = QHBoxLayout(labels_frame)
        labels_layout.setContentsMargins(0, 0, 0, 0)
        labels_layout.setSpacing(20)
        
        username_label = QLabel("Soulseek Username")
        username_label.setFont(self.get_font("SF Pro Text", 12, "bold"))
        username_label.setStyleSheet(f"border: none; color: {self.colors['text_primary']};")
        
        password_label = QLabel("Soulseek Password")
        password_label.setFont(self.get_font("SF Pro Text", 12, "bold"))
        password_label.setStyleSheet(f"border: none; color: {self.colors['text_primary']};")
        
        labels_layout.addWidget(username_label)
        labels_layout.addWidget(password_label)
        content_layout.addWidget(labels_frame)
        
        # Small space between labels and inputs
        content_layout.addSpacing(6)
        
        # Username and password inputs row
        inputs_frame = QFrame()
        inputs_frame.setStyleSheet("border: none;")
        inputs_layout = QHBoxLayout(inputs_frame)
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(20)
        
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        
        inputs_layout.addWidget(self.username)
        inputs_layout.addWidget(self.password)
        content_layout.addWidget(inputs_frame)

        # Remember password checkbox with some spacing
        content_layout.addSpacing(8)  # Space before checkbox
        self.remember_password_var = QCheckBox("Remember password")
        self.remember_password_var.setChecked(True)
        self.remember_password_var.stateChanged.connect(self.on_remember_password_changed)
        self.remember_password_var.setStyleSheet(f"color: {self.colors['text_secondary']};")
        content_layout.addWidget(self.remember_password_var)

        # Download path section  
        content_layout.addSpacing(16)  # Extra space before download path
        
        # Path label
        path_label = QLabel("Download Path (optional)")
        path_label.setFont(self.get_font("SF Pro Text", 12, "bold"))
        path_label.setStyleSheet(f"""
            border: none;
            color: {self.colors['text_primary']};
        """)
        content_layout.addWidget(path_label)
        content_layout.addSpacing(6)  # Space between label and input
        
        # Path input and browse button container
        path_input_frame = QFrame()
        path_input_frame.setStyleSheet("border: none;")
        path_input_layout = QHBoxLayout(path_input_frame)
        path_input_layout.setContentsMargins(0, 0, 0, 0)
        path_input_layout.setSpacing(12)
        
        self.download_path = QLineEdit()
        self.download_path.setPlaceholderText("Leave empty to download to current directory")
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setFixedHeight(46)  # Match input field height
        self.browse_btn.setFixedWidth(100)   # Fixed width for consistency
        self.browse_btn.clicked.connect(self.browse_directory)
        
        path_input_layout.addWidget(self.download_path, 1)  # Give path field more space
        path_input_layout.addWidget(self.browse_btn, 0)     # Fixed size for button
        
        content_layout.addWidget(path_input_frame)
        content_layout.addSpacing(12)  # Space after this section
        
        section_frame.layout().addWidget(content_frame)
        self.scrollable_layout.addWidget(section_frame)

    def create_quality_section(self):
        section_frame = self.create_card_section("Audio Quality Settings", "Set preferred and required audio quality parameters")
        quality_frame = QFrame()
        quality_frame.setStyleSheet("border: none;")
        quality_layout = QHBoxLayout(quality_frame)

        pref_card = self.create_sub_card("Preferred Settings", "Flexible options - will accept alternatives if not found")
        # Get the existing layout from the card and add inputs to it
        pref_card_layout = pref_card.layout()
        self.pref_format_var, self.pref_min_bitrate_var, self.pref_max_bitrate_var = self.create_quality_inputs(pref_card_layout)
        quality_layout.addWidget(pref_card)

        strict_card = self.create_sub_card("Strict Requirements", "Required parameters - no alternatives accepted")
        # Get the existing layout from the card and add inputs to it
        strict_card_layout = strict_card.layout()
        self.strict_format_var, self.strict_min_bitrate_var, self.strict_max_bitrate_var = self.create_quality_inputs(strict_card_layout)
        quality_layout.addWidget(strict_card)
        
        section_frame.layout().addWidget(quality_frame)
        self.scrollable_layout.addWidget(section_frame)

    def create_quality_inputs(self, parent_layout):
        format_combo = self.create_input_field(parent_layout, "Format", input_type="combobox", values=["", "mp3", "flac", "wav", "m4a", "ogg"])
        min_bitrate = self.create_input_field(parent_layout, "Min Bitrate", placeholder="e.g., 320")
        max_bitrate = self.create_input_field(parent_layout, "Max Bitrate", placeholder="e.g., 2500")
        return format_combo, min_bitrate, max_bitrate

    def create_action_section(self):
        action_frame = QFrame()
        action_frame.setStyleSheet("border: none; background-color: " + self.colors['bg_secondary'] + ";")
        action_layout = QHBoxLayout(action_frame)
        self.download_btn = QPushButton("Start Download")
        self.download_btn.clicked.connect(self.start_download)
        action_layout.addWidget(self.download_btn)
        self.scrollable_layout.addWidget(action_frame)

    def create_progress_section(self):
        progress_frame = QFrame()
        progress_frame.setStyleSheet("border: none; background-color: " + self.colors['bg_secondary'] + ";")
        progress_layout = QVBoxLayout(progress_frame)
        self.progress_label = QLabel("Ready to download")
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress)
        self.scrollable_layout.addWidget(progress_frame)

    def create_output_section(self):
        section_frame = self.create_card_section("Download Log", "Real-time output from the download process")
        output_frame = QFrame()
        output_frame.setStyleSheet("border: none;")
        output_layout = QVBoxLayout(output_frame)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        output_layout.addWidget(self.output)
        section_frame.layout().addWidget(output_frame)
        self.scrollable_layout.addWidget(section_frame)

    def create_card_section(self, title, description):
        card_frame = QFrame()
        card_layout = QVBoxLayout(card_frame)
        
        header_frame = QFrame()
        header_frame.setStyleSheet("border: none;")
        header_layout = QVBoxLayout(header_frame)
        
        title_label = QLabel(title)
        title_label.setFont(self.get_font("SF Pro Display", 16, "bold"))
        title_label.setStyleSheet(f"color: {self.colors['text_primary']}; border: none;")
        
        desc_label = QLabel(description)
        desc_label.setFont(self.get_font("SF Pro Text", 10))
        desc_label.setStyleSheet(f"color: {self.colors['text_muted']}; border: none;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(desc_label)
        card_layout.addWidget(header_frame)
        return card_frame

    def create_sub_card(self, title, description):
        card = QFrame()
        card.setStyleSheet(f"background-color: {self.colors['bg_tertiary']}; border: 1px solid {self.colors['border']}; border-radius: 6px;")
        
        # Don't set layout here - let the calling code set it
        header = QFrame()
        header.setStyleSheet("border: none;")
        header_layout = QVBoxLayout(header)
        
        title_label = QLabel(title)
        title_label.setFont(self.get_font("SF Pro Text", 12, "bold"))
        title_label.setStyleSheet(f"color: {self.colors['text_primary']}; border: none;")
        
        desc_label = QLabel(description)
        desc_label.setFont(self.get_font("SF Pro Text", 10))
        desc_label.setStyleSheet(f"color: {self.colors['text_muted']}; border: none;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(desc_label)
        
        # Create the card layout but add the header to it
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(header)
        return card

    def create_input_field(self, parent_layout, label, input_type="entry", show=None, values=None, placeholder=""):
        # Add some space before the label (except for the first field)
        if parent_layout.count() > 0:  # If there are already items in the layout
            parent_layout.addSpacing(8)
        
        # Create label with improved styling (no CSS margins)
        label_widget = QLabel(label)
        label_widget.setFont(self.get_font("SF Pro Text", 12, "bold"))
        label_widget.setStyleSheet(f"""
            border: none;
            color: {self.colors['text_primary']};
        """)
        parent_layout.addWidget(label_widget)
        
        # Small space between label and input
        parent_layout.addSpacing(6)
        
        # Create input widget
        if input_type == "combobox":
            widget = QComboBox()
            if values:
                widget.addItems(values)
        else:
            widget = QLineEdit()
            if show == "*":
                widget.setEchoMode(QLineEdit.Password)
            if placeholder:
                widget.setPlaceholderText(placeholder)
        
        parent_layout.addWidget(widget)
        return widget

    def setup_gui_updates(self):
        """Set up thread-safe GUI updates using a timer"""
        self.gui_timer = QTimer()
        self.gui_timer.timeout.connect(self.process_gui_updates)
        self.gui_timer.start(50)  # Check every 50ms

    def process_gui_updates(self):
        """Process queued GUI updates"""
        try:
            while True:
                update_func, args, kwargs = self.gui_queue.get_nowait()
                update_func(*args, **kwargs)
        except queue.Empty:
            pass

    def safe_gui_update(self, func, *args, **kwargs):
        """Schedule a GUI update to run on the main thread"""
        try:
            self.gui_queue.put((func, args, kwargs))
        except Exception:
            # Fallback: if queue not set up yet, run directly
            try:
                func(*args, **kwargs)
            except:
                pass

    def safe_log_output(self, message):
        """Thread-safe version of log_output"""
        def _update():
            self.output.append(message.rstrip())
            scrollbar = self.output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        self.safe_gui_update(_update)

    def safe_update_progress(self, current, total, description=""):
        """Thread-safe version of update_progress"""
        def _update():
            self.progress.setMaximum(total)
            self.progress.setValue(current)
            if description:
                self.progress_label.setText(description)
        self.safe_gui_update(_update)

    def safe_update_status(self, status_text):
        """Thread-safe status updates"""
        def _update():
            self.progress_label.setText(status_text)
        self.safe_gui_update(_update)

    def check_sldl_availability(self):
        try:
            result = subprocess.run(['which', 'sldl'], capture_output=True, text=True)
            if result.returncode != 0:
                self.safe_log_output("Warning: sldl not found in PATH. Please ensure it's installed at /usr/local/bin/sldl\n")
                self.safe_update_status("Warning: sldl not found")
            else:
                self.safe_log_output(f"sldl found at: {result.stdout.strip()}\n")
                self.safe_update_status("Ready - sldl available")
        except Exception as e:
            self.safe_log_output(f"Error checking sldl availability: {e}\n")

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.download_path.setText(directory)

    def on_remember_password_changed(self):
        if not self.remember_password_var.isChecked():
            try:
                if self.settings_file.exists():
                    with open(self.settings_file, 'r') as f:
                        settings = json.load(f)
                    if 'password' in settings:
                        del settings['password']
                    settings['remember_password'] = False
                    with open(self.settings_file, 'w') as f:
                        json.dump(settings, f, indent=2)
            except Exception as e:
                self.safe_log_output(f"Error updating password settings: {e}\n")
        self.save_settings()

    def log_output(self, message):
        self.output.append(message.rstrip())
        scrollbar = self.output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_progress(self, current, total, description):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.progress_label.setText(description)

    def update_status(self, status_text):
        self.progress_label.setText(status_text)

    def start_download(self):
        playlist_url = self.playlist_url.text().strip()
        username_val = self.username.text().strip()
        password_val = self.password.text().strip()

        if not playlist_url or playlist_url.startswith("https://www.youtube.com/playlist?list=..."):
            QMessageBox.critical(self, "Error", "Please enter a YouTube playlist URL")
            return
        if not username_val:
            QMessageBox.critical(self, "Error", "Please enter your Soulseek username")
            return
        if not password_val:
            QMessageBox.critical(self, "Error", "Please enter your Soulseek password")
            return

        self.download_thread = threading.Thread(target=self.download_songs, daemon=True)
        self.download_thread.start()

    def download_songs(self):
        def _disable_buttons():
            self.download_btn.setEnabled(False)
            self.browse_btn.setEnabled(False)
        
        def _enable_buttons():
            self.download_btn.setEnabled(True)
            self.browse_btn.setEnabled(True)

        self.safe_gui_update(_disable_buttons)
        self.safe_update_progress(0, 100, "Initializing download...")
        self.safe_gui_update(lambda: self.output.clear())

        try:
            playlist_url = self.playlist_url.text().strip()
            username_val = self.username.text().strip()
            password_val = self.password.text().strip()
            download_path_val = self.download_path.text().strip()

            cmd = ['sldl', playlist_url, '--user', username_val, '--pass', password_val]
            if download_path_val:
                cmd.extend(['--path', download_path_val])

            # Add quality options
            pref_format = self.pref_format_var.currentText()
            if pref_format: cmd.extend(['--pref-format', pref_format])
            pref_min_br = self.pref_min_bitrate_var.text().strip()
            if pref_min_br and not pref_min_br.startswith("e.g."): cmd.extend(['--pref-min-bitrate', pref_min_br])
            pref_max_br = self.pref_max_bitrate_var.text().strip()
            if pref_max_br and not pref_max_br.startswith("e.g."): cmd.extend(['--pref-max-bitrate', pref_max_br])

            strict_format = self.strict_format_var.currentText()
            if strict_format: cmd.extend(['--format', strict_format])
            strict_min_br = self.strict_min_bitrate_var.text().strip()
            if strict_min_br and not strict_min_br.startswith("e.g."): cmd.extend(['--min-bitrate', strict_min_br])
            strict_max_br = self.strict_max_bitrate_var.text().strip()
            if strict_max_br and not strict_max_br.startswith("e.g."): cmd.extend(['--max-bitrate', strict_max_br])

            self.safe_log_output(f"Executing command: {' '.join(cmd[:3])} [password] {' '.join(cmd[4:])}\n")
            self.safe_log_output("-" * 50 + "\n")
            self.safe_update_status("Connecting to Soulseek...")

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

            total_songs = 0
            current_song = 0
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.safe_log_output(line)
                    line_clean = line.strip()

                    # Parse total songs
                    if "Downloading" in line_clean and "tracks" in line_clean:
                        try:
                            words = line_clean.split()
                            for i, word in enumerate(words):
                                if word == "Downloading" and i + 1 < len(words):
                                    try:
                                        total_songs = int(words[i + 1])
                                        self.safe_update_progress(0, total_songs, f"Found {total_songs} tracks")
                                        break
                                    except (ValueError, IndexError):
                                        continue
                        except (ValueError, IndexError):
                            pass

                    # Parse progress
                    if "[" in line_clean and "/" in line_clean and "]" in line_clean:
                        try:
                            start = line_clean.find("[") + 1
                            end = line_clean.find("]")
                            progress_str = line_clean[start:end]
                            if "/" in progress_str:
                                current, total = map(int, progress_str.split('/'))
                                current_song = current
                                if total > total_songs:
                                    total_songs = total
                                self.safe_update_progress(current_song, total_songs, f"Downloading song {current_song}/{total_songs}")
                        except (ValueError, IndexError):
                            pass
                    
                    # Look for other progress patterns
                    match = re.search(r'(\d+)/(\d+)', line_clean)
                    if match:
                        try:
                            current = int(match.group(1))
                            total = int(match.group(2))
                            if current <= total and total > 1:
                                current_song = current
                                if total > total_songs:
                                    total_songs = total
                                self.safe_update_progress(current_song, total_songs, f"Processing {current_song}/{total_songs}")
                        except (ValueError, IndexError):
                            pass

            return_code = process.wait()
            if return_code == 0:
                self.safe_update_progress(100, 100, "Download completed")
                self.safe_log_output("\n" + "=" * 50 + "\n")
                self.safe_log_output("Download completed successfully!\n")

                # Process CSV if available
                download_dir = download_path_val if download_path_val else "."
                most_recent_csv = self.find_most_recent_index_csv(download_dir)
                if most_recent_csv:
                    success = self.csv_processor.process_csv_file(str(most_recent_csv))
                    if success:
                        playlist_dir = most_recent_csv.parent.name
                        self.safe_log_output(f"Successfully processed '{most_recent_csv}' -> '{most_recent_csv.parent / '_index_processed.csv'}'\n")
                    else:
                        self.safe_log_output("Failed to process sldl index file.\n")

                self.safe_update_status("Download completed successfully")
                QMessageBox.information(self, "Success", "Download completed successfully!")
            else:
                self.safe_log_output(f"\nProcess exited with code: {return_code}\n")
                self.safe_update_status(f"Download failed (exit code: {return_code})")
                QMessageBox.critical(self, "Error", f"Download failed with exit code: {return_code}")

        except FileNotFoundError:
            error_msg = "sldl command not found. Please ensure slsk-batchdl is installed at /usr/local/bin/sldl"
            self.safe_log_output(f"Error: {error_msg}\n")
            self.safe_update_status("Error: sldl not found")
            QMessageBox.critical(self, "Error", error_msg)
        except Exception as e:
            error_msg = f"Error during download: {e}"
            self.safe_log_output(f"Error: {error_msg}\n")
            self.safe_update_status("Error occurred")
            QMessageBox.critical(self, "Error", error_msg)
        finally:
            self.safe_gui_update(_enable_buttons)

    def find_most_recent_index_csv(self, directory):
        """Find the most recently modified _index.csv file in the directory tree."""
        try:
            download_path = Path(directory)
            if not download_path.exists():
                return None

            index_files = []
            for csv_file in download_path.rglob("_index.csv"):
                if csv_file.is_file():
                    index_files.append(csv_file)

            if not index_files:
                return None

            most_recent = max(index_files, key=lambda f: f.stat().st_mtime)
            return most_recent

        except Exception as e:
            self.safe_log_output(f"Error finding most recent index file: {e}\n")
            return None

    def load_settings(self):
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                
                if 'remember_password' in settings:
                    self.remember_password_var.setChecked(settings['remember_password'])
                if 'username' in settings:
                    self.username.setText(settings['username'])
                if 'password' in settings and settings.get('remember_password', True):
                    decoded_password = base64.b64decode(settings['password']).decode('utf-8')
                    self.password.setText(decoded_password)
                if 'download_path' in settings:
                    self.download_path.setText(settings['download_path'])
                if 'pref_format' in settings:
                    self.pref_format_var.setCurrentText(settings['pref_format'])
                if 'pref_min_bitrate' in settings:
                    self.pref_min_bitrate_var.setText(settings['pref_min_bitrate'])
                if 'pref_max_bitrate' in settings:
                    self.pref_max_bitrate_var.setText(settings['pref_max_bitrate'])
                if 'strict_format' in settings:
                    self.strict_format_var.setCurrentText(settings['strict_format'])
                if 'strict_min_bitrate' in settings:
                    self.strict_min_bitrate_var.setText(settings['strict_min_bitrate'])
                if 'strict_max_bitrate' in settings:
                    self.strict_max_bitrate_var.setText(settings['strict_max_bitrate'])

        except Exception as e:
            self.safe_log_output(f"Error loading settings: {e}\n")

    def save_settings(self):
        if hasattr(self, 'loading_settings') and self.loading_settings:
            return

        try:
            settings = {
                'username': self.username.text().strip(),
                'download_path': self.download_path.text().strip(),
                'pref_format': self.pref_format_var.currentText(),
                'pref_min_bitrate': self.pref_min_bitrate_var.text().strip(),
                'pref_max_bitrate': self.pref_max_bitrate_var.text().strip(),
                'strict_format': self.strict_format_var.currentText(),
                'strict_min_bitrate': self.strict_min_bitrate_var.text().strip(),
                'strict_max_bitrate': self.strict_max_bitrate_var.text().strip(),
                'remember_password': self.remember_password_var.isChecked()
            }
            if self.remember_password_var.isChecked():
                password = self.password.text().strip()
                if password:
                    settings['password'] = base64.b64encode(password.encode('utf-8')).decode('utf-8')
            
            clean_settings = {}
            for key, value in settings.items():
                if key == 'remember_password':
                    clean_settings[key] = value
                elif value and not str(value).startswith("e.g.,") and not str(value).startswith("https://www.youtube.com/playlist"):
                    clean_settings[key] = value
            
            with open(self.settings_file, 'w') as f:
                json.dump(clean_settings, f, indent=2)
        except Exception as e:
            self.safe_log_output(f"Error saving settings: {e}\n")
    
    def closeEvent(self, event):
        self.save_settings()
        event.accept()


def main():
    app = QApplication(sys.argv)
    ex = SoulseekDownloader()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
