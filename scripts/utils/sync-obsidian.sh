#!/bin/bash

# Sync Obsidian vault to documents folder
# Usage: ./sync-obsidian.sh /path/to/obsidian/vault [subfolder]

set -e

OBSIDIAN_PATH="$1"
SUBFOLDER="$2"
DOCUMENTS_DIR="$(dirname "$0")/../../datalake/documents"

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

# Create backup if documents folder exists
if [ -d "$DOCUMENTS_DIR" ]; then
    echo "Backing up current documents folder..."
    mv "$DOCUMENTS_DIR" "${DOCUMENTS_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
fi

# Create documents directory
mkdir -p "$DOCUMENTS_DIR"

# Copy markdown files
echo "Copying markdown files..."
find "$SOURCE_PATH" -name "*.md" -type f | while read -r file; do
    filename=$(basename "$file")
    echo "  Copying $filename"
    cp "$file" "$DOCUMENTS_DIR/"
done

echo "Sync complete!"
echo "Found $(find "$DOCUMENTS_DIR" -name "*.md" | wc -l) markdown files in documents folder" 