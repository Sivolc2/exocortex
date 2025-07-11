#!/bin/bash

# Smart watch Obsidian vault for changes - only sync changed files
# Usage: ./watch-obsidian-smart.sh /path/to/obsidian/vault [subfolder]

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

echo "Smart watching $SOURCE_PATH for changes..."
echo "Press Ctrl+C to stop watching"

# Check if fswatch is available
if ! command -v fswatch &> /dev/null; then
    echo "Installing fswatch for file watching..."
    if command -v brew &> /dev/null; then
        brew install fswatch
    else
        echo "Please install fswatch: brew install fswatch"
        exit 1
    fi
fi

# Create documents directory if it doesn't exist
mkdir -p "$DOCUMENTS_DIR"

# Do initial sync
echo "Performing initial sync..."
"$(dirname "$0")/sync-obsidian-incremental.sh" "$OBSIDIAN_PATH" "$SUBFOLDER"

sync_file() {
    local file_path="$1"
    
    # Only process .md files
    if [[ "$file_path" == *.md ]]; then
        local filename=$(basename "$file_path")
        local dest_path="$DOCUMENTS_DIR/$filename"
        
        if [ -f "$file_path" ]; then
            echo "$(date): Syncing changed file: $filename"
            cp "$file_path" "$dest_path"
        elif [ -f "$dest_path" ]; then
            echo "$(date): Removing deleted file: $filename"
            rm "$dest_path"
        fi
    fi
}

# Watch for specific file changes
fswatch -r "$SOURCE_PATH" | while read -r file; do
    sync_file "$file"
done 