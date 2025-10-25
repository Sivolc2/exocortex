import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from pathlib import Path

logger = logging.getLogger(__name__)

class MatrixClient:
    def __init__(self, homeserver: str, access_token: str):
        self.homeserver = homeserver.rstrip('/')
        self.access_token = access_token
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_id: Optional[str] = None
        self.device_id: Optional[str] = None
        self.filter_id: Optional[str] = None
        self.next_batch: Optional[str] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        url = urljoin(self.homeserver, endpoint)
        headers = self._get_headers()
        
        async with self.session.request(method, url, headers=headers, json=data) as response:
            if response.status == 401:
                error_detail = await response.text()
                raise Exception(f"Authentication failed - invalid or expired token. Server response: {error_detail}")
            elif response.status == 429:
                retry_after = int(response.headers.get('Retry-After', 30))
                logger.warning(f"Rate limited, waiting {retry_after} seconds")
                await asyncio.sleep(retry_after)
                return await self._make_request(method, endpoint, data)
            elif response.status >= 400:
                error_text = await response.text()
                raise Exception(f"HTTP {response.status}: {error_text}")
            
            return await response.json()
    
    async def discover_homeserver(self, domain: str) -> str:
        """Discover homeserver via .well-known"""
        well_known_url = f"https://{domain}/.well-known/matrix/client"
        try:
            async with self.session.get(well_known_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('m.homeserver', {}).get('base_url', f"https://{domain}")
        except:
            pass
        return f"https://{domain}"
    
    async def get_versions(self) -> Dict:
        """Get supported API versions and features"""
        return await self._make_request('GET', '/_matrix/client/versions')
    
    async def get_capabilities(self) -> Dict:
        """Get server capabilities"""
        return await self._make_request('GET', '/_matrix/client/v3/capabilities')
    
    async def whoami(self) -> Dict:
        """Get current user info"""
        result = await self._make_request('GET', '/_matrix/client/v3/account/whoami')
        self.user_id = result.get('user_id')
        self.device_id = result.get('device_id')
        return result
    
    async def create_filter(self) -> str:
        """Create a sync filter for efficient message fetching"""
        filter_data = {
            "room": {
                "timeline": {
                    "types": ["m.room.message", "m.sticker", "m.room.encrypted"],
                    "limit": 200
                },
                "state": {
                    "lazy_load_members": True
                },
                "ephemeral": {"types": []},
                "account_data": {"types": []}
            },
            "presence": {"types": []}
        }
        
        result = await self._make_request(
            'POST', 
            f'/_matrix/client/v3/user/{self.user_id}/filter',
            filter_data
        )
        self.filter_id = result['filter_id']
        return self.filter_id
    
    async def sync(self, since: Optional[str] = None, timeout: int = 30000) -> Dict:
        """Perform sync to get latest events"""
        params = {
            'timeout': timeout
        }
        if self.filter_id:
            params['filter'] = self.filter_id
        if since:
            params['since'] = since
        
        query_string = '&'.join(f'{k}={v}' for k, v in params.items())
        endpoint = f'/_matrix/client/v3/sync?{query_string}'
        
        result = await self._make_request('GET', endpoint)
        self.next_batch = result.get('next_batch')
        return result
    
    async def get_room_messages(self, room_id: str, from_token: Optional[str] = None, 
                               direction: str = 'b', limit: int = 200) -> Dict:
        """Get historical messages from a room"""
        params = {
            'dir': direction,
            'limit': limit
        }
        if from_token:
            params['from'] = from_token
        
        query_string = '&'.join(f'{k}={v}' for k, v in params.items())
        endpoint = f'/_matrix/client/v3/rooms/{room_id}/messages?{query_string}'
        
        return await self._make_request('GET', endpoint)
    
    async def download_media(self, server_name: str, media_id: str) -> bytes:
        """Download media content"""
        # Try authenticated client-scoped media path first
        try:
            endpoint = f'/_matrix/client/v3/media/download/{server_name}/{media_id}'
            url = urljoin(self.homeserver, endpoint)
            headers = self._get_headers()
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.read()
        except:
            pass
        
        # Fallback to legacy media path
        endpoint = f'/_matrix/media/v3/download/{server_name}/{media_id}'
        url = urljoin(self.homeserver, endpoint)
        
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.read()
            else:
                raise Exception(f"Failed to download media: HTTP {response.status}")
    
    async def get_room_keys_backup(self) -> Optional[Dict]:
        """Get room keys from server backup"""
        try:
            return await self._make_request('GET', '/_matrix/client/v3/room_keys/version')
        except:
            return None
    
    async def get_room_keys(self, room_id: str, version: str) -> Dict:
        """Get specific room keys from backup"""
        endpoint = f'/_matrix/client/v3/room_keys/keys/{room_id}?version={version}'
        return await self._make_request('GET', endpoint)
    
    async def get_room_key_for_session(self, room_id: str, session_id: str, version: str) -> Optional[Dict]:
        """Get a specific session key from backup"""
        try:
            endpoint = f'/_matrix/client/v3/room_keys/keys/{room_id}/{session_id}?version={version}'
            return await self._make_request('GET', endpoint)
        except Exception as e:
            logger.warning(f"Failed to get session key for {room_id}:{session_id}: {e}")
            return None