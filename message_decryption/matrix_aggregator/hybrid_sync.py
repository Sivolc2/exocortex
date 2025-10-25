import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from nio import AsyncClient, SyncResponse, LoginResponse
from nio.events import MegolmEvent, RoomMessageText, RoomMessageMedia, Event

logger = logging.getLogger(__name__)

class HybridMatrixClient:
    def __init__(self, homeserver: str, username: str, access_token: str, store_path: str):
        self.homeserver = homeserver
        self.username = username
        self.access_token = access_token
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        # Create nio client for E2EE
        self.nio_client = AsyncClient(
            homeserver,
            f"@{username}:beeper.com",
            device_id="BEEPER_AGGREGATOR",
            store_path=str(self.store_path)
        )
        
        # Set access token
        self.nio_client.access_token = access_token
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.nio_client.load_store()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.nio_client.close()
    
    async def sync_with_decryption(self, since: Optional[str] = None) -> Dict[str, Any]:
        """Perform sync and return decrypted messages"""
        try:
            # Use nio's sync which handles E2EE automatically
            response = await self.nio_client.sync(
                timeout=30000,
                since=since,
                full_state=False
            )
            
            if not isinstance(response, SyncResponse):
                logger.error(f"Sync failed: {response}")
                return {'next_batch': since, 'rooms': {}}
            
            logger.info(f"Sync successful, processing {len(response.rooms.join)} rooms")
            
            # Extract decrypted messages
            rooms_data = {}
            
            for room_id, room_info in response.rooms.join.items():
                room_data = {
                    'messages': [],
                    'state': {},
                    'name': None
                }
                
                # Extract room name from state
                for event in room_info.state:
                    if event.type == 'm.room.name':
                        room_data['name'] = event.content.get('name')
                    elif event.type == 'm.room.canonical_alias':
                        if not room_data['name']:
                            room_data['name'] = event.content.get('alias')
                
                # Process timeline events
                for event in room_info.timeline.events:
                    message_data = None
                    
                    if isinstance(event, MegolmEvent):
                        # Encrypted event that nio has decrypted
                        decrypted = event.decrypted_event
                        
                        if isinstance(decrypted, RoomMessageText):
                            message_data = {
                                'event_id': event.event_id,
                                'sender': event.sender,
                                'timestamp': event.server_timestamp,
                                'type': 'm.room.message',
                                'was_encrypted': True,
                                'content': {
                                    'msgtype': 'm.text',
                                    'body': decrypted.body,
                                    'formatted_body': getattr(decrypted, 'formatted_body', None)
                                }
                            }
                        elif isinstance(decrypted, RoomMessageMedia):
                            message_data = {
                                'event_id': event.event_id,
                                'sender': event.sender,
                                'timestamp': event.server_timestamp,
                                'type': 'm.room.message',
                                'was_encrypted': True,
                                'content': {
                                    'msgtype': getattr(decrypted, 'msgtype', 'm.file'),
                                    'body': decrypted.body,
                                    'url': getattr(decrypted, 'url', None),
                                    'info': getattr(decrypted, 'info', {})
                                }
                            }
                        elif hasattr(decrypted, 'body'):
                            # Other decrypted message types
                            message_data = {
                                'event_id': event.event_id,
                                'sender': event.sender,
                                'timestamp': event.server_timestamp,
                                'type': 'm.room.message',
                                'was_encrypted': True,
                                'content': {
                                    'msgtype': getattr(decrypted, 'msgtype', 'm.text'),
                                    'body': decrypted.body
                                }
                            }
                    
                    elif isinstance(event, (RoomMessageText, RoomMessageMedia)):
                        # Unencrypted message
                        message_data = {
                            'event_id': event.event_id,
                            'sender': event.sender,
                            'timestamp': event.server_timestamp,
                            'type': 'm.room.message',
                            'was_encrypted': False,
                            'content': {
                                'msgtype': getattr(event, 'msgtype', 'm.text'),
                                'body': event.body,
                                'url': getattr(event, 'url', None)
                            }
                        }
                    
                    if message_data:
                        room_data['messages'].append(message_data)
                
                if room_data['messages'] or room_data['name']:
                    rooms_data[room_id] = room_data
            
            return {
                'next_batch': response.next_batch,
                'rooms': rooms_data
            }
            
        except Exception as e:
            logger.error(f"Sync with decryption failed: {e}")
            return {'next_batch': since, 'rooms': {}}
    
    async def backfill_room_messages(self, room_id: str, limit: int = 100) -> List[Dict]:
        """Backfill room messages with decryption"""
        if not self.nio_client:
            return []
        
        try:
            response = await self.nio_client.room_messages(
                room_id=room_id,
                start="",  # Start from most recent
                limit=limit
            )
            
            decrypted_messages = []
            
            if hasattr(response, 'chunk'):
                for event in response.chunk:
                    message_data = None
                    
                    if isinstance(event, MegolmEvent) and event.decrypted_event:
                        decrypted = event.decrypted_event
                        if hasattr(decrypted, 'body'):
                            message_data = {
                                'event_id': event.event_id,
                                'sender': event.sender,
                                'timestamp': event.server_timestamp,
                                'was_encrypted': True,
                                'content': {
                                    'msgtype': getattr(decrypted, 'msgtype', 'm.text'),
                                    'body': decrypted.body
                                }
                            }
                    elif hasattr(event, 'body'):
                        message_data = {
                            'event_id': event.event_id,
                            'sender': event.sender,
                            'timestamp': event.server_timestamp,
                            'was_encrypted': False,
                            'content': {
                                'msgtype': getattr(event, 'msgtype', 'm.text'),
                                'body': event.body
                            }
                        }
                    
                    if message_data:
                        decrypted_messages.append(message_data)
            
            logger.info(f"Backfilled {len(decrypted_messages)} messages from {room_id}")
            return decrypted_messages
            
        except Exception as e:
            logger.error(f"Backfill failed for {room_id}: {e}")
            return []