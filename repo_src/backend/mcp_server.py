#!/usr/bin/env python3
"""
MCP Server for Exocortex Knowledge Base

This server exposes the knowledge base data from @repo_src/backend/data/ as MCP resources and tools.
Provides access to:
- Knowledge index (structured metadata about all files)
- Processed markdown files from Notion, Obsidian, and Discord
- Search functionality across the knowledge base
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Sequence

from mcp.server import Server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    ListResourcesResult, ReadResourceResult, ListToolsResult, CallToolResult
)
from mcp.server.stdio import stdio_server
from pydantic import BaseModel

# Data paths
DATA_ROOT = Path(__file__).parent / "data"
PROCESSED_ROOT = DATA_ROOT / "processed" / "current"
INDEX_ROOT = DATA_ROOT / "index"
KNOWLEDGE_INDEX_JSON = INDEX_ROOT / "knowledge_index.json"
KNOWLEDGE_INDEX_CSV = INDEX_ROOT / "knowledge_index.csv"

# Initialize MCP server
server = Server("exocortex-knowledge")

class IndexEntry(BaseModel):
    """Knowledge base index entry model"""
    id: int
    file_path: str
    source: str
    description: Optional[str] = None
    tags: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

def load_knowledge_index() -> List[IndexEntry]:
    """Load the knowledge index from JSON file"""
    try:
        with open(KNOWLEDGE_INDEX_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [IndexEntry(**entry) for entry in data.get('entries', [])]
    except Exception as e:
        print(f"Error loading knowledge index: {e}", file=sys.stderr)
        return []

def get_file_content(file_path: str) -> str:
    """Get content of a processed file"""
    # Check if this is an obsidian file that needs path translation
    if not file_path.startswith(('obsidian/', 'notion/', 'discord/', 'chat_exports/')):
        # Add obsidian prefix for bare filenames from the knowledge index
        if file_path.endswith('.md'):
            # Transform spaces to underscores and other characters for obsidian file naming
            transformed_file_path = file_path.replace(' ', '_').replace('(', '_').replace(')', '_').replace('/', '_')
            full_path = PROCESSED_ROOT / "obsidian" / transformed_file_path
        else:
            full_path = PROCESSED_ROOT / file_path
    else:
        full_path = PROCESSED_ROOT / file_path
    
    # Security check: ensure file is within allowed directory
    try:
        full_path = full_path.resolve()
        if PROCESSED_ROOT.resolve() not in full_path.parents and full_path != PROCESSED_ROOT.resolve():
            raise ValueError("File path outside allowed directory")
    except Exception:
        raise ValueError("Invalid file path")
    
    try:
        return full_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        # If the direct path doesn't work, try finding the file with different naming conventions
        if file_path.endswith('.md') and not file_path.startswith(('obsidian/', 'notion/', 'discord/', 'chat_exports/')):
            # Try alternative transformations for obsidian files
            alternatives = [
                file_path.replace(' ', '_'),  # Simple space to underscore
                file_path.replace(' - ', '_-_'),  # Specific pattern transformation
                file_path.replace(' ', '_').replace('(', '_(').replace(')', ')_'),  # More specific transformations
            ]
            
            for alt_path in alternatives:
                try:
                    alt_full_path = PROCESSED_ROOT / "obsidian" / alt_path
                    if alt_full_path.exists():
                        return alt_full_path.read_text(encoding='utf-8')
                except Exception:
                    continue
        
        # Handle Discord file reorganization - daily files consolidated into weekly files
        elif file_path.startswith('discord/'):
            # Try to find the content in consolidated weekly files
            if '/2025-' in file_path:
                # Extract date from path like discord/aimibot-channel/2025-06-23.md
                import re
                from datetime import datetime, timedelta
                
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})\.md$', file_path)
                if date_match:
                    date_str = date_match.group(1)
                    try:
                        target_date = datetime.strptime(date_str, '%Y-%m-%d')
                        
                        # Find the Monday of the week containing this date
                        monday = target_date - timedelta(days=target_date.weekday())
                        
                        # Find the Sunday of the same week
                        sunday = monday + timedelta(days=6)
                        
                        # Create the weekly file name pattern
                        week_filename = f"{monday.strftime('%Y-%m-%d')}_to_{sunday.strftime('%Y-%m-%d')}.md"
                        
                        # Try different possible locations for the weekly file
                        potential_paths = [
                            PROCESSED_ROOT / file_path.replace(date_str + '.md', week_filename),
                            PROCESSED_ROOT / "chat_exports" / f"week_{monday.strftime('%Y-%m-%d')}.md",
                        ]
                        
                        for potential_path in potential_paths:
                            if potential_path.exists():
                                return potential_path.read_text(encoding='utf-8')
                    except ValueError:
                        pass  # Invalid date format, continue with other fallbacks
        
        raise FileNotFoundError(f"Could not read file {file_path}: File not found")
    except Exception as e:
        raise FileNotFoundError(f"Could not read file {file_path}: {e}")

def search_knowledge_base(query: str, source_filter: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """Search through the knowledge base"""
    entries = load_knowledge_index()
    query_lower = query.lower()
    
    # Filter by source if specified
    if source_filter:
        entries = [e for e in entries if e.source == source_filter]
    
    # Search in description and tags
    matching_entries = []
    for entry in entries:
        if (entry.description and query_lower in entry.description.lower()) or \
           (entry.tags and query_lower in entry.tags.lower()) or \
           query_lower in entry.file_path.lower():
            matching_entries.append(entry.model_dump())
    
    # Limit results
    limited_entries = matching_entries[:limit]
    
    return {
        "entries": limited_entries,
        "total_count": len(matching_entries),
        "query": query
    }

# === MCP Resources ===

@server.list_resources()
async def list_resources() -> ListResourcesResult:
    """List available knowledge base resources"""
    resources = [
        Resource(
            uri="knowledge-index://json",
            name="Knowledge Index (JSON)",
            description="Complete structured index of all knowledge base files",
            mimeType="application/json"
        ),
        Resource(
            uri="knowledge-index://csv", 
            name="Knowledge Index (CSV)",
            description="Complete structured index of all knowledge base files in CSV format",
            mimeType="text/csv"
        )
    ]
    return ListResourcesResult(resources=resources)

@server.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    """Read a resource by URI"""
    if uri == "knowledge-index://json":
        try:
            content = KNOWLEDGE_INDEX_JSON.read_text(encoding='utf-8')
            return ReadResourceResult(
                contents=[TextContent(type="text", text=content)]
            )
        except Exception as e:
            raise RuntimeError(f"Could not read knowledge index JSON: {e}")
    
    elif uri == "knowledge-index://csv":
        try:
            content = KNOWLEDGE_INDEX_CSV.read_text(encoding='utf-8')
            return ReadResourceResult(
                contents=[TextContent(type="text", text=content)]
            )
        except Exception as e:
            raise RuntimeError(f"Could not read knowledge index CSV: {e}")
    
    else:
        raise ValueError(f"Unknown resource URI: {uri}")

# === MCP Tools ===

@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available tools"""
    tools = [
        Tool(
            name="search_knowledge",
            description="Search through the knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search terms"},
                    "source": {"type": "string", "enum": ["notion", "obsidian", "discord"], "description": "Optional source filter"},
                    "limit": {"type": "integer", "default": 20, "maximum": 100, "description": "Max results"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_knowledge_stats",
            description="Get statistics about the knowledge base",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="read_file",
            description="Read contents of a knowledge base file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file relative to processed data directory"}
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="get_files_by_source",
            description="Get all files from a specific source",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "enum": ["notion", "obsidian", "discord"], "description": "Source to filter by"},
                    "limit": {"type": "integer", "default": 50, "maximum": 200, "description": "Max results"}
                },
                "required": ["source"]
            }
        )
    ]
    return ListToolsResult(tools=tools)

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """Handle tool calls"""
    
    if name == "search_knowledge":
        query = arguments.get("query", "")
        source = arguments.get("source")
        limit = arguments.get("limit", 20)
        
        if limit > 100:
            limit = 100
        
        valid_sources = {'notion', 'obsidian', 'discord'}
        if source and source not in valid_sources:
            raise ValueError(f"Invalid source. Must be one of: {', '.join(valid_sources)}")
        
        result = search_knowledge_base(query, source, limit)
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))]
        )
    
    elif name == "get_knowledge_stats":
        entries = load_knowledge_index()
        
        # Count by source
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
        
        stats = {
            "total_entries": len(entries),
            "sources": source_counts,
            "top_tags": dict(top_tags),
            "data_root": str(DATA_ROOT),
            "last_updated": max([e.updated_at for e in entries if e.updated_at], default="Unknown")
        }
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(stats, indent=2))]
        )
    
    elif name == "read_file":
        file_path = arguments.get("file_path", "")
        if not file_path:
            raise ValueError("file_path is required")
        
        try:
            content = get_file_content(file_path)
            return CallToolResult(
                content=[TextContent(type="text", text=content)]
            )
        except Exception as e:
            raise RuntimeError(f"Could not read file {file_path}: {e}")
    
    elif name == "get_files_by_source":
        source = arguments.get("source", "")
        limit = arguments.get("limit", 50)
        
        valid_sources = {'notion', 'obsidian', 'discord'}
        if source not in valid_sources:
            raise ValueError(f"Invalid source. Must be one of: {', '.join(valid_sources)}")
        
        if limit > 200:
            limit = 200
        
        entries = load_knowledge_index()
        source_entries = [e.model_dump() for e in entries if e.source == source]
        limited_entries = source_entries[:limit]
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(limited_entries, indent=2))]
        )
    
    else:
        raise ValueError(f"Unknown tool: {name}")

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # stdio_server() handles the communication protocol
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())
    
    asyncio.run(main())