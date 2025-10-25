#!/usr/bin/env python3

import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def export_messages_only(config_path: str = "matrix_config.json"):
    """Export all messages without attempting decryption"""
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    db_path = config['output_directory'] + '/matrix_messages.db'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"matrix_export_{timestamp}.jsonl"
    output_path = Path(config['output_directory']) / output_file
    
    exported_count = 0
    encrypted_count = 0
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Get all messages with room information
        cursor = conn.execute("""
            SELECT 
                e.event_id,
                e.room_id,
                r.name as room_name,
                e.sender,
                e.event_type,
                e.content,
                e.decrypted_content,
                e.origin_server_ts,
                datetime(e.origin_server_ts/1000, 'unixepoch') as timestamp
            FROM events e
            LEFT JOIN rooms r ON e.room_id = r.room_id
            WHERE e.event_type IN ('m.room.message', 'm.room.encrypted')
            ORDER BY e.origin_server_ts ASC
        """)
        
        with open(output_path, 'w') as f:
            for row in cursor:
                # Determine message content
                if row['decrypted_content']:
                    # Use decrypted content if available
                    try:
                        message_content = json.loads(row['decrypted_content'])
                    except:
                        message_content = row['decrypted_content']
                else:
                    # Use regular content for unencrypted messages
                    try:
                        message_content = json.loads(row['content'])
                    except:
                        message_content = row['content']
                
                # Create export record
                export_record = {
                    'event_id': row['event_id'],
                    'room_id': row['room_id'],
                    'room_name': row['room_name'],
                    'sender': row['sender'],
                    'event_type': row['event_type'],
                    'content': message_content,
                    'timestamp': row['timestamp'],
                    'origin_server_ts': row['origin_server_ts'],
                    'was_encrypted': row['event_type'] == 'm.room.encrypted',
                    'successfully_decrypted': bool(row['decrypted_content'])
                }
                
                f.write(json.dumps(export_record) + '\n')
                exported_count += 1
                
                if row['event_type'] == 'm.room.encrypted':
                    encrypted_count += 1
    
    logger.info(f"Export complete:")
    logger.info(f"- Total messages: {exported_count}")
    logger.info(f"- Encrypted messages: {encrypted_count}")
    logger.info(f"- Output file: {output_path}")
    
    return str(output_path)

if __name__ == "__main__":
    export_messages_only()