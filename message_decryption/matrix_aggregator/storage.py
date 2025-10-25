import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class MatrixStorage:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS rooms (
                    room_id TEXT PRIMARY KEY,
                    name TEXT,
                    topic TEXT,
                    avatar_url TEXT,
                    canonical_alias TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    room_id TEXT,
                    sender TEXT,
                    event_type TEXT,
                    content TEXT,
                    origin_server_ts INTEGER,
                    decrypted_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (room_id) REFERENCES rooms (room_id)
                );
                
                CREATE TABLE IF NOT EXISTS sync_tokens (
                    id INTEGER PRIMARY KEY,
                    next_batch TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS media_cache (
                    mxc_uri TEXT PRIMARY KEY,
                    local_path TEXT,
                    content_type TEXT,
                    file_size INTEGER,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS room_keys (
                    room_id TEXT,
                    session_id TEXT,
                    session_key TEXT,
                    algorithm TEXT,
                    PRIMARY KEY (room_id, session_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_room_timestamp 
                ON events (room_id, origin_server_ts);
                
                CREATE INDEX IF NOT EXISTS idx_events_sender 
                ON events (sender);
            ''')
    
    def store_sync_token(self, next_batch: str):
        """Store the next_batch token for sync continuation"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO sync_tokens (id, next_batch) VALUES (1, ?)',
                (next_batch,)
            )
    
    def get_sync_token(self) -> Optional[str]:
        """Get the last sync token"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT next_batch FROM sync_tokens WHERE id = 1')
            row = cursor.fetchone()
            return row[0] if row else None
    
    def store_room(self, room_id: str, room_data: Dict):
        """Store room metadata"""
        name = room_data.get('name')
        topic = room_data.get('topic')
        avatar_url = room_data.get('avatar_url')
        canonical_alias = room_data.get('canonical_alias')
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO rooms 
                (room_id, name, topic, avatar_url, canonical_alias, last_updated)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (room_id, name, topic, avatar_url, canonical_alias))
    
    def store_event(self, event: Dict, decrypted_content: Optional[str] = None):
        """Store a Matrix event"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO events 
                (event_id, room_id, sender, event_type, content, origin_server_ts, decrypted_content)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                event['event_id'],
                event['room_id'],
                event['sender'],
                event['type'],
                json.dumps(event.get('content', {})),
                event.get('origin_server_ts', 0),
                decrypted_content
            ))
    
    def store_media(self, mxc_uri: str, local_path: str, content_type: str, file_size: int):
        """Store media cache information"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO media_cache 
                (mxc_uri, local_path, content_type, file_size)
                VALUES (?, ?, ?, ?)
            ''', (mxc_uri, local_path, content_type, file_size))
    
    def get_media_path(self, mxc_uri: str) -> Optional[str]:
        """Get local path for cached media"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT local_path FROM media_cache WHERE mxc_uri = ?',
                (mxc_uri,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    
    def store_room_key(self, room_id: str, session_id: str, session_key: str, algorithm: str):
        """Store E2EE room key"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO room_keys 
                (room_id, session_id, session_key, algorithm)
                VALUES (?, ?, ?, ?)
            ''', (room_id, session_id, session_key, algorithm))
    
    def get_room_messages(self, room_id: str, limit: int = 1000) -> List[Dict]:
        """Get stored messages for a room"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM events 
                WHERE room_id = ? AND event_type = 'm.room.message'
                ORDER BY origin_server_ts ASC
                LIMIT ?
            ''', (room_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_rooms(self) -> List[Dict]:
        """Get all stored rooms"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM rooms ORDER BY last_updated DESC')
            return [dict(row) for row in cursor.fetchall()]