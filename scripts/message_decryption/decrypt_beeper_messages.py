#!/usr/bin/env python3

import asyncio
import json
import getpass
import sqlite3
import base64
import hashlib
import hmac
import logging
import sys
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidSignature
from matrix_aggregator.client import MatrixClient
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupDecryptor:
    def __init__(self, recovery_key: str):
        self.recovery_key = recovery_key
        self.backup_key = None
    
    def _derive_backup_key(self, recovery_key: str) -> bytes:
        """Derive backup decryption key from recovery key"""
        # Matrix recovery keys are base58-encoded
        # Remove the 'E' prefix and checksum, then decode
        if not recovery_key.startswith('E'):
            raise ValueError("Recovery key must start with 'E'")
        
        # For simplicity, we'll use the recovery key directly as seed
        # Real implementation would need proper base58 decoding + checksum validation
        key_material = recovery_key[1:].encode('utf-8')
        
        # Use PBKDF2 to derive 32-byte key (this is simplified)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'matrix_backup_key',  # Real salt would come from backup
            iterations=500000,
        )
        return kdf.derive(key_material)
    
    def decrypt_session_key(self, encrypted_session: Dict) -> Optional[Dict]:
        """Decrypt a single session key from backup"""
        try:
            if not self.backup_key:
                self.backup_key = self._derive_backup_key(self.recovery_key)
            
            # This is a simplified version - real implementation needs:
            # 1. Proper curve25519 key derivation
            # 2. AES-256-GCM decryption with proper IV/tag handling
            # 3. JSON parsing of decrypted session
            
            logger.warning("Session key decryption not fully implemented")
            return None
            
        except Exception as e:
            logger.error(f"Failed to decrypt session key: {e}")
            return None

async def decrypt_with_recovery_key(config_path: str, recovery_key: str = None):
    """Decrypt messages using Matrix recovery key"""
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Use recovery key from config if not provided
    if not recovery_key:
        recovery_key = config.get('recovery_key', '').strip()
        if not recovery_key:
            print("No recovery key found in config or provided as argument")
            return False
    
    output_dir = Path(config['output_directory'])
    db_path = output_dir / 'matrix_messages.db'
    
    print("Decrypting Beeper Messages")
    print("=" * 30)
    print(f"Recovery key: {recovery_key[:15]}...{recovery_key[-10:]}")
    
    decryptor = BackupDecryptor(recovery_key)
    
    async with MatrixClient(config['homeserver'], config['access_token']) as client:
        # Get backup info
        backup_info = await client.get_room_keys_backup()
        version = backup_info['version']
        
        print(f"✓ Using backup version {version} with {backup_info['count']} keys")
        
        # For now, show what we have in the database
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get sample messages to show decryption attempts
            cursor = conn.execute('''
                SELECT room_id, event_id, sender, content, origin_server_ts
                FROM events 
                WHERE event_type = 'm.room.encrypted'
                ORDER BY origin_server_ts DESC
                LIMIT 5
            ''')
            
            messages = [dict(row) for row in cursor.fetchall()]
            
            print(f"\nAttempting to decrypt {len(messages)} sample messages...")
            
            for msg in messages:
                try:
                    content = json.loads(msg['content'])
                    session_id = content.get('session_id')
                    
                    print(f"\nMessage from {msg['sender']}:")
                    print(f"  Session ID: {session_id}")
                    print(f"  Algorithm: {content.get('algorithm')}")
                    
                    # Here we would:
                    # 1. Get the session key from backup for this session_id
                    # 2. Decrypt the session key using recovery key
                    # 3. Use the session key to decrypt the ciphertext
                    
                    print(f"  Status: Session key decryption not yet implemented")
                    
                except Exception as e:
                    print(f"  Error: {e}")
        
        print(f"\n⚠️  To complete decryption implementation, we need:")
        print(f"1. Proper base58 decoding of recovery key")
        print(f"2. Curve25519 key derivation")
        print(f"3. AES-256-GCM session key decryption")
        print(f"4. Megolm message decryption")
        print(f"\nConsider using Element desktop's export feature for now.")

async def simple_decrypt_attempt(config_path: str, recovery_key: str):
    """Simplified decryption attempt - shows process without full crypto"""
    
    # Add recovery key to config for future use
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    config['recovery_key'] = recovery_key
    
    # Save config with recovery key (for future implementations)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✓ Recovery key saved to config")
    print("✓ System ready for full E2EE implementation")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python decrypt_beeper_messages.py <config_path>")
        print("  python decrypt_beeper_messages.py <config_path> <recovery_key>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    recovery_key = None
    if len(sys.argv) > 2:
        recovery_key = sys.argv[2]
    
    success = asyncio.run(decrypt_with_recovery_key(config_path, recovery_key))
    sys.exit(0 if success else 1)