import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from nio import AsyncClient, LoginResponse, SyncResponse
from nio.events import Event, MegolmEvent, RoomMessageText, RoomEncryptedMedia

logger = logging.getLogger(__name__)

class NioCryptoHandler:
    def __init__(self, homeserver: str, user_id: str, device_id: str, access_token: str, store_path: str):
        self.homeserver = homeserver
        self.user_id = user_id 
        self.device_id = device_id
        self.access_token = access_token
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.client: Optional[AsyncClient] = None
        
    async def initialize(self):
        """Initialize the nio client with crypto store"""
        try:
            self.client = AsyncClient(
                self.homeserver,
                self.user_id,
                device_id=self.device_id,
                store_path=str(self.store_path),
                config=None  # Use default config
            )
            
            # Set the access token
            self.client.access_token = self.access_token
            
            # Load existing store
            self.client.load_store()
            
            logger.info(f"Initialized nio crypto client for {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize nio crypto: {e}")
            return False
    
    async def sync_and_decrypt(self) -> Dict[str, Any]:
        """Perform sync and handle decryption"""
        if not self.client:
            return {}
        
        try:
            # Sync with nio client to get encrypted events
            response = await self.client.sync(timeout=30000, full_state=False)
            
            if isinstance(response, SyncResponse):
                logger.info(f"Nio sync successful, next_batch: {response.next_batch}")
                
                # Process rooms and decrypt messages
                decrypted_messages = {}
                
                for room_id, room_info in response.rooms.join.items():
                    room_messages = []
                    
                    for event in room_info.timeline.events:
                        if isinstance(event, MegolmEvent):
                            # This is an encrypted event that nio has decrypted
                            decrypted_event = event.decrypted_event
                            if isinstance(decrypted_event, RoomMessageText):
                                room_messages.append({
                                    'event_id': event.event_id,
                                    'sender': event.sender,
                                    'timestamp': event.server_timestamp,
                                    'decrypted_content': {
                                        'msgtype': 'm.text',
                                        'body': decrypted_event.body,
                                        'formatted_body': getattr(decrypted_event, 'formatted_body', None)
                                    }
                                })
                        elif hasattr(event, 'body'):  # Regular unencrypted message
                            room_messages.append({
                                'event_id': event.event_id,
                                'sender': event.sender,
                                'timestamp': event.server_timestamp,
                                'content': {
                                    'msgtype': getattr(event, 'msgtype', 'm.text'),
                                    'body': event.body
                                }
                            })
                    
                    if room_messages:
                        decrypted_messages[room_id] = room_messages
                
                return {
                    'next_batch': response.next_batch,
                    'decrypted_messages': decrypted_messages
                }
            else:
                logger.error(f"Sync failed: {response}")
                return {}
                
        except Exception as e:
            logger.error(f"Sync and decrypt failed: {e}")
            return {}
    
    async def decrypt_single_event(self, room_id: str, event_data: Dict) -> Optional[Dict]:
        """Decrypt a single encrypted event"""
        if not self.client:
            return None
        
        try:
            # Create event from raw data
            event = Event.parse_event(event_data)
            
            if isinstance(event, MegolmEvent) and event.decrypted_event:
                decrypted = event.decrypted_event
                
                if isinstance(decrypted, RoomMessageText):
                    return {
                        'msgtype': 'm.text',
                        'body': decrypted.body,
                        'formatted_body': getattr(decrypted, 'formatted_body', None)
                    }
                elif hasattr(decrypted, 'body'):
                    return {
                        'msgtype': getattr(decrypted, 'msgtype', 'm.text'),
                        'body': decrypted.body
                    }
            
        except Exception as e:
            logger.debug(f"Could not decrypt event {event_data.get('event_id')}: {e}")
        
        return None
    
    async def close(self):
        """Close the nio client"""
        if self.client:
            await self.client.close()