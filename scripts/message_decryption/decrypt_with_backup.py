#!/usr/bin/env python3

import asyncio
import json
import getpass
import sqlite3
import logging
import sys
from pathlib import Path
from datetime import datetime
from matrix_aggregator.client import MatrixClient
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def decrypt_messages_with_backup(config_path: str):
    """Attempt to decrypt messages using key backup"""
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("Matrix Message Decryption with Key Backup")
    print("=" * 45)
    
    async with MatrixClient(config['homeserver'], config['access_token']) as client:
        # Check backup availability
        try:
            backup_info = await client.get_room_keys_backup()
            print(f"✓ Key backup found: {backup_info['count']} keys available")
            print(f"  Algorithm: {backup_info['algorithm']}")
            print(f"  Version: {backup_info['version']}")
        except Exception as e:
            print(f"✗ No key backup available: {e}")
            return
        
        print("\nTo decrypt messages, you need:")
        print("1. Your Matrix recovery key (58-character key starting with E...)")
        print("2. OR your backup passphrase")
        print("\nThese are usually saved when you first set up encryption.")
        print("In Beeper/Element, check: Settings > Security > Cryptography > Key Backup")
        
        recovery_input = input("\nEnter recovery key or passphrase (or 'skip' to see structure only): ").strip()
        
        if recovery_input.lower() == 'skip':
            await show_backup_structure(client, backup_info)
            return
        
        # For now, show what we'd need to implement full decryption
        print("\n⚠️  Full backup key decryption requires:")
        print("1. PBKDF2 key derivation from passphrase/recovery key")
        print("2. AES-256-GCM decryption of backup keys")
        print("3. Megolm session import and message decryption")
        print("\nThis is a complex cryptographic process that requires careful implementation.")
        print("Consider using Element/Beeper desktop app to export decrypted messages directly.")

async def show_backup_structure(client: MatrixClient, backup_info: Dict):
    """Show the structure of what's in the backup"""
    
    print("\nKey Backup Structure Analysis:")
    print("-" * 30)
    
    try:
        # Get a sample of room keys to show structure
        version = backup_info['version']
        
        # We can't actually decrypt without the recovery key,
        # but we can show what rooms have keys available
        print(f"Backup contains {backup_info['count']} session keys")
        print("To see which rooms have keys, we'd need to implement:")
        print("  GET /_matrix/client/v3/room_keys/keys?version={version}")
        print("\nEach room would show:")
        print("  - session_id: Megolm session identifier")
        print("  - first_message_index: Starting point for decryption")
        print("  - forwarded_count: How many times key was forwarded")
        print("  - is_verified: Whether the session is verified")
        
    except Exception as e:
        logger.error(f"Could not analyze backup structure: {e}")

async def show_sample_decryption_process():
    """Show what the decryption process would look like"""
    
    print("\nDecryption Process Overview:")
    print("=" * 30)
    print("1. Derive backup key from recovery passphrase:")
    print("   - Use PBKDF2 with Matrix-specific parameters")
    print("   - Salt and iterations from backup auth_data")
    print()
    print("2. Decrypt room session keys:")
    print("   - Download encrypted sessions from backup")
    print("   - Decrypt using derived key + AES-256-GCM")
    print()
    print("3. Import megolm sessions:")
    print("   - Parse each session key")
    print("   - Store in local crypto database")
    print()
    print("4. Decrypt individual messages:")
    print("   - Match message session_id to imported session")
    print("   - Decrypt ciphertext using megolm")
    print("   - Parse decrypted JSON content")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python decrypt_with_backup.py <config_path>")
        sys.exit(1)
    
    asyncio.run(decrypt_messages_with_backup(sys.argv[1]))