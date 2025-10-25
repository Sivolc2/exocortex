import asyncio
import aiofiles
import hashlib
import logging
import mimetypes
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class MediaManager:
    def __init__(self, client, storage, media_dir: str):
        self.client = client
        self.storage = storage
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_media_filename(self, mxc_uri: str, content_type: str = None) -> str:
        """Generate a safe filename for media"""
        # Extract server and media ID from mxc://server/mediaId
        parts = mxc_uri.replace('mxc://', '').split('/', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid mxc URI: {mxc_uri}")
        
        server_name, media_id = parts
        
        # Create hash-based filename to avoid conflicts
        hash_input = f"{server_name}/{media_id}".encode()
        file_hash = hashlib.md5(hash_input).hexdigest()[:12]
        
        # Try to get file extension from content type
        extension = ''
        if content_type:
            extension = mimetypes.guess_extension(content_type) or ''
        
        return f"{file_hash}_{media_id}{extension}"
    
    async def download_and_store_media(self, mxc_uri: str, encrypted_file: Optional[Dict] = None) -> Optional[str]:
        """Download and store media, return local path"""
        # Check if already cached
        cached_path = self.storage.get_media_path(mxc_uri)
        if cached_path and Path(cached_path).exists():
            return cached_path
        
        try:
            # Parse mxc URI
            parts = mxc_uri.replace('mxc://', '').split('/', 1)
            if len(parts) != 2:
                logger.error(f"Invalid mxc URI: {mxc_uri}")
                return None
            
            server_name, media_id = parts
            
            # Download content
            if encrypted_file:
                # Handle encrypted media
                from .crypto import CryptoHandler
                crypto = CryptoHandler(self.client, self.storage)
                content = await crypto.decrypt_media(encrypted_file)
                content_type = encrypted_file.get('mimetype', 'application/octet-stream')
            else:
                # Regular media download
                content = await self.client.download_media(server_name, media_id)
                content_type = 'application/octet-stream'  # Default, could be improved with HEAD request
            
            if not content:
                logger.error(f"Failed to download {mxc_uri}")
                return None
            
            # Generate filename and save
            filename = self._get_media_filename(mxc_uri, content_type)
            local_path = self.media_dir / filename
            
            async with aiofiles.open(local_path, 'wb') as f:
                await f.write(content)
            
            # Store in cache database
            self.storage.store_media(
                mxc_uri, 
                str(local_path), 
                content_type, 
                len(content)
            )
            
            logger.info(f"Downloaded {mxc_uri} to {local_path}")
            return str(local_path)
            
        except Exception as e:
            logger.error(f"Failed to download media {mxc_uri}: {e}")
            return None
    
    async def process_message_media(self, event: Dict) -> Dict[str, str]:
        """Extract and download media from a message event"""
        media_files = {}
        content = event.get('content', {})
        
        # Handle different message types
        msgtype = content.get('msgtype')
        
        if msgtype == 'm.image':
            url = content.get('url')
            if url:
                local_path = await self.download_and_store_media(url, content.get('file'))
                if local_path:
                    media_files['image'] = local_path
        
        elif msgtype == 'm.file':
            url = content.get('url')
            if url:
                local_path = await self.download_and_store_media(url, content.get('file'))
                if local_path:
                    media_files['file'] = local_path
        
        elif msgtype == 'm.audio':
            url = content.get('url')
            if url:
                local_path = await self.download_and_store_media(url, content.get('file'))
                if local_path:
                    media_files['audio'] = local_path
        
        elif msgtype == 'm.video':
            url = content.get('url')
            if url:
                local_path = await self.download_and_store_media(url, content.get('file'))
                if local_path:
                    media_files['video'] = local_path
        
        # Handle stickers
        elif event.get('type') == 'm.sticker':
            url = content.get('url')
            if url:
                local_path = await self.download_and_store_media(url, content.get('file'))
                if local_path:
                    media_files['sticker'] = local_path
        
        return media_files