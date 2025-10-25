#!/usr/bin/env python3

import asyncio
import json
import base64
from matrix_aggregator.client import MatrixClient
from matrix_crypto import MatrixCrypto

async def debug_session_decryption():
    """Debug session decryption with real data"""
    
    with open('matrix_config.json', 'r') as f:
        config = json.load(f)
    
    async with MatrixClient(config['homeserver'], config['access_token']) as client:
        # Get backup info
        backup_info = await client.get_room_keys_backup()
        version = backup_info.get('version')
        
        # Get a specific room's session for testing
        room_id = "!02wWYxhO40WfUMcOAWCd:beeper.local"
        session_id = "iECKszC1voKuplCZuJL2sab181tBXZzhNSgOt9A1JMk"
        
        print(f"Testing session decryption for:")
        print(f"Room: {room_id}")
        print(f"Session: {session_id}")
        print(f"Backup version: {version}")
        print()
        
        # Get the session data
        room_keys = await client.get_room_keys(room_id, version)
        session_info = room_keys['sessions'][session_id]
        session_data = session_info['session_data']
        
        print("Session data structure:")
        print(json.dumps(session_data, indent=2))
        print()
        
        # Decode the components (handle padding issues)
        def safe_b64decode(data):
            # Add padding if needed
            padding = 4 - (len(data) % 4)
            if padding != 4:
                data += '=' * padding
            return base64.b64decode(data)
        
        ciphertext = safe_b64decode(session_data['ciphertext'])
        ephemeral = safe_b64decode(session_data['ephemeral'])
        mac = safe_b64decode(session_data['mac'])
        
        print(f"Ciphertext length: {len(ciphertext)}")
        print(f"Ephemeral key length: {len(ephemeral)}")
        print(f"MAC length: {len(mac)}")
        print()
        
        # Try to prepare recovery key
        recovery_key = config['recovery_key']
        key_bytes = MatrixCrypto.decode_recovery_key(recovery_key)
        backup_key = MatrixCrypto.derive_backup_key(key_bytes, backup_info)
        
        print(f"Recovery key length: {len(key_bytes)}")
        print(f"Backup key length: {len(backup_key)}")
        print(f"Recovery key hex: {key_bytes.hex()[:40]}...")
        print(f"Backup key hex: {backup_key.hex()[:40]}...")

if __name__ == "__main__":
    asyncio.run(debug_session_decryption())