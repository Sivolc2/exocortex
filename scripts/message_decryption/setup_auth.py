#!/usr/bin/env python3

import asyncio
import json
import getpass
import sys
from matrix_aggregator.client import MatrixClient

async def get_new_token(homeserver: str, username: str, password: str):
    """Get a new access token via password login"""
    
    login_data = {
        "type": "m.login.password",
        "identifier": {
            "type": "m.id.user",
            "user": username
        },
        "password": password
    }
    
    # Create a temporary client without token for login
    import aiohttp
    async with aiohttp.ClientSession() as session:
        url = f"{homeserver}/_matrix/client/v3/login"
        headers = {'Content-Type': 'application/json'}
        
        async with session.post(url, headers=headers, json=login_data) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                error_text = await response.text()
                raise Exception(f"Login failed: HTTP {response.status} - {error_text}")

async def setup_authentication():
    """Interactive setup for Matrix authentication"""
    
    print("Matrix Authentication Setup")
    print("=" * 30)
    
    # Get current config
    try:
        with open('matrix_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}
    
    homeserver = input(f"Homeserver [{config.get('homeserver', 'https://matrix.org')}]: ").strip()
    if not homeserver:
        homeserver = config.get('homeserver', 'https://matrix.org')
    
    username = input(f"Username [{config.get('username', '')}]: ").strip()
    if not username:
        username = config.get('username', '')
    
    if not username:
        print("Username is required")
        return False
    
    # Get password
    password = getpass.getpass("Password: ")
    if not password:
        print("Password is required")
        return False
    
    try:
        print("\nAuthenticating...")
        login_result = await get_new_token(homeserver, username, password)
        
        # Update config
        config.update({
            "homeserver": homeserver,
            "username": username,
            "access_token": login_result['access_token'],
            "output_directory": config.get('output_directory', 'matrix_exports'),
            "schedule": config.get('schedule', {
                "frequency": "daily",
                "time": "02:00"
            }),
            "max_backups": config.get('max_backups', 30)
        })
        
        # Save updated config
        with open('matrix_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✓ Authentication successful!")
        print(f"✓ User ID: {login_result['user_id']}")
        print(f"✓ Device ID: {login_result['device_id']}")
        print(f"✓ Config saved to matrix_config.json")
        
        # Test the connection
        print("\nTesting connection...")
        async with MatrixClient(homeserver, login_result['access_token']) as client:
            whoami = await client.whoami()
            sync_result = await client.sync(timeout=0)
            rooms_count = len(sync_result.get('rooms', {}).get('join', {}))
            print(f"✓ Connected successfully - found {rooms_count} rooms")
        
        return True
        
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(setup_authentication())
    if success:
        print("\nYou can now run:")
        print("  python matrix_sync.py matrix_config.json")
        print("  python matrix_sync.py matrix_config.json --schedule")
    sys.exit(0 if success else 1)