#!/bin/bash

# Matrix Message Decryption and Export Pipeline
# This script runs the complete pipeline for Matrix message processing

# Navigate to the script's directory
cd "$(dirname "$0")"

echo "Starting Matrix pipeline at $(date)"
echo "========================================"

# Step 1: Sync new messages from the server
echo ""
echo "Step 1: Syncing new messages from Matrix server..."
if python3 matrix_sync.py matrix_config.json; then
    echo "✓ Message sync completed successfully"
else
    echo "✗ Message sync failed"
    exit 1
fi

# Step 2: Decrypt encrypted messages and export everything
echo ""
echo "Step 2: Decrypting messages and exporting..."
if python3 decrypt_and_export.py; then
    echo "✓ Decryption and export completed successfully"
else
    echo "✗ Decryption and export failed"
    exit 1
fi

echo ""
echo "Matrix pipeline completed successfully at $(date)"
echo "==============================================="

# Optional: Show summary statistics
echo ""
echo "Database summary:"
sqlite3 matrix_messages.db "SELECT 
    COUNT(*) as total_events,
    COUNT(CASE WHEN event_type = 'm.room.encrypted' THEN 1 END) as encrypted_events,
    COUNT(CASE WHEN decrypted_content IS NOT NULL THEN 1 END) as decrypted_events
FROM events;"