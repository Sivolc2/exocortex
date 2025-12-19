import os
import asyncio
import discord
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base_fetcher import BaseFetcher

class DiscordFetcher(BaseFetcher):
    """
    Fetches chat logs from Discord channels using a Discord bot.
    
    Requires:
    - DISCORD_BOT_TOKEN set in .env file
    - Bot must be added to the server with proper permissions
    - server_id and channel_ids configured in config.yaml
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.token = os.getenv("DISCORD_BOT_TOKEN")
        self.server_id = int(config.get("server_id")) if config.get("server_id") else None
        # Handle both numeric IDs and channel names
        self.channel_identifiers = config.get("channel_ids", [])
        self.message_limit = config.get("message_limit", 100)  # Limit messages per channel
        self.days_back = config.get("days_back", 30)  # How many days back to fetch

    def fetch(self) -> List[Dict[str, Any]]:
        """Fetch messages from Discord channels synchronously."""
        if not self.token:
            print("WARN: DISCORD_BOT_TOKEN not configured. Cannot fetch from Discord.")
            return []
        if not self.server_id or not self.channel_identifiers:
            print("WARN: Discord server_id or channel_ids not configured in config.yaml.")
            return []

        try:
            # Run the async fetch in a new event loop
            return asyncio.run(self._async_fetch())
        except Exception as e:
            print(f"ERROR: Failed to fetch Discord messages: {e}")
            return []

    async def _async_fetch(self) -> List[Dict[str, Any]]:
        """Asynchronously fetch messages from Discord channels."""
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message content
        
        client = discord.Client(intents=intents)
        
        try:
            await client.login(self.token)
            
            # Get the guild (server) - need to get it with channels
            guild = client.get_guild(self.server_id)
            if not guild:
                # Try to fetch it instead
                try:
                    guild = await client.fetch_guild(self.server_id, with_counts=False)
                    print(f"INFO: Fetched guild '{guild.name}' via API")
                except Exception as e:
                    print(f"ERROR: Could not access server with ID {self.server_id}: {e}")
                    return []
            else:
                print(f"INFO: Found guild '{guild.name}' in bot's cache")
            
            documents = []
            
            # Get all channels in the guild for name-to-ID mapping
            guild_channels = {}
            
            # Get channels from the guild object
            text_channels = guild.text_channels if hasattr(guild, 'text_channels') else []
            if not text_channels:
                # If no channels in guild object, try fetching them manually
                print("INFO: No channels found in guild object, fetching manually...")
                try:
                    channels = await guild.fetch_channels()
                    for channel in channels:
                        if hasattr(channel, 'type') and channel.type == discord.ChannelType.text:
                            text_channels.append(channel)
                except Exception as e:
                    print(f"WARN: Could not fetch channels: {e}")
            
            for channel in text_channels:
                guild_channels[channel.name] = channel.id
                guild_channels[str(channel.id)] = channel.id  # Also allow numeric IDs as strings
            
            print(f"INFO: Found {len(guild_channels)} text channels in server: {list(guild_channels.keys())}")
            
            for channel_identifier in self.channel_identifiers:
                try:
                    # Try to resolve channel name to ID
                    if channel_identifier in guild_channels:
                        channel_id = guild_channels[channel_identifier]
                        print(f"INFO: Resolved '{channel_identifier}' to channel ID {channel_id}")
                    else:
                        # Try to parse as numeric ID
                        try:
                            channel_id = int(channel_identifier)
                        except ValueError:
                            print(f"ERROR: Could not resolve channel '{channel_identifier}'. Available channels: {list(guild_channels.keys())}")
                            continue
                    
                    channel = await client.fetch_channel(channel_id)
                    if not channel:
                        print(f"WARN: Could not access channel with ID {channel_id}")
                        continue
                    
                    print(f"INFO: Fetching messages from #{channel.name}")
                    
                    # Fetch messages
                    messages = []
                    async for message in channel.history(limit=self.message_limit):
                        # Skip bot messages and system messages
                        if message.author.bot or message.type != discord.MessageType.default:
                            continue
                        
                        messages.append({
                            'id': str(message.id),
                            'author': str(message.author),
                            'author_id': str(message.author.id),
                            'content': message.content,
                            'timestamp': message.created_at.isoformat(),
                            'edited_at': message.edited_at.isoformat() if message.edited_at else None,
                            'attachments': [att.url for att in message.attachments],
                            'embeds': [embed.to_dict() for embed in message.embeds],
                            'reactions': [{'emoji': str(reaction.emoji), 'count': reaction.count} 
                                        for reaction in message.reactions]
                        })
                    
                    # Reverse to get chronological order
                    messages.reverse()
                    
                    if messages:
                        # Create a document for this channel
                        content = self._format_messages_as_markdown(messages, channel.name)
                        
                        doc = {
                            "source": "discord",
                            "id": f"{guild.id}-{channel.id}",
                            "content": content,
                            "metadata": {
                                "server_name": guild.name,
                                "server_id": str(guild.id),
                                "channel_name": channel.name,
                                "channel_id": str(channel.id),
                                "message_count": len(messages),
                                "fetched_at": datetime.now(timezone.utc).isoformat(),
                                "oldest_message": messages[0]['timestamp'] if messages else None,
                                "newest_message": messages[-1]['timestamp'] if messages else None
                            }
                        }
                        documents.append(doc)
                        print(f"INFO: Fetched {len(messages)} messages from #{channel.name}")
                
                except Exception as e:
                    print(f"ERROR: Failed to fetch from channel {channel_identifier}: {e}")
                    continue
            
            return documents
            
        finally:
            await client.close()

    def _format_messages_as_markdown(self, messages: List[Dict], channel_name: str) -> str:
        """Format Discord messages as readable Markdown."""
        content = f"# Discord Channel: #{channel_name}\n\n"
        
        current_date = None
        for msg in messages:
            # Parse timestamp
            msg_time = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
            msg_date = msg_time.strftime('%Y-%m-%d')
            
            # Add date header if it's a new day
            if current_date != msg_date:
                content += f"\n## {msg_date}\n\n"
                current_date = msg_date
            
            # Format message
            timestamp = msg_time.strftime('%H:%M')
            author = msg['author']
            message_content = msg['content']
            
            # Escape special markdown characters in content
            message_content = message_content.replace('*', r'\*').replace('_', r'\_').replace('`', r'\`')
            
            content += f"**{author}** *({timestamp})*: {message_content}\n"
            
            # Add attachments
            if msg['attachments']:
                for attachment in msg['attachments']:
                    content += f"  📎 Attachment: {attachment}\n"
            
            # Add reactions
            if msg['reactions']:
                reactions_str = ' '.join([f"{r['emoji']}({r['count']})" for r in msg['reactions']])
                content += f"  Reactions: {reactions_str}\n"
            
            # Add edit info
            if msg['edited_at']:
                edit_time = datetime.fromisoformat(msg['edited_at'].replace('Z', '+00:00'))
                content += f"  *(edited at {edit_time.strftime('%H:%M')})*\n"
            
            content += "\n"
        
        return content