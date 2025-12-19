import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import aiofiles

logger = logging.getLogger(__name__)

class ObsidianExporter:
    def __init__(self, storage, media_manager, output_dir: str):
        self.storage = storage
        self.media_manager = media_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize room name for use as filename"""
        if not name:
            return "unnamed_room"
        
        # Replace problematic characters
        sanitized = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_'))
        return sanitized.strip().replace(' ', '_')[:50]
    
    def _format_timestamp(self, timestamp: int) -> str:
        """Format Matrix timestamp to readable format"""
        dt = datetime.fromtimestamp(timestamp / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_relative_media_path(self, local_path: str) -> str:
        """Get relative path to media file for Obsidian"""
        media_path = Path(local_path)
        if media_path.is_absolute():
            try:
                return str(media_path.relative_to(self.output_dir))
            except ValueError:
                return str(media_path)
        return local_path
    
    async def _format_message_content(self, event: Dict, media_files: Dict[str, str]) -> str:
        """Format message content as Markdown"""
        content = json.loads(event['content'])
        decrypted = event.get('decrypted_content')
        
        if decrypted:
            try:
                content = json.loads(decrypted)
            except:
                pass
        
        msgtype = content.get('msgtype', 'm.text')
        body = content.get('body', '')
        
        # Handle different message types
        if msgtype == 'm.text':
            # Convert Matrix formatting to Markdown
            formatted_body = content.get('formatted_body', body)
            if content.get('format') == 'org.matrix.custom.html':
                # Basic HTML to Markdown conversion
                formatted_body = formatted_body.replace('<strong>', '**').replace('</strong>', '**')
                formatted_body = formatted_body.replace('<em>', '*').replace('</em>', '*')
                formatted_body = formatted_body.replace('<br>', '\n').replace('<br/>', '\n')
                formatted_body = formatted_body.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                return formatted_body
            return body
        
        elif msgtype == 'm.image':
            alt_text = body or 'Image'
            if 'image' in media_files:
                rel_path = self._get_relative_media_path(media_files['image'])
                return f"![{alt_text}]({rel_path})"
            return f"[Image: {alt_text}]"
        
        elif msgtype == 'm.file':
            filename = body or 'File'
            if 'file' in media_files:
                rel_path = self._get_relative_media_path(media_files['file'])
                return f"[📎 {filename}]({rel_path})"
            return f"[📎 {filename}]"
        
        elif msgtype == 'm.audio':
            if 'audio' in media_files:
                rel_path = self._get_relative_media_path(media_files['audio'])
                return f"🎵 [{body or 'Audio'}]({rel_path})"
            return f"🎵 {body or 'Audio message'}"
        
        elif msgtype == 'm.video':
            if 'video' in media_files:
                rel_path = self._get_relative_media_path(media_files['video'])
                return f"🎬 [{body or 'Video'}]({rel_path})"
            return f"🎬 {body or 'Video message'}"
        
        elif event.get('type') == 'm.sticker':
            if 'sticker' in media_files:
                rel_path = self._get_relative_media_path(media_files['sticker'])
                return f"![Sticker: {body}]({rel_path})"
            return f"[Sticker: {body}]"
        
        else:
            return body or f"[{msgtype} message]"
    
    async def export_room_to_markdown(self, room_id: str) -> Optional[str]:
        """Export a room's messages to Markdown format"""
        try:
            # Get room info
            rooms = self.storage.get_all_rooms()
            room_info = next((r for r in rooms if r['room_id'] == room_id), None)
            if not room_info:
                logger.error(f"Room {room_id} not found")
                return None
            
            room_name = room_info.get('name') or room_info.get('canonical_alias') or room_id
            
            # Get messages
            messages = self.storage.get_room_messages(room_id)
            if not messages:
                logger.info(f"No messages found for room {room_id}")
                return None
            
            # Generate filename
            safe_name = self._sanitize_filename(room_name)
            filename = f"{safe_name}_{room_id.replace('!', '').replace(':', '_')}.md"
            file_path = self.output_dir / filename
            
            # Create Markdown content
            markdown_lines = []
            
            # Header with metadata
            markdown_lines.extend([
                f"# {room_name}",
                "",
                f"**Room ID:** {room_id}",
                f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Message Count:** {len(messages)}",
                ""
            ])
            
            if room_info.get('topic'):
                markdown_lines.extend([
                    f"**Topic:** {room_info['topic']}",
                    ""
                ])
            
            markdown_lines.append("---\n")
            
            # Process messages
            current_date = None
            for msg in messages:
                msg_timestamp = msg['origin_server_ts']
                msg_date = datetime.fromtimestamp(msg_timestamp / 1000).date()
                
                # Add date header if date changed
                if current_date != msg_date:
                    current_date = msg_date
                    markdown_lines.extend([
                        "",
                        f"## {msg_date.strftime('%A, %B %d, %Y')}",
                        ""
                    ])
                
                # Download media if present
                media_files = await self.media_manager.process_message_media(msg)
                
                # Format message
                sender = msg['sender']
                timestamp = self._format_timestamp(msg_timestamp)
                content = await self._format_message_content(msg, media_files)
                
                # Add message to markdown
                markdown_lines.extend([
                    f"**{sender}** *{timestamp}*",
                    "",
                    content,
                    ""
                ])
            
            # Write to file
            markdown_content = "\n".join(markdown_lines)
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(markdown_content)
            
            logger.info(f"Exported {len(messages)} messages to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to export room {room_id}: {e}")
            return None
    
    async def export_all_rooms(self) -> List[str]:
        """Export all rooms to Markdown"""
        rooms = self.storage.get_all_rooms()
        exported_files = []
        
        for room in rooms:
            file_path = await self.export_room_to_markdown(room['room_id'])
            if file_path:
                exported_files.append(file_path)
        
        # Create index file
        index_path = self.output_dir / "README.md"
        await self._create_index_file(exported_files, str(index_path))
        
        return exported_files
    
    async def _create_index_file(self, exported_files: List[str], index_path: str):
        """Create an index file listing all exported rooms"""
        index_lines = [
            "# Matrix Message Export",
            "",
            f"Export generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total rooms exported: {len(exported_files)}",
            "",
            "## Rooms",
            ""
        ]
        
        for file_path in exported_files:
            filename = Path(file_path).name
            room_name = filename.replace('.md', '').replace('_', ' ')
            index_lines.append(f"- [{room_name}]({filename})")
        
        async with aiofiles.open(index_path, 'w', encoding='utf-8') as f:
            await f.write("\n".join(index_lines))