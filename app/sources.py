"""Source abstraction for different input types (YouTube, Spotify, CSV, Wishlist).

Each source knows how to:
- Validate its input
- Provide tracks for session logging
- Build sldl command arguments
- Determine the download directory
"""
from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Protocol, runtime_checkable

from app.wishlist import create_csv_from_wishlist, create_sanitized_copy_of_csv, load_items as load_wishlist_items


@dataclass
class SourceConfig:
    """Configuration passed to sources for building commands."""
    sldl_path: str
    username: str
    password: str
    download_path: str
    timestamp: str
    clean_search: bool = False
    
    # Optional settings for command building
    listen_port: str = ""
    concurrent_downloads: str = "2"
    pref_format: str = "Any"
    pref_min_bitrate: str = ""
    pref_max_bitrate: str = ""
    strict_format: str = "Any"
    strict_min_bitrate: str = ""
    strict_max_bitrate: str = ""


@runtime_checkable
class Source(Protocol):
    """Protocol defining the interface for input sources."""
    
    @property
    def name(self) -> str:
        """Human-readable source name."""
        ...
    
    @property
    def uses_timestamped_folder(self) -> bool:
        """Whether this source creates a timestamped subfolder."""
        ...
    
    def validate(self) -> Optional[str]:
        """Validate the source input. Returns error message or None if valid."""
        ...
    
    def get_tracks(self) -> List[str]:
        """Get list of tracks for session logging."""
        ...
    
    def get_sldl_input(self) -> str:
        """Get the input to pass to sldl (URL, file path, or temp file)."""
        ...
    
    def get_download_dir(self, base_path: str, timestamp: str) -> Path:
        """Get the actual download directory (may include timestamped subfolder)."""
        ...
    
    def build_base_args(self, config: SourceConfig) -> List[str]:
        """Build the base sldl command arguments for this source."""
        ...
    
    def get_temp_file(self) -> Optional[str]:
        """Return path to temp file that should be cleaned up, or None."""
        ...


class BaseSource(ABC):
    """Base class with common functionality for all sources."""
    
    def __init__(self) -> None:
        self._temp_file: Optional[str] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        ...
    
    @property
    def uses_timestamped_folder(self) -> bool:
        return False
    
    @abstractmethod
    def validate(self) -> Optional[str]:
        ...
    
    @abstractmethod
    def get_tracks(self) -> List[str]:
        ...
    
    @abstractmethod
    def get_sldl_input(self) -> str:
        ...
    
    def get_download_dir(self, base_path: str, timestamp: str) -> Path:
        """Default: just use base path."""
        return Path(base_path) if base_path else Path.cwd()
    
    def build_base_args(self, config: SourceConfig) -> List[str]:
        """Build base args. Subclasses may override to add --input-type etc."""
        args: List[str] = [
            self.get_sldl_input(),
            '--user', config.username,
            '--pass', config.password,
        ]
        
        download_dir = self.get_download_dir(config.download_path, config.timestamp)
        args.extend(['--path', str(download_dir)])
        
        return args
    
    def get_temp_file(self) -> Optional[str]:
        return self._temp_file


class YouTubeSource(BaseSource):
    """YouTube playlist source."""
    
    def __init__(self, playlist_url: str) -> None:
        super().__init__()
        self.playlist_url = playlist_url.strip()
    
    @property
    def name(self) -> str:
        return "YouTube Playlist"
    
    def validate(self) -> Optional[str]:
        if not self.playlist_url:
            return "No YouTube playlist URL specified."
        return None
    
    def get_tracks(self) -> List[str]:
        # YouTube tracks are fetched dynamically via sldl --print tracks
        # This is handled externally for now
        return []
    
    def get_sldl_input(self) -> str:
        return self.playlist_url


class SpotifySource(BaseSource):
    """Spotify playlist source."""
    
    def __init__(self, playlist_url: str) -> None:
        super().__init__()
        self.playlist_url = playlist_url.strip()
    
    @property
    def name(self) -> str:
        return "Spotify Playlist"
    
    def validate(self) -> Optional[str]:
        if not self.playlist_url:
            return "No Spotify playlist URL specified."
        return None
    
    def get_tracks(self) -> List[str]:
        # Spotify tracks are fetched dynamically via sldl --print tracks
        # This is handled externally for now
        return []
    
    def get_sldl_input(self) -> str:
        return self.playlist_url


class CSVSource(BaseSource):
    """CSV file source."""
    
    def __init__(self, csv_path: str, clean_search: bool = False) -> None:
        super().__init__()
        self.csv_path = csv_path.strip()
        self.clean_search = clean_search
        self._effective_path: Optional[str] = None
    
    @property
    def name(self) -> str:
        return "CSV File"
    
    @property
    def uses_timestamped_folder(self) -> bool:
        return True
    
    def validate(self) -> Optional[str]:
        if not self.csv_path:
            return "No CSV file specified."
        if not Path(self.csv_path).exists():
            return f"CSV file not found: {self.csv_path}"
        return None
    
    def get_tracks(self) -> List[str]:
        """Read tracks from CSV file."""
        tracks: List[str] = []
        try:
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'title' in row and 'artist' in row and row['artist'] and row['title']:
                        tracks.append(f"{row['artist']} - {row['title']}")
                    elif 'title' in row and row['title']:
                        tracks.append(row['title'])
        except Exception:
            pass
        return tracks
    
    def get_sldl_input(self) -> str:
        """Get input path, optionally creating sanitized copy."""
        if self._effective_path is not None:
            return self._effective_path
        
        if self.clean_search:
            sanitized = create_sanitized_copy_of_csv(self.csv_path)
            if sanitized:
                self._temp_file = sanitized
                self._effective_path = sanitized
                return sanitized
        
        self._effective_path = self.csv_path
        return self.csv_path
    
    def get_download_dir(self, base_path: str, timestamp: str) -> Path:
        base = Path(base_path) if base_path else Path.cwd()
        return base / f"csv_{timestamp}"
    
    def build_base_args(self, config: SourceConfig) -> List[str]:
        args: List[str] = [
            self.get_sldl_input(),
            '--input-type', 'csv',
            '--user', config.username,
            '--pass', config.password,
        ]
        
        download_dir = self.get_download_dir(config.download_path, config.timestamp)
        args.extend(['--path', str(download_dir)])
        
        return args


class WishlistSource(BaseSource):
    """Internal wishlist source."""
    
    def __init__(self, clean_search: bool = False) -> None:
        super().__init__()
        self.clean_search = clean_search
        self._csv_path: Optional[str] = None
    
    @property
    def name(self) -> str:
        return "Wishlist"
    
    @property
    def uses_timestamped_folder(self) -> bool:
        return True
    
    def validate(self) -> Optional[str]:
        items = load_wishlist_items()
        if not items:
            return "Wishlist is empty."
        return None
    
    def get_tracks(self) -> List[str]:
        """Get tracks from wishlist."""
        return load_wishlist_items()
    
    def get_sldl_input(self) -> str:
        """Create temp CSV from wishlist."""
        if self._csv_path is not None:
            return self._csv_path
        
        csv_path = create_csv_from_wishlist(self.clean_search)
        if csv_path:
            self._csv_path = csv_path
            self._temp_file = csv_path
            return csv_path
        
        return ""
    
    def get_download_dir(self, base_path: str, timestamp: str) -> Path:
        base = Path(base_path) if base_path else Path.cwd()
        return base / f"wishlist_{timestamp}"
    
    def build_base_args(self, config: SourceConfig) -> List[str]:
        sldl_input = self.get_sldl_input()
        if not sldl_input:
            return []
        
        args: List[str] = [
            sldl_input,
            '--input-type', 'csv',
            '--user', config.username,
            '--pass', config.password,
        ]
        
        download_dir = self.get_download_dir(config.download_path, config.timestamp)
        args.extend(['--path', str(download_dir)])
        
        return args


def create_source(source_type: str, **kwargs) -> Optional[BaseSource]:
    """Factory function to create appropriate source based on type.
    
    Args:
        source_type: One of "YouTube Playlist", "Spotify Playlist", "CSV File", "Wishlist"
        **kwargs: Source-specific arguments:
            - playlist_url: for YouTube/Spotify
            - csv_path: for CSV
            - clean_search: for CSV/Wishlist (optional, defaults to False)
    
    Returns:
        Source instance or None if source_type is unknown
    """
    clean_search = kwargs.get('clean_search', False)
    
    if source_type == "YouTube Playlist":
        return YouTubeSource(kwargs.get('playlist_url', ''))
    elif source_type == "Spotify Playlist":
        return SpotifySource(kwargs.get('playlist_url', ''))
    elif source_type == "CSV File":
        return CSVSource(kwargs.get('csv_path', ''), clean_search=clean_search)
    elif source_type == "Wishlist":
        return WishlistSource(clean_search=clean_search)
    
    return None


def build_sldl_args(config: SourceConfig) -> List[str]:
    """Build common sldl arguments from config (port, concurrency, format, bitrate)."""
    args: List[str] = []
    
    if config.listen_port and config.listen_port.isdigit():
        args.extend(['--listen-port', config.listen_port])
    
    if config.concurrent_downloads:
        args.extend(['--concurrent-downloads', config.concurrent_downloads])
    
    # Preferred format/bitrate
    if config.pref_format and config.pref_format != "Any":
        args.extend(['--pref-format', config.pref_format])
    
    if config.pref_min_bitrate and config.pref_min_bitrate.isdigit():
        args.extend(['--pref-min-bitrate', config.pref_min_bitrate])
    
    if config.pref_max_bitrate and config.pref_max_bitrate.isdigit():
        args.extend(['--pref-max-bitrate', config.pref_max_bitrate])
    
    # Strict format/bitrate
    if config.strict_format and config.strict_format != "Any":
        args.extend(['--format', config.strict_format])
    
    if config.strict_min_bitrate and config.strict_min_bitrate.isdigit():
        args.extend(['--min-bitrate', config.strict_min_bitrate])
    
    if config.strict_max_bitrate and config.strict_max_bitrate.isdigit():
        args.extend(['--max-bitrate', config.strict_max_bitrate])
    
    return args

