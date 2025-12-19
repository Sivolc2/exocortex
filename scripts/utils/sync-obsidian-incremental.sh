#!/bin/bash

# Incremental sync Obsidian vault to documents folder (only changed/new files)
# Usage: ./sync-obsidian-incremental.sh /path/to/obsidian/vault [subfolder]

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

echo "Incremental sync from $SOURCE_PATH to $DOCUMENTS_DIR"

# Create documents directory if it doesn't exist
mkdir -p "$DOCUMENTS_DIR"

# Check if rsync is available
if ! command -v rsync &> /dev/null; then
    echo "rsync not found. Installing..."
    if command -v brew &> /dev/null; then
        brew install rsync
    else
        echo "Please install rsync: brew install rsync (macOS) or apt-get install rsync (Linux)"
        exit 1
    fi
fi

# Use rsync for incremental sync - only copies changed files
echo "Syncing changed files..."
rsync -av --include="*.md" --exclude="*" --delete "$SOURCE_PATH/" "$DOCUMENTS_DIR/"

echo "Incremental sync complete!"
echo "Found $(find "$DOCUMENTS_DIR" -name "*.md" | wc -l) markdown files in documents folder" 