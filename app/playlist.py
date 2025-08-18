from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
import csv


def get_playlist_tracks(
    sldl_path: str | Path, 
    source_type: str, 
    source_value: str, 
    temp_wishlist_builder: Optional[Callable[[], Optional[str]]] = None
) -> List[str]:
    """Return tracks from a playlist or CSV/Wishlist by invoking sldl with --print tracks.

    For CSV/Wishlist types, provide a builder to create a temporary sldl-compatible wishlist string file.
    """
    try:
        if source_type in ("YouTube Playlist", "Spotify Playlist"):
            cmd = [str(sldl_path), source_value, '--print', 'tracks']
        elif source_type in ("CSV File", "Wishlist"):
            if temp_wishlist_builder is None:
                return []
            wishlist_file = temp_wishlist_builder()
            if not wishlist_file:
                return []
            cmd = [str(sldl_path), wishlist_file, '--input-type', 'string', '--print', 'tracks']
        else:
            return []

        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        tracks: List[str] = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and ' - ' in line:
                track_name = re.sub(r'\s*\(\d+s\)$', '', line.strip())
                tracks.append(track_name)
        return tracks
    except Exception:
        return []


def export_youtube_playlist_to_csv(sldl_path: str | Path, playlist_url: str, csv_path: Path) -> bool:
    """Export YouTube playlist tracks into a CSV file using sldl output parsing."""
    try:
        cmd = [str(sldl_path), playlist_url, '--print', 'tracks']
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        tracks: List[Dict[str, str]] = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and ' - ' in line and '(' in line and ')' in line:
                artist_title_part = line.split(' (')[0]
                if ' - ' in artist_title_part:
                    artist, title = artist_title_part.split(' - ', 1)
                    duration_formatted = ""
                    duration_match = re.search(r'\((\d+)s\)', line)
                    if duration_match:
                        seconds = int(duration_match.group(1))
                        duration_formatted = f"{seconds // 60}:{seconds % 60:02d}"
                    tracks.append({
                        'title': title.strip(),
                        'artist': artist.strip(),
                        'duration': duration_formatted,
                        'url': playlist_url,
                        'uploader': artist.strip(),
                    })

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['title', 'artist', 'duration', 'url', 'uploader']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(tracks)
        return True
    except Exception:
        return False


def export_spotify_playlist_to_csv(sldl_path: str | Path, playlist_url: str, csv_path: Path) -> bool:
    """Export Spotify playlist tracks into a CSV file using sldl output parsing."""
    try:
        cmd = [str(sldl_path), playlist_url, '--print', 'tracks']
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        tracks: List[Dict[str, str]] = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and ' - ' in line:
                artist, title = line.split(' - ', 1)
                title_clean = re.sub(r'\s*\(\d+s\)$', '', title.strip())
                tracks.append({
                    'title': title_clean,
                    'artist': artist.strip(),
                    'album': '',
                    'duration': '',
                    'url': playlist_url,
                })

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['title', 'artist', 'album', 'duration', 'url']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(tracks)
        return True
    except Exception:
        return False

