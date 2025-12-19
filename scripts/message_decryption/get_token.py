#!/usr/bin/env python3

import asyncio
import json
import aiohttp
import getpass

async def get_login_flows(homeserver: str):
    """Check what login flows are available"""
    async with aiohttp.ClientSession() as session:
        url = f"{homeserver}/_matrix/client/v3/login"
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to get login flows: {response.status}")

async def login_with_password(homeserver: str, username: str, password: str):
    """Login with username/password"""
    login_data = {
        "type": "m.login.password",
        "identifier": {
            "type": "m.id.user", 
            "user": username
        },
        "password": password
    }
    
    async with aiohttp.ClientSession() as session:
        url = f"{homeserver}/_matrix/client/v3/login"
        headers = {'Content-Type': 'application/json'}
        
        async with session.post(url, headers=headers, json=login_data) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Login failed: {error_text}")

async def main():
    # Load existing config
    with open('matrix_config.json', 'r') as f:
        config = json.load(f)
    
    homeserver = config['homeserver']
    username = config['username']
    
    print(f"Getting new token for {username} on {homeserver}")
    
    # Check available login flows
    try:
        flows = await get_login_flows(homeserver)
        print("Available login flows:")
        for flow in flows.get('flows', []):
            print(f"  - {flow['type']}")
    except Exception as e:
        print(f"Could not check login flows: {e}")
    
    # Get password and login
    password = getpass.getpass(f"Password for {username}: ")
    
    try:
        result = await login_with_password(homeserver, username, password)
        
        # Update config with new token
        config['access_token'] = result['access_token']
        
        # Save updated config
        with open('matrix_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✓ New token saved to matrix_config.json")
        print(f"✓ Logged in as: {result['user_id']}")
        
    except Exception as e:
        print(f"✗ Login failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(main())