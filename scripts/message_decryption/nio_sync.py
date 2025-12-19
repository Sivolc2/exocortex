#!/usr/bin/env python3

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from nio import AsyncClient, SyncResponse
from nio.events import MegolmEvent, RoomMessageText, RoomMessageMedia, RoomMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def sync_and_export_messages(config_path: str):
    """Sync messages using nio and export to markdown"""
    
    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    homeserver = config['homeserver']
    username = config['username']
    access_token = config['access_token']
    output_dir = Path(config['output_directory'])
    
    # Setup paths
    store_path = output_dir / 'nio_store'
    store_path.mkdir(parents=True, exist_ok=True)
    
    user_id = f"@{username.lower()}:beeper.com"
    
    # Create nio client
    client = AsyncClient(
        homeserver,
        user_id,
        device_id="BEEPER_EXPORT",
        store_path=str(store_path)
    )
    
    try:
        # Set access token and load store
        client.access_token = access_token
        client.load_store()
        
        logger.info(f"Starting sync for {user_id}")
        
        # Perform initial sync
        response = await client.sync(timeout=30000, full_state=False)
        
        if not isinstance(response, SyncResponse):
            logger.error(f"Sync failed: {response}")
            return
        
        logger.info(f"Sync successful - processing {len(response.rooms.join)} rooms")
        
        # Process and export rooms
        exported_count = 0
        
        for room_id, room_info in response.rooms.join.items():
            # Get room name
            room_name = None
            for event in room_info.state:
                if hasattr(event, 'content') and event.type == 'm.room.name':
                    room_name = event.content.get('name')
                    break
            
            if not room_name:
                room_name = room_id
            
            # Collect messages from timeline
            messages = []
            
            for event in room_info.timeline.events:
                message_data = None
                
                if isinstance(event, MegolmEvent):
                    # Encrypted event
                    decrypted = event.decrypted_event
                    if decrypted and hasattr(decrypted, 'body'):
                        message_data = {
                            'sender': event.sender,
                            'timestamp': event.server_timestamp,
                            'body': decrypted.body,
                            'encrypted': True,
                            'msgtype': getattr(decrypted, 'msgtype', 'm.text')
                        }
                
                elif isinstance(event, RoomMessage):
                    # Unencrypted message
                    message_data = {
                        'sender': event.sender,
                        'timestamp': event.server_timestamp,
                        'body': event.body,
                        'encrypted': False,
                        'msgtype': getattr(event, 'msgtype', 'm.text')
                    }
                
                if message_data:
                    messages.append(message_data)
            
            # Export room if it has messages
            if messages:
                await export_room_markdown(room_id, room_name, messages, output_dir)
                exported_count += 1
                logger.info(f"Exported {room_name} with {len(messages)} messages")
        
        logger.info(f"Export complete - {exported_count} rooms exported")
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        
    finally:
        await client.close()

async def export_room_markdown(room_id: str, room_name: str, messages: List[Dict], output_dir: Path):
    """Export room messages to markdown file"""
    
    # Sanitize filename
    safe_name = "".join(c for c in room_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')[:50] or 'unnamed_room'
    
    filename = f"{safe_name}_{room_id.replace('!', '').replace(':', '_')[:20]}.md"
    file_path = output_dir / filename
    
    # Sort messages by timestamp
    messages.sort(key=lambda m: m['timestamp'])
    
    # Create markdown content
    lines = [
        f"# {room_name}",
        "",
        f"**Room ID:** {room_id}",
        f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Message Count:** {len(messages)}",
        "",
        "---",
        ""
    ]
    
    current_date = None
    for msg in messages:
        # Format timestamp
        dt = datetime.fromtimestamp(msg['timestamp'] / 1000)
        msg_date = dt.date()
        
        # Add date header if date changed
        if current_date != msg_date:
            current_date = msg_date
            lines.extend([
                "",
                f"## {msg_date.strftime('%A, %B %d, %Y')}",
                ""
            ])
        
        # Format message
        time_str = dt.strftime("%H:%M:%S")
        sender = msg['sender']
        body = msg['body']
        encrypted_marker = "🔒 " if msg['encrypted'] else ""
        
        lines.extend([
            f"**{sender}** *{time_str}* {encrypted_marker}",
            "",
            body,
            ""
        ])
    
    # Write file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

async def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python nio_sync.py <config_path>")
        sys.exit(1)
    
    await sync_and_export_messages(sys.argv[1])

if __name__ == "__main__":
    asyncio.run(main())