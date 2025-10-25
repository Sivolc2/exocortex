import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict

from .client import MatrixClient
from .storage import MatrixStorage
from .sync_engine import SyncEngine
from .media_manager import MediaManager
from .exporter import ObsidianExporter
from .scheduler import MessageScheduler
from .crypto import CryptoHandler
from .nio_crypto import NioCryptoHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MatrixAggregator:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.storage = MatrixStorage(self._get_db_path())
        self.media_manager = None
        self.exporter = None
        self.sync_engine = None
        self.crypto_handler = None
        self.nio_crypto = None
        self.client = None
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _get_db_path(self) -> str:
        """Get database path"""
        output_dir = Path(self.config['output_directory'])
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir / 'matrix_messages.db')
    
    def _get_media_dir(self) -> str:
        """Get media directory path"""
        output_dir = Path(self.config['output_directory'])
        media_dir = output_dir / 'media'
        media_dir.mkdir(parents=True, exist_ok=True)
        return str(media_dir)
    
    async def initialize(self):
        """Initialize all components"""
        self.client = MatrixClient(
            self.config['homeserver'],
            self.config['access_token']
        )
        
        self.media_manager = MediaManager(
            self.client,
            self.storage,
            self._get_media_dir()
        )
        
        self.exporter = ObsidianExporter(
            self.storage,
            self.media_manager,
            self.config['output_directory']
        )
        
        self.sync_engine = SyncEngine(self.client, self.storage)
        
        self.crypto_handler = CryptoHandler(self.client, self.storage)
        
        # Initialize nio crypto handler
        self.nio_crypto = NioCryptoHandler(
            self.config['homeserver'],
            '@' + self.config['username'] + ':beeper.com',  # Full Matrix ID
            None,  # Will be set after client initialization
            self.config['access_token'],
            str(Path(self.config['output_directory']) / 'nio_store')
        )
    
    async def sync_messages(self):
        """Perform a full sync and export"""
        async with self.client:
            await self.sync_engine.initialize()
            
            # Initialize crypto if possible
            store_path = Path(self.config['output_directory']) / 'crypto_store'
            store_path.mkdir(exist_ok=True)
            
            if await self.crypto_handler.initialize_nio_client(
                self.client.user_id, 
                self.client.device_id, 
                str(store_path)
            ):
                await self.crypto_handler.load_room_keys_from_backup()
            
            # Perform sync
            await self.sync_engine.start_sync_loop(stop_after_initial=True)
            
            # Backfill history for active rooms
            rooms = self.storage.get_all_rooms()
            for room in rooms[:10]:  # Limit to first 10 rooms for initial run
                await self.sync_engine.backfill_room_history(room['room_id'], limit=500)
            
            # Export to Markdown
            exported_files = await self.exporter.export_all_rooms()
            logger.info(f"Exported {len(exported_files)} rooms to Markdown")
            
            return exported_files
    
    def start_scheduler(self):
        """Start the scheduled sync process"""
        scheduler = MessageScheduler(
            self.sync_messages,
            self.config.get('schedule', {}).get('frequency', 'daily'),
            self.config.get('schedule', {}).get('time', '02:00')
        )
        
        try:
            scheduler.run_scheduler()
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            scheduler.stop()

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m matrix_aggregator.main <config_path> [--schedule]")
        sys.exit(1)
    
    config_path = sys.argv[1]
    run_scheduler = '--schedule' in sys.argv
    
    aggregator = MatrixAggregator(config_path)
    await aggregator.initialize()
    
    if run_scheduler:
        aggregator.start_scheduler()
    else:
        exported_files = await aggregator.sync_messages()
        print(f"Sync complete. Exported {len(exported_files)} rooms.")

if __name__ == "__main__":
    asyncio.run(main())