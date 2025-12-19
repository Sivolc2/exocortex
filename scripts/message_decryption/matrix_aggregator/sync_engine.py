import asyncio
import logging
from typing import Dict, List, Optional
from .client import MatrixClient
from .storage import MatrixStorage

logger = logging.getLogger(__name__)

class SyncEngine:
    def __init__(self, client: MatrixClient, storage: MatrixStorage):
        self.client = client
        self.storage = storage
        self.running = False
    
    async def initialize(self):
        """Initialize the sync engine"""
        await self.client.whoami()
        logger.info(f"Authenticated as {self.client.user_id}")
        
        versions = await self.client.get_versions()
        logger.info(f"Server versions: {versions.get('versions', [])}")
        
        try:
            capabilities = await self.client.get_capabilities()
            logger.info(f"Server capabilities: {list(capabilities.get('capabilities', {}).keys())}")
        except Exception as e:
            logger.warning(f"Could not fetch capabilities: {e}")
        
        if not self.client.filter_id:
            filter_id = await self.client.create_filter()
            logger.info(f"Created sync filter: {filter_id}")
    
    async def initial_sync(self):
        """Perform initial sync to get current state"""
        logger.info("Performing initial sync...")
        
        since = self.storage.get_sync_token()
        sync_response = await self.client.sync(since=since, timeout=0)
        
        await self.process_sync_response(sync_response)
        return sync_response
    
    async def start_sync_loop(self, stop_after_initial: bool = False):
        """Start the continuous sync loop"""
        self.running = True
        
        try:
            await self.initial_sync()
            
            if stop_after_initial:
                return
            
            logger.info("Starting continuous sync...")
            while self.running:
                try:
                    sync_response = await self.client.sync(
                        since=self.client.next_batch,
                        timeout=30000
                    )
                    await self.process_sync_response(sync_response)
                    
                except Exception as e:
                    logger.error(f"Sync error: {e}")
                    await asyncio.sleep(5)
                    
        except KeyboardInterrupt:
            logger.info("Sync interrupted by user")
        finally:
            self.running = False
    
    def stop(self):
        """Stop the sync loop"""
        self.running = False
    
    async def process_sync_response(self, sync_response: Dict):
        """Process a sync response and store relevant data"""
        if 'next_batch' in sync_response:
            self.storage.store_sync_token(sync_response['next_batch'])
        
        rooms = sync_response.get('rooms', {})
        
        # Process joined rooms
        for room_id, room_data in rooms.get('join', {}).items():
            await self.process_room_data(room_id, room_data)
        
        # Process invited rooms
        for room_id, room_data in rooms.get('invite', {}).items():
            await self.process_room_data(room_id, room_data, is_invite=True)
    
    async def process_room_data(self, room_id: str, room_data: Dict, is_invite: bool = False):
        """Process room data from sync"""
        # Extract room metadata from state events
        state_events = room_data.get('state', {}).get('events', [])
        room_metadata = {}
        
        for event in state_events:
            if event['type'] == 'm.room.name':
                room_metadata['name'] = event.get('content', {}).get('name')
            elif event['type'] == 'm.room.topic':
                room_metadata['topic'] = event.get('content', {}).get('topic')
            elif event['type'] == 'm.room.avatar':
                room_metadata['avatar_url'] = event.get('content', {}).get('url')
            elif event['type'] == 'm.room.canonical_alias':
                room_metadata['canonical_alias'] = event.get('content', {}).get('alias')
        
        self.storage.store_room(room_id, room_metadata)
        
        # Process timeline events (messages)
        if not is_invite:
            timeline_events = room_data.get('timeline', {}).get('events', [])
            for event in timeline_events:
                if event['type'] in ['m.room.message', 'm.sticker', 'm.room.encrypted']:
                    # Ensure room_id is set on the event
                    if 'room_id' not in event:
                        event['room_id'] = room_id
                    self.storage.store_event(event)
                    logger.debug(f"Stored event {event['event_id']} in {room_id}")
    
    async def backfill_room_history(self, room_id: str, limit: int = 1000):
        """Backfill historical messages for a room"""
        logger.info(f"Backfilling history for room {room_id}")
        
        total_fetched = 0
        from_token = None
        
        while total_fetched < limit:
            try:
                batch_limit = min(200, limit - total_fetched)
                response = await self.client.get_room_messages(
                    room_id, from_token=from_token, limit=batch_limit
                )
                
                events = response.get('chunk', [])
                if not events:
                    break
                
                for event in events:
                    if event['type'] in ['m.room.message', 'm.sticker', 'm.room.encrypted']:
                        self.storage.store_event(event)
                
                total_fetched += len(events)
                from_token = response.get('end')
                
                if not from_token:
                    break
                    
                logger.info(f"Fetched {total_fetched}/{limit} events for {room_id}")
                
            except Exception as e:
                logger.error(f"Error backfilling {room_id}: {e}")
                break
        
        logger.info(f"Completed backfill for {room_id}: {total_fetched} events")