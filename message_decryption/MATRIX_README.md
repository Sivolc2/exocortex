# Matrix Message Aggregator

A Python system for downloading and storing Matrix/Beeper messages with Obsidian-friendly Markdown export.

## Features

- **Matrix Client-Server API v3** support with feature detection
- **Efficient sync** with lazy-loaded members and filtered message types
- **Media download** with local caching and Obsidian linking
- **Markdown export** optimized for Obsidian with embedded media
- **Scheduled sync** for automated message aggregation
- **E2EE placeholder** support (encrypted messages marked as such)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure authentication:**
   ```bash
   python setup_auth.py
   ```
   This will prompt for your Matrix credentials and create/update `matrix_config.json`.

3. **Test connection:**
   ```bash
   python test_connection.py matrix_config.json
   ```

## Usage

### One-time sync
```bash
python matrix_sync.py matrix_config.json
```

### Scheduled sync (runs continuously)
```bash
python matrix_sync.py matrix_config.json --schedule
```

### Configuration

The `matrix_config.json` file contains:

```json
{
  "homeserver": "https://matrix.org",
  "username": "your_username",
  "access_token": "your_access_token",
  "output_directory": "matrix_exports",
  "schedule": {
    "frequency": "daily",
    "time": "02:00"
  },
  "max_backups": 30
}
```

## Output Structure

```
matrix_exports/
├── README.md                    # Index of all exported rooms
├── Room_Name_!room_id.md       # Individual room exports
├── Another_Room_!room_id.md
└── media/                      # Downloaded media files
    ├── abc123_media1.jpg
    └── def456_media2.pdf
```

## Obsidian Integration

The exported Markdown files are designed for Obsidian:

- **Room files** include metadata headers and chronological message layout
- **Media files** are linked with relative paths for portability
- **Daily sections** organize messages by date
- **User timestamps** show sender and time for each message

## Technical Details

### API Compliance
- Uses Matrix Client-Server API v3 endpoints
- Implements proper authentication with token refresh handling
- Feature detection via `/_matrix/client/versions` and `/_matrix/client/v3/capabilities`
- Handles rate limiting with exponential backoff

### Storage
- SQLite database for message storage and sync state
- Efficient indexing for room and timestamp queries
- Media cache tracking with local file references

### Sync Strategy
- Creates filtered sync for messages only (excludes typing, presence)
- Lazy-loads room members to reduce bandwidth
- Backfills historical messages up to configurable limit
- Continues from last sync token on subsequent runs

### Media Handling
- Downloads and caches all media attachments
- Supports images, files, audio, video, and stickers
- Generates safe filenames with collision avoidance
- Handles both authenticated and legacy media endpoints

## Limitations

- **E2EE**: Encrypted messages show as placeholders (full E2EE requires additional setup)
- **Rate limits**: Respects server rate limits but may be slow for large histories
- **Memory usage**: Processes rooms sequentially to manage memory

## Troubleshooting

1. **Authentication errors**: Run `python setup_auth.py` to get a fresh token
2. **Connection issues**: Check `matrix_config.json` homeserver URL
3. **Missing media**: Check network connectivity and server media policies
4. **Sync failures**: Check logs in console output for specific error details