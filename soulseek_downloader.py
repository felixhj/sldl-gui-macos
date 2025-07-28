#!/usr/bin/env python3
"""
SoulseekDownloader - A Python GUI application for batch downloading music from Soulseek
using YouTube playlist URLs and the slsk-batchdl tool.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import subprocess
import threading
import os
import sys
from pathlib import Path


class SoulseekDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Soulseek Downloader")
        self.root.geometry("800x650")
        self.root.resizable(True, True)

        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TLabel', font=('Helvetica', 12))
        self.style.configure('TButton', font=('Helvetica', 12), padding=5)
        self.style.configure('Accent.TButton', font=('Helvetica', 12, 'bold'), foreground='white', background='#0078D7')
        self.style.configure('TEntry', font=('Helvetica', 12), padding=5)
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('Header.TLabel', font=('Helvetica', 18, 'bold'))

        # Create main frame
        main_frame = ttk.Frame(root, padding="20", style='TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # --- Widgets ---
        # Title
        title_label = ttk.Label(main_frame, text="Soulseek Downloader", style='Header.TLabel', background='#f0f0f0')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky=tk.W)

        # Input Frame
        input_frame = ttk.Frame(main_frame, padding="15", style='TFrame')
        input_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E))
        input_frame.columnconfigure(1, weight=1)

        # YouTube Playlist URL
        ttk.Label(input_frame, text="YouTube Playlist URL:", background='#f0f0f0').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.playlist_url = ttk.Entry(input_frame, width=60)
        self.playlist_url.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))

        # Soulseek Credentials
        ttk.Label(input_frame, text="Soulseek Username:", background='#f0f0f0').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.username = ttk.Entry(input_frame)
        self.username.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))

        ttk.Label(input_frame, text="Soulseek Password:", background='#f0f0f0').grid(row=2, column=0, sticky=tk.W, pady=5)
        self.password = ttk.Entry(input_frame, show="*")
        self.password.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))

        # Download Path
        ttk.Label(input_frame, text="Download Path:", background='#f0f0f0').grid(row=3, column=0, sticky=tk.W, pady=5)
        self.download_path = ttk.Entry(input_frame)
        self.download_path.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        self.browse_btn = ttk.Button(input_frame, text="Browse", command=self.browse_directory)
        self.browse_btn.grid(row=3, column=2, padx=(5, 0), pady=5)
        
        # Options Frame
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="15")
        options_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.high_quality_var = tk.BooleanVar(value=True)
        self.high_quality_check = ttk.Checkbutton(
            options_frame,
            text="Download 320kbps MP3 only",
            variable=self.high_quality_var
        )
        self.high_quality_check.grid(row=0, column=0, sticky=tk.W)

        # Download button
        self.download_btn = ttk.Button(main_frame, text="Download Songs", command=self.start_download, style='Accent.TButton')
        self.download_btn.grid(row=3, column=0, columnspan=3, pady=20)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, orient='horizontal', length=400, mode='determinate')
        self.progress.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        # Output text area
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)

        self.output = scrolledtext.ScrolledText(output_frame, height=15, width=80, font=('Menlo', 11), relief=tk.SUNKEN, borderwidth=1)
        self.output.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=5)
        status_bar.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Check if sldl is available
        self.check_sldl_availability()
    
    def check_sldl_availability(self):
        """Check if sldl is available in the system PATH"""
        try:
            result = subprocess.run(['which', 'sldl'], capture_output=True, text=True)
            if result.returncode != 0:
                self.log_output("Warning: sldl not found in PATH. Please ensure it's installed at /usr/local/bin/sldl\n")
                self.status_var.set("Warning: sldl not found")
            else:
                self.log_output(f"sldl found at: {result.stdout.strip()}\n")
                self.status_var.set("Ready - sldl available")
        except Exception as e:
            self.log_output(f"Error checking sldl availability: {e}\n")
    
    def browse_directory(self):
        """Open directory browser for download path"""
        directory = filedialog.askdirectory()
        if directory:
            self.download_path.delete(0, tk.END)
            self.download_path.insert(0, directory)
    
    def log_output(self, message):
        """Add message to output area"""
        self.output.insert(tk.END, message)
        self.output.see(tk.END)
        self.root.update_idletasks()
    
    def start_download(self):
        """Start the download process in a separate thread"""
        if not self.playlist_url.get().strip():
            messagebox.showerror("Error", "Please enter a YouTube playlist URL")
            return
        
        if not self.username.get().strip():
            messagebox.showerror("Error", "Please enter your Soulseek username")
            return
        
        if not self.password.get().strip():
            messagebox.showerror("Error", "Please enter your Soulseek password")
            return
        
        # Run download in separate thread to keep GUI responsive
        thread = threading.Thread(target=self.download_songs, daemon=True)
        thread.start()
    
    def download_songs(self):
        """Execute the sldl command and capture output"""
        self.download_btn.config(state='disabled')
        self.browse_btn.config(state='disabled')
        self.progress['value'] = 0
        self.progress['maximum'] = 100
        self.status_var.set("Starting download...")
        self.output.delete(1.0, tk.END)
        
        try:
            # Build command
            cmd = ['sldl', self.playlist_url.get().strip()]
            
            # Add credentials
            cmd.extend(['--user', self.username.get().strip()])
            cmd.extend(['--pass', self.password.get().strip()])
            
            # Add download path if specified
            if self.download_path.get().strip():
                cmd.extend(['--path', self.download_path.get().strip()])

            # Add high quality option if selected
            if self.high_quality_var.get():
                cmd.extend(['--pref-min-bitrate', '320', '--format', 'mp3'])
            
            self.log_output(f"Executing command: {' '.join(cmd[:3])} [password] {' '.join(cmd[4:])}\n")
            self.log_output("-" * 50 + "\n")
            
            # Run the process
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output in real-time
            total_songs = 0
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.log_output(line)
                    
                    # Check for total songs
                    if "Found" in line and "tracks" in line:
                        try:
                            total_songs = int(line.split()[1])
                            self.progress['maximum'] = total_songs
                        except (ValueError, IndexError):
                            pass
                    
                    # Check for progress
                    if line.startswith("["):
                        try:
                            progress_str = line.split(']')[0][1:]
                            current, total = map(int, progress_str.split('/'))
                            self.progress['value'] = current
                            if total != total_songs:
                                total_songs = total
                                self.progress['maximum'] = total
                            self.status_var.set(f"Downloading song {current}/{total_songs}")
                        except (ValueError, IndexError):
                             pass
            
            # Wait for process to complete
            return_code = process.wait()
            
            if return_code == 0:
                self.log_output("\n" + "=" * 50 + "\n")
                self.log_output("Download completed successfully!\n")
                self.status_var.set("Download completed successfully")
                messagebox.showinfo("Success", "Download completed successfully!")
            else:
                self.log_output(f"\nProcess exited with code: {return_code}\n")
                self.status_var.set(f"Download failed (exit code: {return_code})")
                messagebox.showerror("Error", f"Download failed with exit code: {return_code}")
                
        except FileNotFoundError:
            error_msg = "sldl command not found. Please ensure slsk-batchdl is installed at /usr/local/bin/sldl"
            self.log_output(f"Error: {error_msg}\n")
            self.status_var.set("Error: sldl not found")
            messagebox.showerror("Error", error_msg)
        except Exception as e:
            error_msg = f"Error during download: {e}"
            self.log_output(f"Error: {error_msg}\n")
            self.status_var.set("Error occurred")
            messagebox.showerror("Error", error_msg)
        finally:
            self.progress.stop()
            self.download_btn.config(state='normal')
            self.browse_btn.config(state='normal')


def main():
    """Main function to run the application"""
    root = tk.Tk()
    
    # Set application icon if available
    try:
        # You can add an icon file here if you have one
        # root.iconbitmap('icon.ico')  # For Windows
        # root.iconbitmap('icon.xbm')  # For Unix/Linux
        pass
    except:
        pass
    
    app = SoulseekDownloader(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    # Start the application
    root.mainloop()


if __name__ == "__main__":
    main() 