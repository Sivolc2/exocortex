# Gmail MCP Server Setup

This guide explains how to set up the Gmail MCP server to access your Gmail messages.

## Prerequisites

1. A Google account with Gmail
2. Python environment with required dependencies installed

## Setup Steps

### 1. Install Dependencies

```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Or if using the project's virtual environment:

```bash
source .venv/bin/activate
pip install -r repo_src/backend/requirements.txt
```

### 2. Create Google Cloud Project and Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

### 3. Create OAuth 2.0 Credentials

1. In Google Cloud Console, go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: External (for personal use) or Internal (for workspace)
   - Add your email as a test user
   - Scopes: Add `gmail.readonly` scope
4. Application type: "Desktop app"
5. Name: "Exocortex Gmail MCP"
6. Click "Create"
7. Download the credentials JSON file

### 4. Save Credentials

1. Create the credentials directory:
   ```bash
   mkdir -p .credentials
   ```

2. Save the downloaded JSON file as:
   ```bash
   .credentials/gmail_credentials.json
   ```

### 5. First-Time Authentication

When you first run the Gmail MCP server, it will open a browser window for authentication:

```bash
python repo_src/backend/gmail_mcp_server.py
```

1. Sign in with your Google account
2. Grant the requested permissions (read-only access to Gmail)
3. The server will save an access token to `.credentials/gmail_token.json`
4. Future runs will use this token (it auto-refreshes when expired)

## Using the Gmail MCP Server

### Running the Server

```bash
python repo_src/backend/gmail_mcp_server.py
```

### Available Tools

1. **search_emails**: Search emails using Gmail query syntax
   - Query examples:
     - `from:sender@example.com`
     - `subject:meeting`
     - `after:2024/01/01 before:2024/12/31`
     - `is:unread`
     - `has:attachment`

2. **get_email**: Get full content of a specific email by message ID

3. **get_recent_emails**: Get recent emails from the last N days

4. **get_email_stats**: Get statistics about your Gmail account

### Gmail Query Syntax Reference

Common search operators:
- `from:sender@example.com` - Emails from a specific sender
- `to:recipient@example.com` - Emails to a specific recipient
- `subject:keyword` - Emails with keyword in subject
- `after:YYYY/MM/DD` - Emails after a date
- `before:YYYY/MM/DD` - Emails before a date
- `is:unread` - Unread emails
- `is:starred` - Starred emails
- `has:attachment` - Emails with attachments
- `label:labelname` - Emails with a specific label

You can combine multiple operators:
```
from:boss@example.com after:2024/01/01 has:attachment
```

## Configuring with Claude Code

To use this MCP server with Claude Code, add it to your Claude Code MCP settings.

## Security Notes

- The credentials files contain sensitive authentication data
- `.credentials/` directory is gitignored by default
- The server only requests read-only access to Gmail
- Tokens are stored locally and auto-refresh

## Troubleshooting

### "Gmail API libraries not installed"
Run: `pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client`

### "Gmail credentials not found"
Make sure you've downloaded and saved the OAuth credentials to `.credentials/gmail_credentials.json`

### "Invalid grant" or authentication errors
Delete `.credentials/gmail_token.json` and re-authenticate

### API quota limits
Gmail API has daily quota limits. For personal use, the default quotas should be sufficient.
