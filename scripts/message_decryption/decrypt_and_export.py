#!/usr/bin/env python3

import asyncio
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from matrix_aggregator.client import MatrixClient
from matrix_aggregator.storage import MatrixStorage
from matrix_crypto import MatrixCrypto

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatrixDecryptor:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.storage = MatrixStorage(self.config['output_directory'] + '/matrix_messages.db')
        self.session_key_cache = {}
        self.backup_key = None
        
    async def get_backup_info(self, client: MatrixClient) -> Optional[Dict]:
        """Get backup information from server"""
        try:
            backup_info = await client.get_room_keys_backup()
            if backup_info:
                logger.info(f"Found backup version: {backup_info.get('version')}")
                return backup_info
            else:
                logger.warning("No backup found on server")
                return None
        except Exception as e:
            logger.error(f"Failed to get backup info: {e}")
            return None
    
    async def initialize_crypto(self, client: MatrixClient) -> bool:
        """Initialize cryptographic components"""
        try:
            # Decode recovery key
            recovery_key = self.config.get('recovery_key')
            if not recovery_key:
                logger.error("No recovery key found in config")
                return False
                
            key_bytes = MatrixCrypto.decode_recovery_key(recovery_key)
            logger.info("Recovery key decoded successfully")
            
            # Get backup info from server
            backup_info = await self.get_backup_info(client)
            if not backup_info:
                logger.error("Cannot decrypt without backup info")
                return False
            
            # Derive backup key
            self.backup_key = MatrixCrypto.derive_backup_key(key_bytes, backup_info)
            logger.info("Backup key derived successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Crypto initialization failed: {e}")
            return False
    
    async def get_session_key(self, client: MatrixClient, room_id: str, session_id: str, backup_version: str) -> Optional[str]:
        """Get and decrypt session key for a specific session"""
        
        # Check cache first
        cache_key = f"{room_id}:{session_id}"
        if cache_key in self.session_key_cache:
            return self.session_key_cache[cache_key]
        
        try:
            # Get encrypted session from backup
            room_keys = await client.get_room_keys(room_id, backup_version)
            
            sessions = room_keys.get('sessions', {})
            if session_id not in sessions:
                logger.warning(f"Session {session_id} not found in backup")
                return None
            
            session_info = sessions[session_id]
            session_data = session_info.get('session_data', {})
            
            # Decrypt session key
            decrypted_key = MatrixCrypto.decrypt_session_data(session_data, self.backup_key)
            
            if decrypted_key:
                self.session_key_cache[cache_key] = decrypted_key
                logger.info(f"Successfully decrypted session key for {room_id}:{session_id}")
                return decrypted_key
            else:
                logger.warning(f"Failed to decrypt session key for {room_id}:{session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting session key: {e}")
            return None
    
    async def decrypt_messages(self, client: MatrixClient) -> int:
        """Decrypt all pending encrypted messages"""
        
        # Initialize crypto
        if not await self.initialize_crypto(client):
            logger.error("Failed to initialize crypto")
            return 0
        
        # Get backup version
        backup_info = await self.get_backup_info(client)
        backup_version = backup_info.get('version') if backup_info else None
        
        if not backup_version:
            logger.error("No backup version available")
            return 0
        
        # Get encrypted messages from database
        with sqlite3.connect(self.storage.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT event_id, room_id, content 
                FROM events 
                WHERE event_type = 'm.room.encrypted' 
                AND decrypted_content IS NULL
                ORDER BY origin_server_ts ASC
            """)
            encrypted_messages = cursor.fetchall()
        
        logger.info(f"Found {len(encrypted_messages)} encrypted messages to decrypt")
        
        decrypted_count = 0
        
        for msg in encrypted_messages:
            try:
                event_id = msg['event_id']
                room_id = msg['room_id']
                content = json.loads(msg['content'])
                
                # Extract encryption details
                algorithm = content.get('algorithm')
                session_id = content.get('session_id')
                ciphertext = content.get('ciphertext')
                
                if algorithm != 'm.megolm.v1.aes-sha2':
                    logger.warning(f"Unsupported algorithm: {algorithm}")
                    continue
                
                if not session_id or not ciphertext:
                    logger.warning(f"Missing session_id or ciphertext in {event_id}")
                    continue
                
                # Try to get session key
                session_key = await self.get_session_key(client, room_id, session_id, backup_version)
                
                if session_key:
                    # Decrypt message
                    decrypted_content = MatrixCrypto.decrypt_megolm_event(ciphertext, session_key)
                    
                    if decrypted_content:
                        # Update database with decrypted content
                        with sqlite3.connect(self.storage.db_path) as conn:
                            conn.execute(
                                "UPDATE events SET decrypted_content = ? WHERE event_id = ?",
                                (decrypted_content, event_id)
                            )
                            conn.commit()
                        
                        decrypted_count += 1
                        logger.info(f"Decrypted message {event_id}")
                    else:
                        logger.warning(f"Failed to decrypt message content for {event_id}")
                else:
                    # Mark as attempted but failed
                    logger.warning(f"No session key available for {event_id} (session: {session_id})")
                    # Continue processing other messages
                    
            except Exception as e:
                logger.error(f"Error processing message {msg.get('event_id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Successfully decrypted {decrypted_count} messages")
        return decrypted_count
    
    def export_messages(self, output_file: str = None) -> str:
        """Export all messages to JSONL format"""
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"matrix_export_{timestamp}.jsonl"
        
        output_path = Path(self.config['output_directory']) / output_file
        
        exported_count = 0
        
        with sqlite3.connect(self.storage.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get all messages with room information
            cursor = conn.execute("""
                SELECT 
                    e.event_id,
                    e.room_id,
                    r.name as room_name,
                    e.sender,
                    e.event_type,
                    e.content,
                    e.decrypted_content,
                    e.origin_server_ts,
                    datetime(e.origin_server_ts/1000, 'unixepoch') as timestamp
                FROM events e
                LEFT JOIN rooms r ON e.room_id = r.room_id
                WHERE e.event_type IN ('m.room.message', 'm.room.encrypted')
                ORDER BY e.origin_server_ts ASC
            """)
            
            with open(output_path, 'w') as f:
                for row in cursor:
                    # Determine message content
                    if row['decrypted_content']:
                        # Use decrypted content for encrypted messages
                        try:
                            message_content = json.loads(row['decrypted_content'])
                        except:
                            message_content = row['decrypted_content']
                    else:
                        # Use regular content for unencrypted messages
                        try:
                            message_content = json.loads(row['content'])
                        except:
                            message_content = row['content']
                    
                    # Create export record
                    export_record = {
                        'event_id': row['event_id'],
                        'room_id': row['room_id'],
                        'room_name': row['room_name'],
                        'sender': row['sender'],
                        'event_type': row['event_type'],
                        'content': message_content,
                        'timestamp': row['timestamp'],
                        'origin_server_ts': row['origin_server_ts'],
                        'was_encrypted': row['event_type'] == 'm.room.encrypted'
                    }
                    
                    f.write(json.dumps(export_record) + '\n')
                    exported_count += 1
        
        logger.info(f"Exported {exported_count} messages to {output_path}")
        return str(output_path)

async def main():
    """Main function to decrypt and export Matrix messages"""
    
    config_file = "matrix_config.json"
    
    try:
        decryptor = MatrixDecryptor(config_file)
        
        # Connect to Matrix server
        async with MatrixClient(
            decryptor.config['homeserver'],
            decryptor.config['access_token']
        ) as client:
            
            # Verify authentication
            whoami = await client.whoami()
            logger.info(f"Connected as {whoami.get('user_id')}")
            
            # Decrypt messages
            decrypted_count = await decryptor.decrypt_messages(client)
            
            # Export all messages
            export_path = decryptor.export_messages()
            
            print(f"\nDecryption and export complete:")
            print(f"- Decrypted: {decrypted_count} messages")
            print(f"- Exported to: {export_path}")
            
    except Exception as e:
        logger.error(f"Main process failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())