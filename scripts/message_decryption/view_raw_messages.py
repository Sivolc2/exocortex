#!/usr/bin/env python3

import sqlite3
import json
import sys
from datetime import datetime
from pathlib import Path

def view_raw_messages(config_path: str, room_name: str = None, limit: int = 10):
    """View raw message data from the database"""
    
    # Load config to get database path
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    output_dir = Path(config['output_directory'])
    db_path = output_dir / 'matrix_messages.db'
    
    if not db_path.exists():
        print("No database found. Run matrix_sync.py first.")
        return
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # If room name provided, find the room
        if room_name:
            cursor = conn.execute('''
                SELECT room_id, name, canonical_alias 
                FROM rooms 
                WHERE name LIKE ? OR canonical_alias LIKE ? OR room_id LIKE ?
            ''', (f'%{room_name}%', f'%{room_name}%', f'%{room_name}%'))
            
            rooms = [dict(row) for row in cursor.fetchall()]
            
            if not rooms:
                print(f"No rooms found matching '{room_name}'")
                return
            elif len(rooms) > 1:
                print("Multiple rooms found:")
                for i, room in enumerate(rooms):
                    name = room['name'] or room['canonical_alias'] or room['room_id']
                    print(f"  {i+1}. {name} ({room['room_id']})")
                return
            
            room_id = rooms[0]['room_id']
            room_display_name = rooms[0]['name'] or rooms[0]['canonical_alias'] or room_id
            
        else:
            # Show available rooms
            cursor = conn.execute('''
                SELECT r.room_id, r.name, r.canonical_alias, COUNT(e.event_id) as message_count
                FROM rooms r
                LEFT JOIN events e ON r.room_id = e.room_id 
                WHERE e.event_type IN ('m.room.message', 'm.room.encrypted')
                GROUP BY r.room_id
                HAVING message_count > 0
                ORDER BY message_count DESC
                LIMIT 20
            ''')
            
            rooms = [dict(row) for row in cursor.fetchall()]
            
            print("Available rooms (top 20 by message count):")
            for i, room in enumerate(rooms):
                name = room['name'] or room['canonical_alias'] or 'Unnamed Room'
                print(f"  {i+1}. {name} - {room['message_count']} messages")
            
            print(f"\nUsage: python view_raw_messages.py {config_path} '<room_name>'")
            return
        
        # Get messages for the selected room
        cursor = conn.execute('''
            SELECT event_id, sender, event_type, content, origin_server_ts, decrypted_content
            FROM events 
            WHERE room_id = ? AND event_type IN ('m.room.message', 'm.room.encrypted')
            ORDER BY origin_server_ts DESC
            LIMIT ?
        ''', (room_id, limit))
        
        messages = [dict(row) for row in cursor.fetchall()]
        
        print(f"\n{'='*60}")
        print(f"Raw Messages from: {room_display_name}")
        print(f"Room ID: {room_id}")
        print(f"Showing {len(messages)} most recent messages")
        print(f"{'='*60}\n")
        
        for i, msg in enumerate(messages, 1):
            dt = datetime.fromtimestamp(msg['origin_server_ts'] / 1000)
            
            print(f"Message {i}:")
            print(f"  Event ID: {msg['event_id']}")
            print(f"  Sender: {msg['sender']}")
            print(f"  Type: {msg['event_type']}")
            print(f"  Timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if msg['event_type'] == 'm.room.encrypted':
                try:
                    content = json.loads(msg['content'])
                    print(f"  Algorithm: {content.get('algorithm', 'unknown')}")
                    print(f"  Session ID: {content.get('session_id', 'unknown')[:20]}...")
                    print(f"  Ciphertext: {content.get('ciphertext', 'unknown')[:50]}...")
                    
                    if msg['decrypted_content']:
                        print(f"  Decrypted: {msg['decrypted_content']}")
                    else:
                        print(f"  Decrypted: [Not available]")
                        
                except Exception as e:
                    print(f"  Content: [Error parsing: {e}]")
            else:
                try:
                    content = json.loads(msg['content'])
                    print(f"  Message Type: {content.get('msgtype', 'unknown')}")
                    print(f"  Body: {content.get('body', '[No body]')}")
                except Exception as e:
                    print(f"  Content: [Error parsing: {e}]")
            
            print(f"  Raw Content: {msg['content'][:100]}...")
            print()

def show_encryption_details(config_path: str):
    """Show detailed encryption information"""
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    output_dir = Path(config['output_directory'])
    db_path = output_dir / 'matrix_messages.db'
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Get encryption algorithm breakdown
        cursor = conn.execute('''
            SELECT 
                json_extract(content, '$.algorithm') as algorithm,
                COUNT(*) as count
            FROM events 
            WHERE event_type = 'm.room.encrypted'
            GROUP BY algorithm
        ''')
        
        algorithms = [dict(row) for row in cursor.fetchall()]
        
        print("Encryption Algorithm Breakdown:")
        for alg in algorithms:
            print(f"  {alg['algorithm']}: {alg['count']} messages")
        
        # Show sample encrypted content structure
        cursor = conn.execute('''
            SELECT content 
            FROM events 
            WHERE event_type = 'm.room.encrypted'
            LIMIT 1
        ''')
        
        sample = cursor.fetchone()
        if sample:
            print(f"\nSample Encrypted Message Structure:")
            try:
                content = json.loads(sample['content'])
                print(json.dumps(content, indent=2))
            except:
                print("Could not parse sample message")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python view_raw_messages.py <config_path>                    # List rooms")
        print("  python view_raw_messages.py <config_path> '<room_name>'      # View messages")
        print("  python view_raw_messages.py <config_path> --encryption       # Show encryption details")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    if len(sys.argv) > 2:
        if sys.argv[2] == '--encryption':
            show_encryption_details(config_path)
        else:
            room_name = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            view_raw_messages(config_path, room_name, limit)
    else:
        view_raw_messages(config_path)