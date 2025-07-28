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
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QProgressBar, QFileDialog, QMessageBox,
    QCheckBox, QComboBox, QFrame, QScrollArea
)
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import pyqtSignal, QObject, QThread

from csv_processor import SLDLCSVProcessor


class Communicate(QObject):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int, str)
    status_signal = pyqtSignal(str)

class SoulseekDownloader(QWidget):
    def __init__(self):
        super().__init__()
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

        # Create main container with padding
        main_container = QFrame(self)
        main_container.setObjectName("mainContainer")
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(30, 20, 30, 20)

        # Create scrollable main frame
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.scrollable_frame = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)

        # Main content
        self.create_header()
        self.create_connection_section()
        self.create_quality_section()
        self.create_action_section()
        self.create_progress_section()
        self.create_output_section()

        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

        # Thread-safe GUI updates
        self.comm = Communicate()
        self.comm.log_signal.connect(self.log_output)
        self.comm.progress_signal.connect(self.update_progress)
        self.comm.status_signal.connect(self.update_status)

        # Initialize
        self.check_sldl_availability()
        self.csv_processor = SLDLCSVProcessor()
        
        # Settings management
        self.settings_file = Path.home() / ".soulseek_downloader_settings.json"
        self.loading_settings = True
        self.load_settings()
        self.loading_settings = False

        self.show()

    def setup_modern_styles(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.colors['bg_secondary']};
            }}
            QFrame#mainContainer {{
                background-color: {self.colors['bg_secondary']};
            }}
            QLabel {{
                color: {self.colors['text_secondary']};
            }}
            QLineEdit, QComboBox {{
                padding: 8px;
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton {{
                padding: 12px 20px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                color: white;
                background-color: {self.colors['primary']};
            }}
            QPushButton:hover {{
                background-color: {self.colors['primary_light']};
            }}
            QTextEdit {{
                background-color: #1a1a1a;
                color: #e0e0e0;
                border: none;
                border-radius: 4px;
                font-family: 'SF Mono', 'Consolas', 'Monaco', 'Menlo', 'Courier New', monospace;
                font-size: 12px;
            }}
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: {self.colors['bg_tertiary']};
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {self.colors['secondary']};
                border-radius: 4px;
            }}
        """)

    def create_header(self):
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        title_label = QLabel("Soulseek Downloader")
        title_label.setFont(QFont("SF Pro Display", 28, QFont.Bold))
        title_label.setStyleSheet(f"color: {self.colors['text_primary']};")
        subtitle_label = QLabel("Download music collections from YouTube playlists via Soulseek")
        subtitle_label.setFont(QFont("SF Pro Text", 12))
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        self.scrollable_frame.addWidget(header_frame)

    def create_connection_section(self):
        section_frame = self.create_card_section("Connection Settings", "Configure your Soulseek credentials and download preferences")
        content_frame = QFrame(section_frame)
        content_layout = QVBoxLayout(content_frame)

        self.playlist_url = self.create_input_field(content_layout, "YouTube Playlist URL", placeholder="https://www.youtube.com/playlist?list=...")
        
        cred_frame = QFrame()
        cred_layout = QHBoxLayout(cred_frame)
        self.username = self.create_input_field(cred_layout, "Soulseek Username")
        self.password = self.create_input_field(cred_layout, "Soulseek Password", show="*")
        content_layout.addWidget(cred_frame)

        self.remember_password_var = QCheckBox("Remember password")
        self.remember_password_var.setChecked(True)
        self.remember_password_var.stateChanged.connect(self.on_remember_password_changed)
        content_layout.addWidget(self.remember_password_var)

        path_frame = QFrame()
        path_layout = QHBoxLayout(path_frame)
        self.download_path = self.create_input_field(path_layout, "Download Path (optional)")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_directory)
        path_layout.addWidget(self.browse_btn)
        content_layout.addWidget(path_frame)
        
        section_layout = section_frame.layout()
        section_layout.addWidget(content_frame)
        self.scrollable_frame.addWidget(section_frame)

    def create_quality_section(self):
        section_frame = self.create_card_section("Audio Quality Settings", "Set preferred and required audio quality parameters")
        quality_frame = QFrame(section_frame)
        quality_layout = QHBoxLayout(quality_frame)

        pref_card = self.create_sub_card("Preferred Settings", "Flexible options - will accept alternatives if not found")
        pref_content = QFrame(pref_card)
        pref_layout = QVBoxLayout(pref_content)
        self.pref_format_var, self.pref_min_bitrate_var, self.pref_max_bitrate_var = self.create_quality_inputs(pref_layout)
        pref_card.setLayout(pref_layout)
        quality_layout.addWidget(pref_card)

        strict_card = self.create_sub_card("Strict Requirements", "Required parameters - no alternatives accepted")
        strict_content = QFrame(strict_card)
        strict_layout = QVBoxLayout(strict_content)
        self.strict_format_var, self.strict_min_bitrate_var, self.strict_max_bitrate_var = self.create_quality_inputs(strict_layout)
        strict_card.setLayout(strict_layout)
        quality_layout.addWidget(strict_card)
        
        section_layout = section_frame.layout()
        section_layout.addWidget(quality_frame)
        self.scrollable_frame.addWidget(section_frame)

    def create_quality_inputs(self, parent_layout):
        format_combo = self.create_input_field(parent_layout, "Format", input_type="combobox", values=["", "mp3", "flac", "wav", "m4a", "ogg"])
        min_bitrate = self.create_input_field(parent_layout, "Min Bitrate", placeholder="e.g., 320")
        max_bitrate = self.create_input_field(parent_layout, "Max Bitrate", placeholder="e.g., 2500")
        return format_combo, min_bitrate, max_bitrate

    def create_action_section(self):
        action_frame = QFrame()
        action_layout = QHBoxLayout(action_frame)
        self.download_btn = QPushButton("Start Download")
        self.download_btn.clicked.connect(self.start_download)
        action_layout.addWidget(self.download_btn)
        self.scrollable_frame.addWidget(action_frame)

    def create_progress_section(self):
        progress_frame = QFrame()
        progress_layout = QVBoxLayout(progress_frame)
        self.progress_label = QLabel("Ready to download")
        self.progress = QProgressBar()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress)
        self.scrollable_frame.addWidget(progress_frame)

    def create_output_section(self):
        section_frame = self.create_card_section("Download Log", "Real-time output from the download process")
        output_frame = QFrame(section_frame)
        output_layout = QVBoxLayout(output_frame)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        output_layout.addWidget(self.output)
        section_layout = section_frame.layout()
        section_layout.addWidget(output_frame)
        self.scrollable_frame.addWidget(section_frame)

    def create_card_section(self, title, description):
        card_frame = QFrame()
        card_frame.setFrameShape(QFrame.StyledPanel)
        card_layout = QVBoxLayout(card_frame)
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        title_label = QLabel(title)
        title_label.setFont(QFont("SF Pro Display", 16, QFont.Bold))
        desc_label = QLabel(description)
        desc_label.setFont(QFont("SF Pro Text", 10))
        header_layout.addWidget(title_label)
        header_layout.addWidget(desc_label)
        card_layout.addWidget(header_frame)
        return card_frame

    def create_sub_card(self, title, description):
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card_layout = QVBoxLayout(card)
        header = QFrame()
        header_layout = QVBoxLayout(header)
        title_label = QLabel(title)
        title_label.setFont(QFont("SF Pro Text", 12, QFont.Bold))
        desc_label = QLabel(description)
        desc_label.setFont(QFont("SF Pro Text", 10))
        header_layout.addWidget(title_label)
        header_layout.addWidget(desc_label)
        card_layout.addWidget(header)
        return card

    def create_input_field(self, parent_layout, label, input_type="entry", show=None, values=None, placeholder=""):
        label_widget = QLabel(label)
        parent_layout.addWidget(label_widget)
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

    def check_sldl_availability(self):
        try:
            result = subprocess.run(['which', 'sldl'], capture_output=True, text=True)
            if result.returncode != 0:
                self.comm.log_signal.emit("Warning: sldl not found in PATH. Please ensure it's installed at /usr/local/bin/sldl\n")
                self.comm.status_signal.emit("Warning: sldl not found")
            else:
                self.comm.log_signal.emit(f"sldl found at: {result.stdout.strip()}\n")
                self.comm.status_signal.emit("Ready - sldl available")
        except Exception as e:
            self.comm.log_signal.emit(f"Error checking sldl availability: {e}\n")

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
                self.comm.log_signal.emit(f"Error updating password settings: {e}\n")
        self.save_settings()

    def log_output(self, message):
        self.output.append(message)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

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
        self.download_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.comm.progress_signal.emit(0, 100, "Initializing download...")
        self.output.clear()

        try:
            playlist_url = self.playlist_url.text().strip()
            username_val = self.username.text().strip()
            password_val = self.password.text().strip()
            download_path_val = self.download_path.text().strip()

            cmd = ['sldl', playlist_url, '--user', username_val, '--pass', password_val]
            if download_path_val:
                cmd.extend(['--path', download_path_val])

            pref_format = self.pref_format_var.currentText()
            if pref_format: cmd.extend(['--pref-format', pref_format])
            pref_min_br = self.pref_min_bitrate_var.text().strip()
            if pref_min_br: cmd.extend(['--pref-min-bitrate', pref_min_br])
            pref_max_br = self.pref_max_bitrate_var.text().strip()
            if pref_max_br: cmd.extend(['--pref-max-bitrate', pref_max_br])

            strict_format = self.strict_format_var.currentText()
            if strict_format: cmd.extend(['--format', strict_format])
            strict_min_br = self.strict_min_bitrate_var.text().strip()
            if strict_min_br: cmd.extend(['--min-bitrate', strict_min_br])
            strict_max_br = self.strict_max_bitrate_var.text().strip()
            if strict_max_br: cmd.extend(['--max-bitrate', strict_max_br])

            self.comm.log_signal.emit(f"Executing command: {' '.join(cmd[:3])} [password] {' '.join(cmd[4:])}\n")
            self.comm.status_signal.emit("Connecting to Soulseek...")

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

            total_songs = 0
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.comm.log_signal.emit(line)
                    line_clean = line.strip()
                    # ... (rest of the parsing logic, adapted for pyqt signals)
            
            return_code = process.wait()
            if return_code == 0:
                self.comm.progress_signal.emit(100, 100, "Download completed")
                # ... (rest of the completion logic)
            else:
                self.comm.status_signal.emit(f"Download failed (exit code: {return_code})")

        except FileNotFoundError:
            # ... (error handling)
            pass
        except Exception as e:
            # ... (error handling)
            pass
        finally:
            self.download_btn.setEnabled(True)
            self.browse_btn.setEnabled(True)

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
                # ... (load other settings)

        except Exception as e:
            self.comm.log_signal.emit(f"Error loading settings: {e}\n")

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
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            self.comm.log_signal.emit(f"Error saving settings: {e}\n")
    
    def closeEvent(self, event):
        self.save_settings()
        event.accept()

def main():
    app = QApplication(sys.argv)
    ex = SoulseekDownloader()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
