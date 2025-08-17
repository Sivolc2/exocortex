# MCP-Powered Knowledge Chat

This document describes the new MCP-powered chat functionality that allows users to query their personal knowledge base directly through a conversational interface.

## Overview

The MCP (Model Context Protocol) chat system provides a new way to interact with your knowledge base by:

1. **Intelligent Search**: Extracts key search terms from user queries
2. **Contextual Retrieval**: Finds relevant documents using the MCP server
3. **Smart Selection**: Uses LLM to choose the most relevant files
4. **Contextualized Responses**: Generates answers based on your personal knowledge

## Architecture

```
User Query → Search Term Extraction → MCP Knowledge Search → File Selection → Content Loading → Response Generation
```

### Components

- **MCP Client** (`mcp_client.py`): Interface to communicate with MCP server
- **MCP Chat Agent** (`agents/mcp_chat_agent.py`): Orchestrates the knowledge-based chat flow
- **MCP Chat Router** (`routers/mcp_chat.py`): FastAPI endpoints for MCP chat functionality
- **Frontend Integration**: New "Knowledge Chat" tab in the UI

## Usage

### Frontend

1. Open the application in your browser
2. Click on the "Knowledge Chat" tab
3. Ask questions about your notes, research, meetings, or any topics in your knowledge base

Example queries:
- "What research have I done on AI?"
- "Tell me about my meetings with colleagues"
- "What are my thoughts on post-labor economics?"
- "Any notes about specific projects or people?"

### API Endpoints

#### POST `/api/mcp-chat/`
Main chat endpoint that processes user queries through the MCP system.

**Request:**
```json
{
  "prompt": "What research have I done on AI?",
  "selection_model": "anthropic/claude-3-haiku",
  "execution_model": "anthropic/claude-3.5-sonnet",
  "enabled_sources": {"notion": true, "obsidian": true, "discord": true}
}
```

**Response:**
```json
{
  "response": "Based on your knowledge base, you've conducted research on...",
  "selected_files": ["obsidian/AI_Research.md", "notion/ai-project.md"],
  "file_token_info": [
    {"file_path": "obsidian/AI_Research.md", "token_count": 850},
    {"file_path": "notion/ai-project.md", "token_count": 1200}
  ],
  "total_tokens": 2050
}
```

#### GET `/api/mcp-chat/status`
Check MCP server connectivity and knowledge base statistics.

#### GET `/api/mcp-chat/search/{query}`
Direct search endpoint for the knowledge base.

## Configuration

### Environment Variables

```bash
# Required for LLM functionality
OPENROUTER_API_KEY=your_openrouter_api_key

# Optional: Model preferences (defaults provided)
SELECTION_MODEL=anthropic/claude-3-haiku
EXECUTION_MODEL=anthropic/claude-3.5-sonnet
```

### Model Configuration

The system uses two models:
- **Selection Model**: For extracting search terms and selecting relevant files (fast, efficient)
- **Execution Model**: For generating final responses (powerful, nuanced)

## Features

### Smart Search Term Extraction
The system analyzes user queries to identify:
- Main topics and concepts
- Proper nouns (people, companies, projects)
- Technical terms and domains
- Intent indicators

### Contextual File Selection
- Searches across all sources (Notion, Obsidian, Discord)
- Ranks results by relevance and description quality
- Uses LLM to select the most relevant files for the specific query
- Limits context to prevent token overflow

### Comprehensive Response Generation
- Synthesizes information from multiple sources
- Cites specific files and sources
- Provides conversational, helpful responses
- Acknowledges limitations when information is incomplete

## Testing

Run the test suite to verify functionality:

```bash
cd /path/to/backend
python test_mcp_chat.py
```

The test suite validates:
- MCP client connectivity
- Knowledge base search functionality
- File reading capabilities
- Statistics retrieval

## Troubleshooting

### Common Issues

1. **No search results**: Check that the MCP server is running and knowledge index is populated
2. **API errors**: Verify OPENROUTER_API_KEY is set correctly
3. **Import errors**: Ensure all dependencies are installed (`pip install -r requirements.txt`)
4. **File read errors**: Check file permissions and paths in the processed data directory

### Debug Mode

Enable debug output by running:
```bash
python test_mcp_chat.py
```

This will show detailed information about:
- Search term extraction
- Knowledge base queries
- File selection process
- Response generation

## Comparison with Repository Chat

| Feature | Repository Chat | Knowledge Chat |
|---------|----------------|----------------|
| **Data Source** | Current repository files | Personal knowledge base |
| **Scope** | Code documentation | Notes, research, meetings |
| **Search Method** | File selection agent | MCP-powered search |
| **Context** | Technical documentation | Personal insights and history |
| **Use Case** | Code understanding | Knowledge exploration |

## Future Enhancements

Planned improvements:
- **Memory**: Remember conversation context across queries
- **Citations**: More detailed source attribution
- **Filtering**: Advanced source and date filtering
- **Export**: Save interesting conversations
- **Analytics**: Track frequently accessed knowledge areas