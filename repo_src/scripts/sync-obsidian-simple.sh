#!/bin/bash

# Simple sync Obsidian vault to documents folder (no backup)
# Usage: ./sync-obsidian-simple.sh /path/to/obsidian/vault [subfolder]

set -e

OBSIDIAN_PATH="$1"
SUBFOLDER="$2"
DOCUMENTS_DIR="$(dirname "$0")/../backend/documents"

if [ -z "$OBSIDIAN_PATH" ]; then
    echo "Usage: $0 /path/to/obsidian/vault [subfolder]"
    echo "Example: $0 ~/Documents/MyVault"
    echo "Example: $0 ~/Documents/MyVault project-notes"
    exit 1
fi

if [ ! -d "$OBSIDIAN_PATH" ]; then
    echo "Error: Obsidian vault not found at $OBSIDIAN_PATH"
    exit 1
fi

SOURCE_PATH="$OBSIDIAN_PATH"
if [ -n "$SUBFOLDER" ]; then
    SOURCE_PATH="$OBSIDIAN_PATH/$SUBFOLDER"
    if [ ! -d "$SOURCE_PATH" ]; then
        echo "Error: Subfolder $SUBFOLDER not found in vault"
        exit 1
    fi
fi

echo "Syncing from $SOURCE_PATH to $DOCUMENTS_DIR"

# Create documents directory if it doesn't exist
mkdir -p "$DOCUMENTS_DIR"

# Remove existing markdown files first
echo "Cleaning existing markdown files..."
find "$DOCUMENTS_DIR" -name "*.md" -type f -delete 2>/dev/null || true

# Copy markdown files
echo "Copying markdown files..."
find "$SOURCE_PATH" -name "*.md" -type f | while read -r file; do
    filename=$(basename "$file")
    echo "  Copying $filename"
    cp "$file" "$DOCUMENTS_DIR/"
done

echo "Sync complete!"
echo "Found $(find "$DOCUMENTS_DIR" -name "*.md" | wc -l) markdown files in documents folder" 