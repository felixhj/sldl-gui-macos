from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, ClassVar
import json


SETTINGS_FILE: Path = Path.home() / ".soulseek_downloader_settings.json"


@dataclass
class Settings:
    """Typed representation of persisted application settings.

    Only contains data; no UI logic. Unknown keys in the underlying JSON are
    ignored on load and never written back on save.
    """

    selected_source: str = "YouTube Playlist"  # One of: YouTube Playlist, Spotify Playlist, Wishlist, CSV File
    playlist_url: str = ""
    spotify_url: str = ""
    csv_file_path: str = ""

    username: str = ""
    password: str = ""  # Saved only if remember_password is True
    remember_password: bool = False

    download_path: str = ""

    listen_port: str = ""  # Keep as string to match UI field
    concurrent_downloads: str = "2"  # UI uses string values "1".."4"

    # Preferred/strict format and bitrates (kept as strings to mirror UI fields)
    pref_format: str = "Any"
    strict_format: str = "Any"
    pref_min_bitrate: str = ""
    pref_max_bitrate: str = ""
    strict_min_bitrate: str = ""
    strict_max_bitrate: str = ""

    # Feature toggles
    wishlist_mode: bool = False
    clean_search: bool = False

    # Reserved for future additions; allows safe expansion without breaking older JSON
    _extras: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    # Class constants for validation
    ALLOWED_SOURCES: ClassVar[set[str]] = {"YouTube Playlist", "Spotify Playlist", "Wishlist", "CSV File"}
    ALLOWED_CONCURRENT: ClassVar[set[str]] = {"1", "2", "3", "4"}

    @staticmethod
    def load(path: Path = SETTINGS_FILE) -> Settings:
        """Load settings from JSON file, providing sane defaults when missing."""
        if not path.exists():
            return Settings()

        try:
            with path.open("r", encoding="utf-8") as f:
                raw: Dict[str, Any] = json.load(f)
        except Exception:
            # Corrupt or unreadable file: fall back to defaults
            return Settings()

        # Extract known fields, ignore unknowns
        known: Dict[str, Any] = {}
        extras: Dict[str, Any] = {}
        for key, value in raw.items():
            if key in Settings.__dataclass_fields__:
                known[key] = value
            else:
                extras[key] = value

        s = Settings(**known)
        s._extras = extras
        s.validate()
        return s

    def save(self, path: Path = SETTINGS_FILE) -> None:
        """Persist settings, excluding unknown fields unless still present in file."""
        # Persist only known, public fields
        serializable = asdict(self)
        serializable.pop("_extras", None)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)
        except Exception:
            # Silent failure to avoid crashing the UI on save
            pass

    def validate(self) -> None:
        """Clamp or sanitize values to safe ranges expected by the app."""
        # Selected source
        if self.selected_source not in self.ALLOWED_SOURCES:
            self.selected_source = "YouTube Playlist"

        # Concurrent downloads (string values "1".."4")
        if self.concurrent_downloads not in self.ALLOWED_CONCURRENT:
            self.concurrent_downloads = "2"

        # Port must be digits or empty; keep as string to match UI field semantics
        if self.listen_port and not str(self.listen_port).isdigit():
            self.listen_port = ""

        # Normalize empty strings for bitrates; keep only digits
        for key in [
            "pref_min_bitrate",
            "pref_max_bitrate",
            "strict_min_bitrate",
            "strict_max_bitrate",
        ]:
            val = getattr(self, key, "")
            if val and not str(val).isdigit():
                setattr(self, key, "")

