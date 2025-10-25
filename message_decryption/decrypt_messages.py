#!/usr/bin/env python3

import asyncio
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from matrix_aggregator.client import MatrixClient
from matrix_aggregator.storage import MatrixStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def export_messages_with_metadata(config_path: str):
    """Export messages including encrypted ones with metadata"""
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    output_dir = Path(config['output_directory'])
    db_path = output_dir / 'matrix_messages.db'
    
    if not db_path.exists():
        print("No database found. Run matrix_sync.py first.")
        return
    
    # Connect to database
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Get all rooms with messages
        cursor = conn.execute('''
            SELECT r.room_id, r.name, r.canonical_alias, COUNT(e.event_id) as message_count,
                   COUNT(CASE WHEN e.event_type = 'm.room.encrypted' THEN 1 END) as encrypted_count
            FROM rooms r
            LEFT JOIN events e ON r.room_id = e.room_id 
            WHERE e.event_type IN ('m.room.message', 'm.room.encrypted', 'm.sticker')
            GROUP BY r.room_id
            HAVING message_count > 0
            ORDER BY message_count DESC
        ''')
        
        rooms = [dict(row) for row in cursor.fetchall()]
        
        print(f"\nFound {len(rooms)} rooms with messages:")
        for room in rooms[:10]:  # Show top 10
            name = room['name'] or room['canonical_alias'] or room['room_id']
            print(f"  {name}: {room['message_count']} messages ({room['encrypted_count']} encrypted)")
        
        if len(rooms) > 10:
            print(f"  ... and {len(rooms) - 10} more rooms")
        
        # Export rooms to markdown
        exported_count = 0
        
        for room in rooms:
            room_id = room['room_id']
            room_name = room['name'] or room['canonical_alias'] or room_id
            
            # Get messages for this room
            cursor = conn.execute('''
                SELECT event_id, sender, event_type, content, origin_server_ts
                FROM events 
                WHERE room_id = ? AND event_type IN ('m.room.message', 'm.room.encrypted', 'm.sticker')
                ORDER BY origin_server_ts ASC
            ''', (room_id,))
            
            messages = [dict(row) for row in cursor.fetchall()]
            
            if messages:
                await export_room_with_encrypted_markdown(room_id, room_name, messages, output_dir)
                exported_count += 1
        
        print(f"\n✓ Exported {exported_count} rooms to {output_dir}")
        
        # Create index
        await create_index_file(rooms, output_dir)

async def export_room_with_encrypted_markdown(room_id: str, room_name: str, messages: list, output_dir: Path):
    """Export room to markdown, showing encrypted messages with metadata"""
    
    # Sanitize filename
    safe_name = "".join(c for c in room_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')[:50] or 'unnamed_room'
    
    filename = f"{safe_name}_{room_id.replace('!', '').replace(':', '_')[:20]}.md"
    file_path = output_dir / filename
    
    # Create markdown content
    lines = [
        f"# {room_name}",
        "",
        f"**Room ID:** {room_id}",
        f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Messages:** {len(messages)}",
        f"**Encrypted Messages:** {sum(1 for m in messages if m['event_type'] == 'm.room.encrypted')}",
        "",
        "---",
        ""
    ]
    
    current_date = None
    for msg in messages:
        # Format timestamp
        dt = datetime.fromtimestamp(msg['origin_server_ts'] / 1000)
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
        
        if msg['event_type'] == 'm.room.encrypted':
            lines.extend([
                f"**{sender}** *{time_str}* 🔒",
                "",
                "*[Encrypted message - requires E2EE keys for decryption]*",
                f"```",
                f"Event ID: {msg['event_id']}",
                f"Algorithm: {json.loads(msg['content']).get('algorithm', 'unknown')}",
                f"```",
                ""
            ])
        else:
            # Parse message content
            try:
                content = json.loads(msg['content'])
                body = content.get('body', '[No body]')
                msgtype = content.get('msgtype', 'm.text')
                
                if msgtype == 'm.image':
                    lines.extend([
                        f"**{sender}** *{time_str}* 🖼️",
                        "",
                        f"*[Image: {body}]*",
                        ""
                    ])
                elif msgtype == 'm.file':
                    lines.extend([
                        f"**{sender}** *{time_str}* 📎",
                        "",
                        f"*[File: {body}]*",
                        ""
                    ])
                else:
                    lines.extend([
                        f"**{sender}** *{time_str}*",
                        "",
                        body,
                        ""
                    ])
            except:
                lines.extend([
                    f"**{sender}** *{time_str}*",
                    "",
                    "*[Unable to parse message content]*",
                    ""
                ])
    
    # Write file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

async def create_index_file(rooms: list, output_dir: Path):
    """Create index file with room statistics"""
    index_path = output_dir / "README.md"
    
    total_messages = sum(room['message_count'] for room in rooms)
    total_encrypted = sum(room['encrypted_count'] for room in rooms)
    
    lines = [
        "# Matrix Message Export",
        "",
        f"Export generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total rooms: {len(rooms)}",
        f"Total messages: {total_messages}",
        f"Encrypted messages: {total_encrypted} ({total_encrypted/total_messages*100:.1f}%)",
        "",
        "## Rooms",
        ""
    ]
    
    for room in rooms:
        name = room['name'] or room['canonical_alias'] or 'Unnamed Room'
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')[:50] or 'unnamed_room'
        filename = f"{safe_name}_{room['room_id'].replace('!', '').replace(':', '_')[:20]}.md"
        
        lines.append(f"- [{name}]({filename}) - {room['message_count']} messages ({room['encrypted_count']} encrypted)")
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python decrypt_messages.py <config_path>")
        sys.exit(1)
    
    asyncio.run(export_messages_with_metadata(sys.argv[1]))