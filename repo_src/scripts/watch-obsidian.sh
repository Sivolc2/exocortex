#!/bin/bash

# Watch Obsidian vault for changes and auto-sync (incremental)
# Usage: ./watch-obsidian.sh /path/to/obsidian/vault [subfolder]

set -e

OBSIDIAN_PATH="$1"
SUBFOLDER="$2"
SCRIPT_DIR="$(dirname "$0")"

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

echo "Watching $SOURCE_PATH for changes (incremental sync)..."
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

# Do initial sync
echo "Performing initial sync..."
"$SCRIPT_DIR/sync-obsidian-incremental.sh" "$OBSIDIAN_PATH" "$SUBFOLDER"

# Watch for changes and use incremental sync
fswatch -o "$SOURCE_PATH" | while read -r num; do
    echo "$(date): Changes detected, syncing only changed files..."
    "$SCRIPT_DIR/sync-obsidian-incremental.sh" "$OBSIDIAN_PATH" "$SUBFOLDER"
    echo "Incremental sync complete. Watching for more changes..."
done 