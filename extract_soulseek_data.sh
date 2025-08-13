#!/bin/bash

# Script to convert SoulSeek binary files to UTF-8 and extract wish list items
# Usage: ./extract_soulseek_data.sh <input_file> [output_csv_file]

# Check if input file is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_file> [output_csv_file]"
    echo "Example: $0 soulseek-client.dat.1754219507676"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_CSV="${2:-soulseek-wishlist-export.csv}"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' not found"
    exit 1
fi

echo "Processing file: $INPUT_FILE"

# Create temporary UTF-8 text file
TEMP_UTF8_FILE=$(mktemp)
echo "Converting binary file to UTF-8..."

# Extract strings from binary file and save as UTF-8
strings "$INPUT_FILE" > "$TEMP_UTF8_FILE"

# Check if conversion was successful
if [ ! -s "$TEMP_UTF8_FILE" ]; then
    echo "Error: Failed to extract text from binary file"
    rm -f "$TEMP_UTF8_FILE"
    exit 1
fi

echo "UTF-8 conversion completed. Extracting wish list items..."

# Extract lines between wish_list_item and is_ignored
# Using awk to find the range and output to CSV
awk '
BEGIN {
    in_wish_list = 0
    csv_output = "'$OUTPUT_CSV'"
    print "track" > csv_output
}

{
    if ($0 == "wish_list_item") {
        in_wish_list = 1
        next
    }
    
    if ($0 == "is_ignored") {
        in_wish_list = 0
        next
    }
    
    if (in_wish_list && $0 != "") {
        # Escape quotes and add to CSV
        gsub(/"/, "\"\"", $0)
        print "\"" $0 "\"" >> csv_output
    }
}

END {
    if (in_wish_list) {
        print "Warning: Found 'wish_list_item' but no matching 'is_ignored' found" > "/dev/stderr"
    }
}
' "$TEMP_UTF8_FILE"

# Check if CSV was created successfully
if [ -f "$OUTPUT_CSV" ]; then
    LINE_COUNT=$(wc -l < "$OUTPUT_CSV")
    echo "Successfully extracted $LINE_COUNT lines to '$OUTPUT_CSV'"
    
    # Show first few lines of the CSV
    echo "First few lines of the CSV file:"
    head -5 "$OUTPUT_CSV"
else
    echo "Warning: No wish list items found between 'wish_list_item' and 'is_ignored'"
fi

# Clean up temporary file
rm -f "$TEMP_UTF8_FILE"

echo "Processing complete!" 