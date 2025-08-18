from __future__ import annotations

import csv
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import List, Optional, Set, Dict, Any, Callable


WISHLIST_FILE: Path = Path.home() / ".soulseek_downloader_wishlist.csv"


def load_items() -> List[str]:
    """Load wishlist items from the CSV file."""
    items: List[str] = []
    if WISHLIST_FILE.exists():
        try:
            with open(WISHLIST_FILE, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'combined-string' in row and row['combined-string']:
                        items.append(row['combined-string'])
                    elif 'title' in row and 'artist' in row:
                        if row['artist'] and row['title']:
                            items.append(f"{row['artist']} - {row['title']}")
                        elif row['title'] and not row['artist']:
                            items.append(row['title'])
                    elif 'track' in row and row['track']:
                        items.append(row['track'])
        except Exception:
            pass
    return items


def save_items(items: List[str]) -> None:
    """Save wishlist items to the CSV file."""
    with open(WISHLIST_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['artist', 'title']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            if ' - ' in item:
                artist, title = item.split(' - ', 1)
                writer.writerow({'artist': artist, 'title': title})
            else:
                writer.writerow({'artist': '', 'title': item})


def add_items(new_items: List[str]) -> int:
    """Add new items to the wishlist, avoiding duplicates."""
    try:
        existing = set(load_items())
        to_add = set(new_items) - existing
        if to_add:
            all_items = list(existing) + list(to_add)
            save_items(all_items)
            return len(to_add)
        return 0
    except Exception:
        return 0


def remove_items(remove_list: List[str]) -> int:
    """Remove items from the wishlist."""
    try:
        existing = load_items()
        remove_set = set(remove_list)
        remaining = [item for item in existing if item not in remove_set]
        if len(remaining) != len(existing):
            save_items(remaining)
            return len(existing) - len(remaining)
        return 0
    except Exception:
        return 0


def clean_search_string(text: str) -> str:
    """Clean and normalize search strings by removing diacritics and non-alphanumeric characters."""
    normalized = unicodedata.normalize('NFKD', str(text))
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    ascii_text = re.sub(r'[^A-Za-z0-9]+', ' ', ascii_text)
    ascii_text = re.sub(r'\s+', ' ', ascii_text).strip()
    return ascii_text


def create_csv_from_wishlist(clean_enabled: bool) -> Optional[str]:
    """Create a temporary CSV file from the wishlist items."""
    items = load_items()
    if not items:
        return None
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='')
    writer = csv.writer(temp_file)
    writer.writerow(['artist', 'title'])
    for item in items:
        if ' - ' in item:
            artist, title = item.split(' - ', 1)
            if clean_enabled:
                artist = clean_search_string(artist)
                title = clean_search_string(title)
            writer.writerow([artist, title])
        else:
            title_only = clean_search_string(item) if clean_enabled else item
            writer.writerow(['', title_only])
    temp_file.close()
    return temp_file.name


def create_sanitized_copy_of_csv(csv_path: str, clean_fn: Callable[[str], str] = clean_search_string) -> Optional[str]:
    """Create a sanitized copy of a CSV file using the provided cleaning function."""
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames or []
            has_artist_title = 'artist' in fieldnames and 'title' in fieldnames
            has_track = 'track' in fieldnames
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='')

            if has_artist_title:
                writer = csv.DictWriter(temp_file, fieldnames=['artist', 'title'])
                writer.writeheader()
                for row in reader:
                    artist = clean_fn(row.get('artist', ''))
                    title = clean_fn(row.get('title', ''))
                    if artist or title:
                        writer.writerow({'artist': artist, 'title': title})
            elif has_track:
                writer = csv.DictWriter(temp_file, fieldnames=['track'])
                writer.writeheader()
                for row in reader:
                    track = clean_fn(row.get('track', ''))
                    if track:
                        writer.writerow({'track': track})
            else:
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                writer.writeheader()
                for row in reader:
                    writer.writerow(row)

            temp_file.close()
            return temp_file.name
    except Exception:
        return None


def smart_cross_reference(log_item: Dict[str, Any], wishlist_items: Set[str]) -> Optional[str]:
    """Match log rows against wishlist items across formats and permutations."""
    artist = log_item.get('artist', '')
    title = log_item.get('title', '')
    combined_string = log_item.get('combined_string', '')

    possible: List[str] = []
    if artist and title:
        possible.append(f"{artist} - {title}")
        possible.append(f"{artist} {title}")
        possible.append(f"{title} {artist}")
    elif title and not artist:
        possible.append(title)
        parts = title.split()
        if len(parts) >= 2:
            for i in range(1, len(parts)):
                a = ' '.join(parts[:i])
                t = ' '.join(parts[i:])
                possible.append(f"{a} - {t}")
                possible.append(f"{t} - {a}")
    elif combined_string and not artist and not title:
        possible.append(combined_string)
        parts = combined_string.split()
        if len(parts) >= 2:
            for i in range(1, len(parts)):
                a = ' '.join(parts[:i])
                t = ' '.join(parts[i:])
                possible.append(f"{a} - {t}")
                possible.append(f"{t} - {a}")

    for m in possible:
        if m in wishlist_items:
            return m
    return None

