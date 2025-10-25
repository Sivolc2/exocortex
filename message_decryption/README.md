# Matrix Chat Exporter

Automated Matrix/Element chat export system that solves the "Unable to decrypt message" problem by regularly backing up your chats via the Matrix API.

## Quick Start

1. **Install dependencies:**
   ```bash
   ./install_requirements.sh
   ```

2. **Get your Matrix access token:**
   - Open Element in browser
   - Settings → Help & About → Access Token
   - Copy the token

3. **Initial setup:**
   ```bash
   python3 schedule_matrix_export.py --run-once
   ```
   This creates `matrix_config.json` - edit it with your credentials.

4. **Test the export:**
   ```bash
   python3 schedule_matrix_export.py --run-once
   ```

## Configuration

Edit `matrix_config.json`:

```json
{
  "homeserver": "https://matrix.org",
  "username": "@your_username:matrix.org",
  "access_token": "your_access_token_here",
  "output_directory": "matrix_exports",
  "schedule": {
    "frequency": "daily",
    "time": "02:00"
  },
  "max_backups": 30
}
```

## Scheduling Options

### Option 1: Python Scheduler (Simple)
```bash
python3 schedule_matrix_export.py
```
Runs continuously with built-in scheduling.

### Option 2: macOS LaunchAgent (Recommended)
```bash
python3 setup_launchd.py
launchctl load ~/Library/LaunchAgents/com.user.matrix-exporter.plist
```
Native macOS scheduling, runs in background.

### Option 3: Manual/Cron
```bash
# Add to crontab for daily 2 AM exports
0 2 * * * cd /Users/starsong/Downloads/ai_import && python3 schedule_matrix_export.py --run-once
```

## Output Format

- **Individual room files:** `matrix_exports/export_TIMESTAMP/RoomName.md`
- **Complete JSON backup:** `complete_export_TIMESTAMP.json`
- **Automatic cleanup:** Keeps only last 30 exports

## Solving E2EE Decryption Issues

This approach bypasses Element's export limitations by:
- Using Matrix API directly (no E2EE export issues)
- Regular automated backups prevent data loss
- Preserves all message history and metadata
- Works across device changes and session resets

## Commands

- `python3 matrix_chat_exporter.py --homeserver https://matrix.org --username @user:matrix.org --token TOKEN`
- `python3 schedule_matrix_export.py --run-once` (single export)
- `python3 schedule_matrix_export.py` (continuous scheduling)
- `python3 setup_launchd.py` (setup macOS automation)