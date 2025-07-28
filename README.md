# SoulseekDownloader

A Python GUI application that provides a graphical user interface for batch downloading music from Soulseek using YouTube playlist URLs.

## Overview

SoulseekDownloader is a cross-platform Python application built with tkinter that simplifies the process of downloading music from Soulseek. It takes a YouTube playlist URL, extracts the song information, and uses the [slsk-batchdl](https://github.com/fiso64/slsk-batchdl) (`sldl`) command-line tool to download the corresponding tracks from Soulseek.

## Features

- **YouTube Playlist Integration**: Enter a YouTube playlist URL to automatically extract song information
- **Soulseek Authentication**: Secure login with your Soulseek username and password
- **Custom Download Path**: Specify where you want to save your downloaded music
- **Real-time Output**: View download progress and status updates in real-time with thread-safe GUI updates
- **CSV Processing**: Automatically converts numeric error codes to human-readable descriptions
- **Settings Persistence**: Automatically saves and restores user preferences (credentials, paths, quality settings)
- **Quality Control**: Flexible preferred settings and strict quality requirements for audio formats and bitrates
- **Modern UI**: Clean, intuitive interface with modern styling and cross-platform compatibility
- **Thread-Safe Operations**: Downloads run in background threads to keep the GUI responsive

## Prerequisites

Before using SoulseekDownloader, you need to have the `sldl` command-line tool installed on your system. The application expects `sldl` to be available in your system PATH (typically `/usr/local/bin/sldl` on macOS/Linux).

### Installing sldl

The `sldl` tool is the [slsk-batchdl](https://github.com/fiso64/slsk-batchdl) Soulseek downloader that can be installed via various methods:

1. **Manual installation** (recommended):

   - Download the latest release from the [slsk-batchdl releases page](https://github.com/fiso64/slsk-batchdl/releases)
   - Extract the downloaded file
   - Make it executable: `chmod +x sldl`
   - Move it to `/usr/local/bin/`: `sudo mv sldl /usr/local/bin/`

2. **Use included binary** (macOS x64):

   - This repository includes a pre-compiled macOS x64 binary in the `sldl_osx-x64/` directory
   - Copy to system path: `sudo cp sldl_osx-x64/sldl /usr/local/bin/`
   - Make executable: `sudo chmod +x /usr/local/bin/sldl`

3. **Build from source**:
   - The `slsk-batchdl-master/` directory contains the complete source code
   - Requires .NET SDK: `dotnet build`
   - The executable will be in the build output directory

## Installation

1. Clone or download this repository
2. Ensure you have Python 3.6+ installed
3. Install the `sldl` command-line tool (see Prerequisites above)
4. Run the application using one of the methods below

### Running the Application

**Option 1: Direct Python execution (Recommended)**

```bash
python3 soulseek_downloader.py
```

**Option 2: Using the launcher script**

```bash
chmod +x run_soulseek_downloader.sh
./run_soulseek_downloader.sh
```

**Option 3: Double-click the launcher script**

- Make the script executable: `chmod +x run_soulseek_downloader.sh`
- Double-click `run_soulseek_downloader.sh` in Finder

### Using the CSV Processor Standalone

The CSV processor can also be used independently to process existing CSV files from slsk-batchdl:

```bash
# Process a single CSV file
python3 csv_processor.py your_file.csv

# Process all CSV files in a directory
python3 csv_processor.py --directory ./downloads

# Get help
python3 csv_processor.py --help
```

## Usage

1. **Launch the Application**: Run `python3 soulseek_downloader.py` from the terminal

2. **Enter YouTube Playlist URL**: Paste the URL of a YouTube playlist containing the songs you want to download

3. **Provide Soulseek Credentials**:

   - Enter your Soulseek username
   - Enter your Soulseek password (securely hidden)
   - Optionally uncheck "Remember password" if you prefer not to save credentials

4. **Set Download Path** (optional): Specify a custom directory where you want to save the downloaded music. If left empty, sldl will use its default location.

5. **Configure Audio Quality Settings**:

   **Preferred Settings (Flexible)**:

   - **Format**: Choose from mp3, flac, wav, m4a, ogg (leave empty to accept any)
   - **Min Bitrate**: Set minimum bitrate in kbps (e.g., 320)
   - **Max Bitrate**: Set maximum bitrate in kbps (e.g., 2500)

   **Strict Requirements (Required)**:

   - **Format**: Strict format requirement (will reject other formats)
   - **Min Bitrate**: Strict minimum bitrate requirement
   - **Max Bitrate**: Strict maximum bitrate requirement

6. **Start Download**: Click the "Start Download" button to begin the batch download process

7. **Monitor Progress**: Watch the real-time output in the scrollable text area to track download progress and any errors

8. **Process CSV Files**: After download completion, the sldl index file (`_index.csv`) is automatically processed to add human-readable error codes and state descriptions.

## Settings Persistence

The application automatically saves your preferences and restores them when you restart the app. The following settings are remembered:

- **Soulseek credentials** (username and password - only if "Remember password" is checked)
- **Download path**
- **Audio quality preferences** (format, bitrate settings for both preferred and strict options)

Settings are saved automatically as you type and when you close the application. The settings file is stored in your home directory as `.soulseek_downloader_settings.json`.

**Security Note**: Passwords are encoded with base64 for basic obfuscation, but the settings file should still be kept secure as it contains your Soulseek credentials.

## Project Structure

```
SoulseekDownloader/
├── soulseek_downloader.py             # Main Python application (1,127 lines)
├── csv_processor.py                   # Standalone CSV processing module (212 lines)
├── run_soulseek_downloader.sh         # Launcher script for easy execution
├── requirements.txt                   # Python dependencies (uses only standard library)
├── README.md                          # This documentation file
├── _index_processed.csv               # Example processed CSV output
├── sldl_osx-x64/                     # Pre-compiled slsk-batchdl executable (macOS x64)
│   ├── sldl                          # slsk-batchdl executable (26MB)
│   └── sldl.pdb                      # Debug symbols
└── slsk-batchdl-master/              # Complete slsk-batchdl source code
    ├── slsk-batchdl/                 # Main source directory
    ├── slsk-batchdl.Tests/           # Unit tests
    ├── Dockerfile                    # Docker configuration
    ├── README.md                     # slsk-batchdl documentation
    └── [other source files]
```

### Key Components

- **soulseek_downloader.py**: The main Python application with modern GUI, download logic, and thread-safe operations
- **csv_processor.py**: Standalone module for processing CSV files and adding human-readable error descriptions
- **run_soulseek_downloader.sh**: Shell script launcher for easy execution with Python version detection
- **requirements.txt**: Lists Python dependencies (uses only standard library modules)
- **sldl_osx-x64/**: Contains pre-compiled slsk-batchdl executable for macOS x64
- **slsk-batchdl-master/**: Complete source code of the slsk-batchdl tool

## Technical Details

The application works by:

1. Taking user input (playlist URL, credentials, download path, quality settings)
2. Creating a subprocess to execute the `sldl` command from [slsk-batchdl](https://github.com/fiso64/slsk-batchdl)
3. Passing the appropriate arguments to `sldl` with configured quality parameters
4. Capturing and displaying real-time output from the process using threading
5. Parsing download progress from multiple output patterns for accurate progress tracking
6. Handling process completion and error states with proper GUI feedback
7. Automatically processing the sldl index file using the separate `csv_processor.py` module

### Python Implementation Features

- **Thread-Safe GUI Updates**: Uses queue-based system for safe GUI updates from background threads
- **Real-time Progress Tracking**: Parses multiple output patterns to track download progress accurately
- **Modern UI Design**: Clean interface with custom styling and cross-platform font handling
- **Robust Error Handling**: Comprehensive error handling with user-friendly messages and debug output
- **Modular Architecture**: CSV processing logic separated into reusable, standalone module
- **Settings Management**: Automatic persistence with base64 encoding for password obfuscation
- **Cross-platform Compatibility**: Works on Windows, macOS, and Linux with proper font fallbacks
- **No External Dependencies**: Uses only Python standard library modules

## CSV Processing and Error Codes

The application automatically processes CSV files generated by `sldl` to convert numeric error codes into human-readable descriptions. This functionality is implemented in a separate module (`csv_processor.py`) that can also be used independently.

### State Codes (from slsk-batchdl source code)

- **0**: Initial - Track not yet processed
- **1**: Downloaded - Successfully downloaded
- **2**: Failed - Download failed (see failure reason)
- **3**: AlreadyExists - File already exists locally
- **4**: NotFoundLastTime - Not found in previous search attempt

### Failure Reason Codes (from slsk-batchdl source code)

- **0**: None - No failure
- **1**: InvalidSearchString - Search string format invalid
- **2**: OutOfDownloadRetries - Exceeded maximum retry attempts
- **3**: NoSuitableFileFound - No files matched quality criteria
- **4**: AllDownloadsFailed - All download attempts failed
- **5**: Other - Unspecified failure reason

### CSV File Structure

The CSV files generated by slsk-batchdl contain columns like:

```
filepath,artist,album,title,length,tracktype,state,failurereason
```

After processing, additional columns are added:

```
filepath,artist,album,title,length,tracktype,state,failurereason,state_description,failure_description
```

## Troubleshooting

### Common Issues

1. **"Error running sldl"**:

   - Make sure `sldl` is installed and accessible in your PATH
   - Test with: `which sldl` (should return a path)
   - Try installing from the included binary: `sudo cp sldl_osx-x64/sldl /usr/local/bin/`

2. **AttributeError: 'SoulseekDownloader' object has no attribute 'gui_queue'**:

   - This is a known initialization issue that occasionally occurs
   - **Solution**: Restart the application - the GUI queue setup happens during initialization
   - If persistent, check that you're using Python 3.6+ and tkinter is properly installed

3. **IndentationError in soulseek_downloader.py**:

   - This indicates the Python file was corrupted or improperly edited
   - **Solution**: Re-download the original file or check for mixing tabs/spaces in the code

4. **Authentication failures**:

   - Verify your Soulseek username and password are correct
   - Check that your Soulseek account is active and not banned

5. **Download path issues**:

   - Ensure the specified download path exists and is writable
   - Use absolute paths to avoid confusion

6. **Playlist parsing errors**:

   - Check that the YouTube playlist URL is valid and accessible
   - Ensure the playlist is public or unlisted (not private)

7. **Rate limiting**:
   - Soulseek may ban users for 30 minutes if too many searches are performed
   - The `sldl` tool has built-in rate limiting (34 searches every 220 seconds by default)

### Debugging Steps

1. **Check sldl installation**:

   ```bash
   which sldl
   sldl --help
   ```

2. **Test sldl manually**:

   ```bash
   sldl "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID" --user YOUR_USERNAME --pass YOUR_PASSWORD
   ```

3. **Check Python version**:

   ```bash
   python3 --version
   ```

4. **Run with debug output**:

   - The application logs detailed debug information to the output area
   - Look for `[DEBUG]` and `[PROGRESS]` messages for troubleshooting

5. **Verify file permissions**:
   ```bash
   chmod +x run_soulseek_downloader.sh
   chmod +x sldl_osx-x64/sldl
   ```

## Requirements

- **Python**: 3.6 or later with tkinter support
- **Operating System**: Windows, macOS, or Linux
- **sldl**: Command-line tool installed in system PATH
- **Dependencies**: None (uses only Python standard library)

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is open source. Please check the license file for more details.

## Disclaimer

This application is for educational and personal use only. Please respect copyright laws and only download music that you have the right to access. The developers are not responsible for any misuse of this software.

## Acknowledgments

- Built with Python and tkinter for cross-platform compatibility
- Integrates with the [slsk-batchdl](https://github.com/fiso64/slsk-batchdl) Soulseek downloader tool
- Uses YouTube playlist parsing for song identification
- Thanks to [fiso64](https://github.com/fiso64) for creating the excellent `sldl` command-line tool
- Modern UI design inspired by contemporary application interfaces
