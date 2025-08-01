# Wishlist Functionality

The sldl-gui application now supports wishlist functionality, allowing you to use wishlist files as input sources and export failed downloads to wishlist format.

## Features

### 1. Wishlist as Input Source

You can use wishlist files as an input source for batch downloads:

1. Select "Wishlist" from the source dropdown
2. Enter the path to your wishlist file or use the browse button to select it
3. Configure your Soulseek credentials and download settings
4. Click "Start Download" to process the wishlist

### 2. Export Failed Downloads to Wishlist

After a download session, you can export failed downloads to a wishlist file:

1. Go to "Extra Tools" → "Export Failed Downloads to Wishlist"
2. Select a location to save the wishlist file
3. The application will parse the sldl index file and extract failed downloads
4. A new wishlist file will be created with the failed items

### 3. Open Wishlist Files

You can open wishlist files in your default text editor:

1. Go to "Extra Tools" → "Open Wishlist File"
2. Select a wishlist file to open
3. The file will open in your default text editor

## Wishlist File Format

Wishlist files use the sldl list format:

```
# sldl wishlist file
# Format: "input" "conditions" "pref_conditions"
# Example: "Artist - Title" "format=mp3; br>128" "br >= 320"

"Pink Floyd - Wish You Were Here" "" ""
"The Beatles - Let It Be" "" ""
"Led Zeppelin - Stairway to Heaven" "" ""
```

### Format Explanation

- **Input**: The search query (e.g., "Artist - Title" or "artist=Artist,title=Title")
- **Conditions**: Required conditions that must be met (optional)
- **Pref_conditions**: Preferred conditions for better quality (optional)

### Input Formats

You can use various input formats in your wishlist:

1. **Simple format**: `"Artist - Title"`
2. **Structured format**: `"artist=Artist,title=Title"`
3. **Album format**: `"a:Artist - Album"` (for album downloads)
4. **URL format**: Direct URLs to playlists or tracks

## Workflow Example

1. **Download from playlist**: Use YouTube or Spotify playlist as input
2. **Check for failures**: After download completes, check the output for failed items
3. **Export failures**: Use "Export Failed Downloads to Wishlist" to create a wishlist
4. **Retry failed items**: Use the generated wishlist as input source to retry failed downloads
5. **Repeat**: Continue this process until all items are successfully downloaded

## Tips

- Wishlist files are saved as `.txt` files
- The application automatically detects and uses the most recent sldl index file
- Failed downloads are extracted with their original search queries
- You can manually edit wishlist files to add conditions or modify entries
- Use album format (`a:Artist - Album`) for album downloads instead of individual tracks

## Integration with sldl

This functionality integrates with the sldl command-line tool's wishlist features:

- Uses `--input-type list` parameter for wishlist processing
- Parses sldl index files (`.sldl`) to extract failed downloads
- Generates wishlist files in sldl-compatible format
- Supports all sldl wishlist input formats and conditions
