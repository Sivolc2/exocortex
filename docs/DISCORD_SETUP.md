# Discord Bot Setup Guide

Your Discord fetcher has been implemented! Here's how to set it up and use it.

## Bot Configuration

Your bot token is already configured in `.env`:
```
DISCORD_BOT_TOKEN=""
```

Application ID: ``

## Required Bot Permissions

Your bot needs these permissions to function properly:
- **Read Messages** - To access message history
- **Read Message History** - To fetch historical messages
- **View Channels** - To see the channels you want to fetch from

## Getting Server and Channel IDs

To configure which Discord server and channels to fetch from:

1. **Enable Developer Mode** in Discord:
   - Go to User Settings (gear icon)
   - Go to Advanced → Enable Developer Mode

2. **Get Server ID**:
   - Right-click on your server name → Copy Server ID

3. **Get Channel IDs**:
   - Right-click on each channel you want to fetch → Copy Channel ID

## Configuration

Update `config.yaml` with your actual server and channel IDs:

```yaml
data_sources:
  discord:
    enabled: true
    server_id: "YOUR_ACTUAL_SERVER_ID"  # Replace this
    channel_ids:  # Replace these with actual channel IDs
      - "YOUR_CHANNEL_ID_1"
      - "YOUR_CHANNEL_ID_2"
    message_limit: 100  # Messages per channel (adjust as needed)
    days_back: 30  # Currently unused, for future date filtering
```

## Testing the Implementation

1. **Quick Test**:
   ```bash
   python test_discord_fetcher.py
   ```
   Note: Update the server_id and channel_ids in the test script first.

2. **Full Integration Test**:
   ```bash
   python repo_src/scripts/combine_sources.py
   ```
   This will run all enabled data sources and create a combined output file.

## Bot Invitation URL

If you need to re-invite the bot to your server, use this URL (replace YOUR_SERVER_ID):
```
https://discord.com/oauth2/authorize?client_id=1405379030701576202&permissions=65536&scope=bot&guild_id=YOUR_SERVER_ID
```

The permissions=65536 gives the bot "Read Message History" permission.

## Output Format

The Discord fetcher creates documents with this structure:
- **Source**: "discord"
- **ID**: "{server_id}-{channel_id}"
- **Content**: Formatted markdown with messages organized by date
- **Metadata**: Server info, channel info, message counts, timestamps

Messages are formatted as:
```markdown
# Discord Channel: #channel-name

## 2024-01-15

**Username** *(14:30)*: Message content here
  📎 Attachment: https://cdn.discord.com/...
  Reactions: 👍(5) ❤️(2)

**AnotherUser** *(14:32)*: Another message
  *(edited at 14:33)*
```

## Troubleshooting

**"Could not access server"**: 
- Check that the bot is invited to your server
- Verify the server_id is correct

**"Could not access channel"**:
- Ensure the bot has permission to view the channel
- Check that channel_ids are correct
- Make sure channels are not private without bot access

**"No messages fetched"**:
- Check if there are recent messages in the channels
- Verify the bot can see message history
- Check message_limit setting

**Authentication errors**:
- Verify DISCORD_BOT_TOKEN in .env is correct
- Check that the token hasn't expired
