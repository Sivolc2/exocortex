# Text Message Export Setup

This guide explains how to set up automated text message export from Matrix/Beeper to your exocortex knowledge base.

## Overview

The text message system uses the Matrix protocol (via Beeper) to export encrypted messages to markdown files that can be indexed and searched in your exocortex.

## Current Status

The system is already configured with:
- Matrix aggregator scripts in `scripts/message_decryption/`
- 146 chat exports already processed in `datalake/processed/current/chat_exports/`
- Configuration template at `scripts/message_decryption/matrix_config.json`

## Setup Steps

### 1. Configure Matrix/Beeper Credentials

Edit `scripts/message_decryption/matrix_config.json`:

```json
{
  "homeserver": "https://matrix.beeper.com",
  "username": "YOUR_USERNAME",
  "access_token": "YOUR_ACCESS_TOKEN",
  "recovery_key": "YOUR_RECOVERY_KEY",
  "output_directory": "matrix_exports",
  "schedule": {
    "frequency": "daily",
    "time": "02:00"
  },
  "max_backups": 30
}
```

### 2. Get Your Beeper Access Token

You can use the helper script:

```bash
cd scripts/message_decryption
python get_token.py
```

Or manually:
1. Log in to Beeper
2. In Settings > Advanced, find your access token
3. Copy the access token to the config file

### 3. Run Message Export

One-time sync:

```bash
cd scripts/message_decryption
python -m matrix_aggregator.main matrix_config.json
```

With scheduling (runs daily at configured time):

```bash
python -m matrix_aggregator.main matrix_config.json --schedule
```

### 4. Verify Export

Check that messages are being exported:

```bash
ls -la matrix_exports/
```

Exported messages are in markdown format, organized by room/conversation.

## Available Scripts

### Core Export Scripts

- `matrix_aggregator/main.py` - Main aggregator with scheduling
- `export_messages.py` - Simple export script
- `decrypt_messages.py` - Decrypt encrypted messages

### Utility Scripts

- `get_token.py` - Get Beeper access token
- `test_connection.py` - Test Matrix connection
- `view_raw_messages.py` - View raw message data

### Debugging Scripts

- `debug_session.py` - Debug Matrix session
- `test_decryption.py` - Test message decryption

## Data Flow

1. **Sync**: Matrix client syncs messages from Beeper homeserver
2. **Decrypt**: Encrypted messages are decrypted using E2EE keys
3. **Store**: Messages stored in local SQLite database
4. **Export**: Messages exported to markdown files
5. **Index**: Markdown files indexed by exocortex for search

## Export Format

Messages are exported as markdown files with:
- Timestamp
- Sender information
- Message content
- Media attachments (downloaded separately)
- Metadata (reactions, edits, etc.)

Example export location:
```
matrix_exports/
├── !roomid123/
│   ├── 2024-01-01.md
│   ├── 2024-01-02.md
│   └── media/
│       └── image.jpg
```

## Integration with Exocortex

Exported messages are automatically:
1. Moved to `datalake/processed/current/chat_exports/`
2. Indexed by `scripts/utils/sync_index.py`
3. Available for search via MCP server
4. Included in knowledge base queries

## Running Regular Exports

### Option 1: Manual Run

Run the export script whenever you want to sync:

```bash
pnpm run messages:sync  # If script is added to package.json
```

### Option 2: Scheduled Export

Use the built-in scheduler:

```bash
python -m matrix_aggregator.main matrix_config.json --schedule
```

### Option 3: System Cron Job

Add to your crontab:

```bash
# Daily at 2 AM
0 2 * * * cd /path/to/exocortex/scripts/message_decryption && python -m matrix_aggregator.main matrix_config.json
```

## Troubleshooting

### "Access token invalid"
- Get a fresh token using `get_token.py`
- Update `matrix_config.json` with new token

### "Decryption failed"
- Ensure recovery key is set correctly
- Run `decrypt_with_backup.py` to restore keys

### "No messages exported"
- Check that rooms are being synced: `python test_connection.py`
- Verify output directory permissions

### "Database locked"
- Only one export process can run at a time
- Stop any running sync processes

## Security Notes

- Access tokens are sensitive - never commit to git
- Recovery keys enable message decryption - keep secure
- Messages are stored locally in SQLite database
- Exported markdown files contain your message history

## Next Steps

After setting up message export:

1. Run initial sync to export all historical messages
2. Set up scheduled sync for daily updates
3. Verify messages appear in knowledge base searches
4. Configure message filtering if needed
