#!/usr/bin/env python3

import asyncio
import json
from matrix_aggregator.client import MatrixClient

async def debug_backup():
    """Debug backup structure"""
    
    with open('matrix_config.json', 'r') as f:
        config = json.load(f)
    
    async with MatrixClient(config['homeserver'], config['access_token']) as client:
        # Get backup info
        backup_info = await client.get_room_keys_backup()
        print("Backup Info:")
        print(json.dumps(backup_info, indent=2))
        
        if backup_info:
            version = backup_info.get('version')
            print(f"\nTrying to get room keys for a specific room...")
            
            # Get one room's keys to see structure
            try:
                room_keys = await client.get_room_keys("!02wWYxhO40WfUMcOAWCd:beeper.local", version)
                print("\nSample Room Keys Structure:")
                print(json.dumps(room_keys, indent=2))
                
                # Check one session structure
                sessions = room_keys.get('sessions', {})
                if sessions:
                    session_id = list(sessions.keys())[0]
                    session_data = sessions[session_id]
                    print(f"\nSample Session Data for {session_id}:")
                    print(json.dumps(session_data, indent=2))
                    
            except Exception as e:
                print(f"Error getting room keys: {e}")

if __name__ == "__main__":
    asyncio.run(debug_backup())