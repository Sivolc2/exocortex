#!/usr/bin/env python3

import asyncio
import json
import logging
from matrix_aggregator.client import MatrixClient
from matrix_aggregator.storage import MatrixStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def populate_database(config_path: str):
    """Populate database with messages from recent sync"""
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    storage = MatrixStorage(config['output_directory'] + '/matrix_messages.db')
    
    async with MatrixClient(config['homeserver'], config['access_token']) as client:
        # Verify connection
        whoami = await client.whoami()
        logger.info(f"Connected as {whoami.get('user_id')}")
        
        # Create filter and sync
        await client.create_filter()
        sync_result = await client.sync(timeout=30000)
        
        # Process joined rooms
        rooms = sync_result.get('rooms', {}).get('join', {})
        logger.info(f"Processing {len(rooms)} rooms")
        
        total_events = 0
        encrypted_events = 0
        
        for room_id, room_data in rooms.items():
            # Store room info
            state_events = room_data.get('state', {}).get('events', [])
            room_info = {}
            
            for event in state_events:
                if event.get('type') == 'm.room.name':
                    room_info['name'] = event.get('content', {}).get('name')
                elif event.get('type') == 'm.room.topic':
                    room_info['topic'] = event.get('content', {}).get('topic')
                elif event.get('type') == 'm.room.avatar':
                    room_info['avatar_url'] = event.get('content', {}).get('url')
                elif event.get('type') == 'm.room.canonical_alias':
                    room_info['canonical_alias'] = event.get('content', {}).get('alias')
            
            storage.store_room(room_id, room_info)
            
            # Store timeline events
            timeline_events = room_data.get('timeline', {}).get('events', [])
            
            for event in timeline_events:
                storage.store_event(event)
                total_events += 1
                
                if event.get('type') == 'm.room.encrypted':
                    encrypted_events += 1
            
            # Also get some historical messages for this room
            try:
                history = await client.get_room_messages(room_id, limit=50)
                historical_events = history.get('chunk', [])
                
                for event in historical_events:
                    storage.store_event(event)
                    total_events += 1
                    
                    if event.get('type') == 'm.room.encrypted':
                        encrypted_events += 1
                        
                logger.info(f"Processed room {room_id}: {len(timeline_events)} recent + {len(historical_events)} historical events")
                
            except Exception as e:
                logger.warning(f"Failed to get history for {room_id}: {e}")
        
        logger.info(f"Database populated with {total_events} total events ({encrypted_events} encrypted)")

if __name__ == "__main__":
    asyncio.run(populate_database("matrix_config.json"))