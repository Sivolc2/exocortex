"""
MCP Client Integration

This module provides a client interface to connect to the local MCP server
and retrieve knowledge base information for chat agents.
"""

import json
import subprocess
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import tempfile
from pydantic import BaseModel

class MCPSearchResult(BaseModel):
    """Result from MCP search operations"""
    entries: List[Dict[str, Any]]
    total_count: int
    query: str

class MCPClient:
    """Client for interacting with the local MCP server"""
    
    def __init__(self, server_script_path: Optional[str] = None):
        """Initialize MCP client
        
        Args:
            server_script_path: Path to mcp_server.py script. If None, uses relative path.
        """
        if server_script_path is None:
            self.server_script_path = str(Path(__file__).parent / "mcp_server.py")
        else:
            self.server_script_path = server_script_path
    
    async def _run_mcp_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Run a command against the MCP server via subprocess
        
        Args:
            command: JSON-RPC command to send to MCP server
            
        Returns:
            Response from MCP server
        """
        try:
            # Create a temporary file with the command
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(command, f)
                temp_file = f.name
            
            # Run the MCP server with the command
            process = await asyncio.create_subprocess_exec(
                'python', self.server_script_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send the command as JSON-RPC
            command_json = json.dumps(command) + '\n'
            stdout, stderr = await process.communicate(command_json.encode())
            
            if process.returncode != 0:
                raise RuntimeError(f"MCP server error: {stderr.decode()}")
            
            # Parse response
            response_lines = stdout.decode().strip().split('\n')
            for line in response_lines:
                if line.strip():
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
                        
            raise RuntimeError("No valid JSON response from MCP server")
            
        except Exception as e:
            raise RuntimeError(f"Failed to communicate with MCP server: {e}")
        finally:
            # Clean up temp file
            try:
                Path(temp_file).unlink()
            except:
                pass
    
    async def search_knowledge(self, query: str, source: Optional[str] = None, limit: int = 20) -> MCPSearchResult:
        """Search the knowledge base using MCP server
        
        Args:
            query: Search terms
            source: Optional source filter (notion, obsidian, discord)
            limit: Maximum results to return
            
        Returns:
            Search results from MCP server
        """
        # Use direct function calls for reliability
        return await self._direct_search_fallback(query, source, limit)
    
    async def _direct_search_fallback(self, query: str, source: Optional[str], limit: int) -> MCPSearchResult:
        """Fallback to direct function calls if subprocess communication fails"""
        try:
            from repo_src.backend.mcp_server import search_knowledge_base
            result = search_knowledge_base(query, source, limit)
            return MCPSearchResult(**result)
        except Exception as e:
            raise RuntimeError(f"Both MCP subprocess and direct calls failed: {e}")
    
    async def read_file(self, file_path: str) -> str:
        """Read a file from the knowledge base
        
        Args:
            file_path: Path to file relative to processed data directory
            
        Returns:
            File contents as string
        """
        # Use direct function calls for reliability
        try:
            from repo_src.backend.mcp_server import get_file_content
            return get_file_content(file_path)
        except Exception as e:
            raise RuntimeError(f"Failed to read file {file_path}: {e}")
    
    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base
        
        Returns:
            Statistics dictionary with source counts, top tags, etc.
        """
        # Use direct function calls for reliability
        try:
            from repo_src.backend.mcp_server import load_knowledge_index
            entries = load_knowledge_index()
            
            source_counts = {}
            tag_counts = {}
            
            for entry in entries:
                source_counts[entry.source] = source_counts.get(entry.source, 0) + 1
                
                if entry.tags:
                    tags = [tag.strip() for tag in entry.tags.split(',')]
                    for tag in tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # Get top tags
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
            
            return {
                "total_entries": len(entries),
                "sources": source_counts,
                "top_tags": dict(top_tags),
                "status": "direct_access"
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get knowledge stats: {e}")

# Global MCP client instance
_mcp_client = None

def get_mcp_client() -> MCPClient:
    """Get or create the global MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client