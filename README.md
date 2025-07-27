# SoulseekDownloader

A Python GUI application that provides a graphical user interface for batch downloading music from Soulseek using YouTube playlist URLs.

## Overview

SoulseekDownloader is a cross-platform Python application built with tkinter that simplifies the process of downloading music from Soulseek. It takes a YouTube playlist URL, extracts the song information, and uses the [slsk-batchdl](https://github.com/fiso64/slsk-batchdl) (`sldl`) command-line tool to download the corresponding tracks from Soulseek.

## Features

- **YouTube Playlist Integration**: Enter a YouTube playlist URL to automatically extract song information
- **Soulseek Authentication**: Secure login with your Soulseek username and password
- **Custom Download Path**: Specify where you want to save your downloaded music
- **Real-time Output**: View download progress and status updates in real-time
- **Cross-platform UI**: Clean, intuitive interface built with tkinter

## Prerequisites

Before using SoulseekDownloader, you need to have the `sldl` command-line tool installed on your system. The application expects `sldl` to be available at `/usr/local/bin/sldl`.

### Installing sldl

The `sldl` tool is the [slsk-batchdl](https://github.com/fiso64/slsk-batchdl) Soulseek downloader that can be installed via various methods:

1. **Manual installation** (recommended):

   - Download the latest release from the [slsk-batchdl releases page](https://github.com/fiso64/slsk-batchdl/releases)
   - Extract the downloaded file
   - Make it executable: `chmod +x sldl`
   - Move it to `/usr/local/bin/`: `sudo mv sldl /usr/local/bin/`

2. **Docker** (alternative):

   ```bash
   git clone https://github.com/fiso64/slsk-batchdl
   cd slsk-batchdl
   docker compose up -d
   ```

3. **Build from source**:
   - Clone the repository: `git clone https://github.com/fiso64/slsk-batchdl`
   - Build using .NET: `dotnet build`
   - The executable will be in the build output directory

## Installation

1. Clone or download this repository
2. Ensure you have Python 3.6+ installed
3. Run the application using one of the methods below

### Running the Application

**Option 1: Direct Python execution (Recommended)**

```bash
python3 soulseek_downloader.py
```

**Option 2: Using the launcher script**

```bash
./run_soulseek_downloader.sh
```

**Option 3: Double-click the launcher script**

- Make the script executable: `chmod +x run_soulseek_downloader.sh`
- Double-click `run_soulseek_downloader.sh` in Finder

### Creating a Standalone Executable (Advanced)

Creating standalone executables on macOS can be complex due to system restrictions. The recommended approach is to run the Python script directly.

If you still want to try creating an executable, you may need to:

1. Install Xcode Command Line Tools
2. Use a virtual environment
3. Handle macOS security restrictions

However, running the Python script directly is simpler and more reliable.

## Usage

1. **Launch the Application**: Run `python3 soulseek_downloader.py` from the terminal

2. **Enter YouTube Playlist URL**: Paste the URL of a YouTube playlist containing the songs you want to download

3. **Provide Soulseek Credentials**:

   - Enter your Soulseek username
   - Enter your Soulseek password (securely hidden)

4. **Set Download Path** (optional): Specify a custom directory where you want to save the downloaded music. If left empty, sldl will use its default location.

5. **Start Download**: Click the "Download Songs" button to begin the batch download process

6. **Monitor Progress**: Watch the real-time output in the scrollable text area to track download progress and any errors

## Project Structure

```
SoulseekDownloader/
├── soulseek_downloader.py             # Main Python application
├── run_soulseek_downloader.sh         # Launcher script for easy execution
├── requirements.txt                   # Python dependencies (none required)
├── README.md                          # This file
└── sldl_osx-x64/                     # slsk-batchdl executable (if downloaded)
```

### Key Components

- **soulseek_downloader.py**: The main Python application with GUI and download logic
- **run_soulseek_downloader.sh**: Shell script launcher for easy execution
- **requirements.txt**: Lists Python dependencies (uses only standard library)
- **sldl_osx-x64/**: Contains the slsk-batchdl executable (optional, can be installed system-wide)

## Technical Details

The application works by:

1. Taking user input (playlist URL, credentials, download path)
2. Creating a subprocess to execute the `sldl` command from [slsk-batchdl](https://github.com/fiso64/slsk-batchdl)
3. Passing the appropriate arguments to `sldl` (YouTube playlist URL, Soulseek credentials, download path)
4. Capturing and displaying real-time output from the process using threading
5. Handling process completion and error states with proper GUI feedback

The `sldl` tool supports various input types including YouTube playlists, Spotify playlists, CSV files, and direct song searches. It automatically handles Soulseek authentication, search, and download processes.

### Python Implementation Features

- **Threading**: Downloads run in background threads to keep the GUI responsive
- **Real-time Output**: Live display of download progress and status
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Cross-platform**: Works on Windows, macOS, and Linux
- **No Dependencies**: Uses only Python standard library modules

## Requirements

- **Python**: 3.6 or later
- **Operating System**: Windows, macOS, or Linux
- **sldl**: Command-line tool installed at `/usr/local/bin/sldl` (or in PATH)

## Troubleshooting

### Common Issues

1. **"Error running sldl"**: Make sure `sldl` is installed and accessible at `/usr/local/bin/sldl`
2. **Authentication failures**: Verify your Soulseek username and password are correct
3. **Download path issues**: Ensure the specified download path exists and is writable
4. **Playlist parsing errors**: Check that the YouTube playlist URL is valid and accessible
5. **Rate limiting**: Soulseek may ban users for 30 minutes if too many searches are performed. The `sldl` tool has built-in rate limiting (34 searches every 220 seconds by default)

### Debugging

- Check the output text area for detailed error messages
- Verify `sldl` installation: `which sldl` should return `/usr/local/bin/sldl`
- Test `sldl` manually from Terminal to ensure it works correctly
- Check the [slsk-batchdl documentation](https://github.com/fiso64/slsk-batchdl) for advanced configuration options

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
