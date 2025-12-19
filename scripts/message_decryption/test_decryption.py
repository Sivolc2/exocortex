#!/usr/bin/env python3

import asyncio
import json
from matrix_aggregator.client import MatrixClient
from matrix_crypto import MatrixCrypto

async def test_single_session():
    """Test decryption of a single session"""
    
    with open('matrix_config.json', 'r') as f:
        config = json.load(f)
    
    async with MatrixClient(config['homeserver'], config['access_token']) as client:
        # Get backup info
        backup_info = await client.get_room_keys_backup()
        version = backup_info.get('version')
        
        # Prepare keys
        recovery_key = config['recovery_key']
        key_bytes = MatrixCrypto.decode_recovery_key(recovery_key)
        backup_key = MatrixCrypto.derive_backup_key(key_bytes, backup_info)
        
        # Get specific session data
        room_id = "!02wWYxhO40WfUMcOAWCd:beeper.local"
        session_id = "iECKszC1voKuplCZuJL2sab181tBXZzhNSgOt9A1JMk"
        
        room_keys = await client.get_room_keys(room_id, version)
        session_info = room_keys['sessions'][session_id]
        session_data = session_info['session_data']
        
        print("Attempting decryption...")
        result = MatrixCrypto.decrypt_session_data(session_data, backup_key)
        
        if result:
            print(f"SUCCESS! Session key: {result[:20]}...")
        else:
            print("FAILED: Could not decrypt session key")

if __name__ == "__main__":
    asyncio.run(test_single_session())