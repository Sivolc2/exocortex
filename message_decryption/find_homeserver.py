#!/usr/bin/env python3

import asyncio
import aiohttp
import json

async def discover_homeserver(domain: str):
    """Try to discover the actual Matrix homeserver for a domain"""
    
    print(f"Discovering homeserver for {domain}...")
    
    # Try .well-known discovery
    well_known_urls = [
        f"https://{domain}/.well-known/matrix/client",
        f"https://www.{domain}/.well-known/matrix/client"
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in well_known_urls:
            try:
                print(f"Trying {url}")
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        homeserver_url = data.get('m.homeserver', {}).get('base_url')
                        if homeserver_url:
                            print(f"✓ Found homeserver: {homeserver_url}")
                            
                            # Verify it's a real Matrix homeserver
                            versions_url = f"{homeserver_url.rstrip('/')}/_matrix/client/versions"
                            try:
                                async with session.get(versions_url, timeout=10) as ver_response:
                                    if ver_response.status == 200:
                                        versions = await ver_response.json()
                                        print(f"✓ Verified Matrix server: {versions.get('versions', [])}")
                                        return homeserver_url
                                    else:
                                        print(f"✗ Not a valid Matrix server (HTTP {ver_response.status})")
                            except Exception as e:
                                print(f"✗ Could not verify Matrix server: {e}")
                        else:
                            print("✗ No homeserver URL in well-known response")
                    else:
                        print(f"✗ HTTP {response.status}")
            except Exception as e:
                print(f"✗ Failed: {e}")
        
        # Try common Matrix homeserver URLs for the domain
        candidate_urls = [
            f"https://matrix.{domain}",
            f"https://{domain}:8448",
            f"https://{domain}",
        ]
        
        print("\nTrying common Matrix homeserver patterns...")
        for url in candidate_urls:
            try:
                print(f"Trying {url}")
                versions_url = f"{url}/_matrix/client/versions"
                async with session.get(versions_url, timeout=10) as response:
                    if response.status == 200:
                        versions = await response.json()
                        print(f"✓ Found Matrix server: {versions.get('versions', [])}")
                        return url
                    else:
                        print(f"✗ HTTP {response.status}")
            except Exception as e:
                print(f"✗ Failed: {e}")
    
    return None

async def main():
    print("Beeper Homeserver Discovery")
    print("=" * 30)
    
    # Try common domains
    domains = ["beeper.com", "matrix.beeper.com"]
    
    for domain in domains:
        homeserver = await discover_homeserver(domain)
        if homeserver:
            print(f"\n🎉 Success! Use this homeserver URL: {homeserver}")
            
            # Update the config
            try:
                with open('matrix_config.json', 'r') as f:
                    config = json.load(f)
                
                config['homeserver'] = homeserver
                
                with open('matrix_config.json', 'w') as f:
                    json.dump(config, f, indent=2)
                
                print("✓ Updated matrix_config.json with correct homeserver URL")
                print("\nNow try: python get_token.py")
                
            except Exception as e:
                print(f"Could not update config: {e}")
            
            return True
        
        print(f"\nNo Matrix homeserver found for {domain}")
    
    print("\n❌ Could not find Beeper's Matrix homeserver")
    print("You may need to:")
    print("1. Check Beeper's current documentation")
    print("2. Contact Beeper support for the correct homeserver URL")
    print("3. Use a different Matrix account (like matrix.org)")
    
    return False

if __name__ == "__main__":
    asyncio.run(main())