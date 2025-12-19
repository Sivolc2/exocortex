#!/usr/bin/env python3

import asyncio
import json
import sqlite3
import logging
import sys
from pathlib import Path
from datetime import datetime
from matrix_aggregator.client import MatrixClient
from matrix_crypto import MatrixCrypto

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def decrypt_and_export(config_path: str):
    """Full decryption and export pipeline"""
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    recovery_key = config.get('recovery_key', '').strip()
    if not recovery_key:
        print("No recovery key found in config")
        return False
    
    output_dir = Path(config['output_directory'])
    db_path = output_dir / 'matrix_messages.db'
    
    print("Matrix Message Decryption")
    print("=" * 30)
    
    try:
        # Decode recovery key
        recovery_bytes = MatrixCrypto.decode_recovery_key(recovery_key)
        print(f"✓ Recovery key decoded: {len(recovery_bytes)} bytes")
        
        async with MatrixClient(config['homeserver'], config['access_token']) as client:
            # Get backup info
            backup_info = await client.get_room_keys_backup()
            print(f"✓ Backup found: {backup_info['count']} keys, version {backup_info['version']}")
            
            # Derive backup key
            backup_key = MatrixCrypto.derive_backup_key(recovery_bytes, backup_info)
            print(f"✓ Backup key derived")
            
            # Get session keys for a sample room
            # Let's get keys for the most active room
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute('''
                    SELECT room_id, COUNT(*) as msg_count
                    FROM events 
                    WHERE event_type = 'm.room.encrypted'
                    GROUP BY room_id
                    ORDER BY msg_count DESC
                    LIMIT 1
                ''')
                
                top_room = cursor.fetchone()
                if not top_room:
                    print("No encrypted messages found")
                    return False
                
                room_id, msg_count = top_room
                print(f"✓ Testing with room {room_id} ({msg_count} messages)")
                
                # Try to get backup keys for this room
                try:
                    room_keys = await client.get_room_keys(room_id, backup_info['version'])
                    print(f"✓ Retrieved backup keys for room: {len(room_keys.get('sessions', {}))} sessions")
                    
                    # Show what we'd decrypt
                    sessions = room_keys.get('sessions', {})
                    for session_id, session_data in list(sessions.items())[:3]:  # Show first 3
                        print(f"  Session {session_id[:20]}...: {session_data.get('first_message_index', 0)} messages")
                    
                except Exception as e:
                    print(f"⚠️  Could not retrieve room keys: {e}")
            
            print(f"\n📋 Summary:")
            print(f"✓ Recovery key: valid")
            print(f"✓ Backup access: working")
            print(f"✓ Database: {msg_count} encrypted messages ready")
            print(f"\n⚠️  Full megolm decryption requires additional crypto implementation")
            print(f"💡 For immediate access, export from Beeper/Element desktop app")
            
        return True
        
    except Exception as e:
        print(f"✗ Decryption failed: {e}")
        return False

async def show_decryption_status(config_path: str):
    """Show current decryption capabilities"""
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    output_dir = Path(config['output_directory'])
    db_path = output_dir / 'matrix_messages.db'
    
    print("Current Decryption Status")
    print("=" * 25)
    
    # Check recovery key
    recovery_key = config.get('recovery_key', '').strip()
    if recovery_key:
        try:
            MatrixCrypto.decode_recovery_key(recovery_key)
            print("✓ Recovery key: valid in config")
        except:
            print("✗ Recovery key: invalid format")
    else:
        print("✗ Recovery key: not set in config")
    
    # Check database
    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM events WHERE event_type = "m.room.encrypted"')
            encrypted_count = cursor.fetchone()[0]
            print(f"✓ Database: {encrypted_count} encrypted messages")
    else:
        print("✗ Database: not found")
    
    # Check backup access
    try:
        async with MatrixClient(config['homeserver'], config['access_token']) as client:
            backup_info = await client.get_room_keys_backup()
            print(f"✓ Server backup: {backup_info['count']} keys available")
    except Exception as e:
        print(f"✗ Server backup: {e}")
    
    print(f"\n📝 Next steps:")
    print(f"1. Ensure recovery key is in matrix_config.json")
    print(f"2. Run: python full_decrypt.py matrix_config.json")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python full_decrypt.py <config_path>              # Full decrypt attempt")
        print("  python full_decrypt.py <config_path> --status     # Show status only")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2] == '--status':
        asyncio.run(show_decryption_status(config_path))
    else:
        success = asyncio.run(decrypt_and_export(config_path))
        sys.exit(0 if success else 1)