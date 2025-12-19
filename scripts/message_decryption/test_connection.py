#!/usr/bin/env python3

import asyncio
import json
import sys
from matrix_aggregator.client import MatrixClient

async def test_connection(config_path: str):
    """Test Matrix connection and authentication"""
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"Testing connection to {config['homeserver']}...")
    print(f"Username: {config['username']}")
    
    async with MatrixClient(config['homeserver'], config['access_token']) as client:
        try:
            # Test basic connectivity
            versions = await client.get_versions()
            print(f"✓ Server supports API versions: {versions.get('versions', [])}")
            
            # Test authentication
            whoami = await client.whoami()
            print(f"✓ Authenticated as: {whoami['user_id']}")
            
            # Test capabilities
            try:
                capabilities = await client.get_capabilities()
                print(f"✓ Server capabilities available")
            except Exception as e:
                print(f"⚠ Could not fetch capabilities: {e}")
            
            # Test sync with timeout=0 for quick response
            print("Testing sync...")
            sync_result = await client.sync(timeout=0)
            
            joined_rooms = len(sync_result.get('rooms', {}).get('join', {}))
            print(f"✓ Sync successful - found {joined_rooms} joined rooms")
            
            # List some rooms
            if joined_rooms > 0:
                print("\nSample rooms:")
                for room_id, room_data in list(sync_result['rooms']['join'].items())[:5]:
                    room_name = "Unknown"
                    for event in room_data.get('state', {}).get('events', []):
                        if event['type'] == 'm.room.name':
                            room_name = event.get('content', {}).get('name', 'Unknown')
                            break
                    print(f"  - {room_name} ({room_id})")
            
            print("\n✓ Connection test successful!")
            
        except Exception as e:
            print(f"✗ Connection test failed: {e}")
            print("\nTroubleshooting:")
            print("1. Check if your access token is valid")
            print("2. Verify the homeserver URL is correct")
            print("3. Ensure you have permission to access the Matrix API")
            return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_connection.py <config_path>")
        sys.exit(1)
    
    success = asyncio.run(test_connection(sys.argv[1]))
    sys.exit(0 if success else 1)