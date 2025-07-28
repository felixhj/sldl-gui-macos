#!/usr/bin/env python3
"""SoulseekDownloader - PyObjC GUI version."""

import subprocess
import threading
import json
from pathlib import Path

import objc
from Cocoa import (
    NSApplication, NSApp, NSWindow, NSButton, NSTextField, NSSecureTextField,
    NSScrollView, NSTextView, NSProgressIndicator, NSMakeRect,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskResizable, NSBackingStoreBuffered,
    NSOpenPanel, NSObject, NSApplicationActivationPolicyRegular
)

SETTINGS_FILE = Path.home() / ".soulseek_downloader_settings.json"

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        self.build_ui()
        self.load_settings()
        NSApp.activateIgnoringOtherApps_(True)

    def build_ui(self):
        style = (
            NSWindowStyleMaskTitled |
            NSWindowStyleMaskClosable |
            NSWindowStyleMaskResizable
        )
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(100.0, 100.0, 700.0, 500.0),
            style,
            NSBackingStoreBuffered,
            False
        )
        self.window.setTitle_("Soulseek Downloader")
        view = self.window.contentView()

        y = 440
        self.playlist_label = NSTextField.labelWithString_("YouTube Playlist URL:")
        self.playlist_label.setFrame_(NSMakeRect(20, y, 200, 24))
        view.addSubview_(self.playlist_label)
        self.playlist_field = NSTextField.alloc().initWithFrame_(NSMakeRect(220, y, 460, 24))
        view.addSubview_(self.playlist_field)

        y -= 40
        self.user_label = NSTextField.labelWithString_("Soulseek Username:")
        self.user_label.setFrame_(NSMakeRect(20, y, 200, 24))
        view.addSubview_(self.user_label)
        self.user_field = NSTextField.alloc().initWithFrame_(NSMakeRect(220, y, 200, 24))
        view.addSubview_(self.user_field)

        y -= 40
        self.pass_label = NSTextField.labelWithString_("Soulseek Password:")
        self.pass_label.setFrame_(NSMakeRect(20, y, 200, 24))
        view.addSubview_(self.pass_label)
        self.pass_field = NSSecureTextField.alloc().initWithFrame_(NSMakeRect(220, y, 200, 24))
        view.addSubview_(self.pass_field)

        y -= 40
        self.path_label = NSTextField.labelWithString_("Download Path:")
        self.path_label.setFrame_(NSMakeRect(20, y, 200, 24))
        view.addSubview_(self.path_label)
        self.path_field = NSTextField.alloc().initWithFrame_(NSMakeRect(220, y, 300, 24))
        view.addSubview_(self.path_field)
        self.browse_button = NSButton.alloc().initWithFrame_(NSMakeRect(530, y, 80, 24))
        self.browse_button.setTitle_("Browse")
        self.browse_button.setTarget_(self)
        self.browse_button.setAction_(objc.selector(self.browse_directory_, signature=b'v@:'))
        view.addSubview_(self.browse_button)

        y -= 50
        self.start_button = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 150, 32))
        self.start_button.setTitle_("Start Download")
        self.start_button.setTarget_(self)
        self.start_button.setAction_(objc.selector(self.start_download_, signature=b'v@:'))
        view.addSubview_(self.start_button)

        self.progress = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(180, y, 250, 20))
        self.progress.setIndeterminate_(False)
        self.progress.setMinValue_(0)
        self.progress.setMaxValue_(100)
        view.addSubview_(self.progress)

        y -= 230
        self.output_view = NSTextView.alloc().initWithFrame_(NSMakeRect(20, 20, 650, 200))
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 20, 650, 200))
        scroll.setDocumentView_(self.output_view)
        scroll.setHasVerticalScroller_(True)
        view.addSubview_(scroll)

        self.window.makeKeyAndOrderFront_(None)

    def append_output(self, text):
        def _append():
            self.output_view.textStorage().mutableString().appendString_(text)
            length = len(self.output_view.string())
            self.output_view.scrollRangeToVisible_((length, 0))
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(_append, signature=b'v@:'), None, False)

    def browse_directory_(self, sender):
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(False)
        panel.setCanChooseDirectories_(True)
        panel.setAllowsMultipleSelection_(False)
        if panel.runModal() == 1:
            url = panel.URL()
            if url:
                self.path_field.setStringValue_(url.path())

    def start_download_(self, sender):
        self.start_button.setEnabled_(False)
        self.progress.setDoubleValue_(0)
        thread = threading.Thread(target=self.download_thread)
        thread.start()

    def download_thread(self):
        playlist_url = self.playlist_field.stringValue().strip()
        username = self.user_field.stringValue().strip()
        password = self.pass_field.stringValue().strip()
        path = self.path_field.stringValue().strip()

        if not playlist_url or not username or not password:
            self.append_output("Error: Please fill in all required fields.\n")
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                objc.selector(lambda: self.start_button.setEnabled_(True), signature=b'v@:'), None, False)
            return

        cmd = ['sldl', playlist_url, '--user', username, '--pass', password]
        if path:
            cmd.extend(['--path', path])

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        total = 0
        current = 0
        for line in process.stdout:
            self.append_output(line)
            if "Found" in line and ("tracks" in line or "songs" in line):
                try:
                    total = int(line.split()[1])
                    self.progress.setMaxValue_(float(total))
                except Exception:
                    pass
            if "Downloading" in line and "/" in line:
                try:
                    parts = line[line.find('[')+1:line.find(']')].split('/')
                    current = int(parts[0])
                    self.progress.doubleValue()
                    self.performSelectorOnMainThread_withObject_waitUntilDone_(
                        objc.selector(lambda val=current: self.progress.setDoubleValue_(float(val)), signature=b'v@:'), None, False)
                except Exception:
                    pass

        process.wait()
        self.append_output("Download finished.\n")
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(lambda: self.start_button.setEnabled_(True), signature=b'v@:'), None, False)
        self.save_settings()

    def load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                self.playlist_field.setStringValue_(data.get('playlist_url', ''))
                self.user_field.setStringValue_(data.get('username', ''))
                self.pass_field.setStringValue_(data.get('password', ''))
                self.path_field.setStringValue_(data.get('download_path', ''))
            except Exception:
                pass

    def save_settings(self):
        data = {
            'playlist_url': self.playlist_field.stringValue(),
            'username': self.user_field.stringValue(),
            'password': self.pass_field.stringValue(),
            'download_path': self.path_field.stringValue(),
        }
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


def main():
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    app.run()


if __name__ == "__main__":
    main()
