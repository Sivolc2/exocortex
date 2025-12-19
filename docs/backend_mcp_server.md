# Exocortex Knowledge Base MCP Server

This MCP (Model Context Protocol) server provides AI models with access to your personal knowledge base, including processed files from Notion, Obsidian, and Discord.

## Features

### Resources
- **Knowledge Index (JSON)**: Complete structured index of all knowledge base files
- **Knowledge Index (CSV)**: Same index in CSV format for analysis
- **Individual Files**: Access any processed markdown file by path

### Tools
- **search_knowledge**: Search through descriptions, tags, and file paths
- **get_knowledge_stats**: Get statistics about your knowledge base
- **get_files_by_source**: List files from a specific source (notion, obsidian, discord)

## Setup

### 1. Install Dependencies

```bash
cd /Users/starsong/Central/Projects/interactives/exocortex/repo_src/backend
pip install -r requirements.txt
```

### 2. Test the Server

Test the MCP server using the built-in CLI inspector:

```bash
# Test server functionality
python -c "import sys; sys.path.append('.'); from mcp_server import mcp; print('Server loads successfully')"

# Test with MCP CLI inspector (if available)
mcp dev mcp_server.py
```

### 3. Configure Claude Desktop

#### Option A: Manual Configuration
1. Open `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Add the exocortex-knowledge server configuration:

```json
{
  "mcpServers": {
    "exocortex-knowledge": {
      "command": "python",
      "args": [
        "/Users/starsong/Central/Projects/interactives/exocortex/repo_src/backend/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/starsong/Central/Projects/interactives/exocortex/repo_src/backend"
      }
    }
  }
}
```

#### Option B: Use Provided Configuration
Copy the provided configuration:

```bash
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Note**: This will overwrite your existing Claude Desktop configuration. If you have other MCP servers, merge the configurations manually.

### 4. Restart Claude Desktop

After updating the configuration, restart Claude Desktop to load the MCP server.

## Usage in Claude

### Accessing Resources
- Attach the knowledge index: "Attach resource `knowledge-index://json`"
- Access a specific file: "Attach resource `file://notion/244771fe-f76d-8071-898d-e592136fd762.md`"

### Using Tools
- Search your knowledge: `search_knowledge(query="AI research", source="obsidian", limit=10)`
- Get statistics: `get_knowledge_stats()`
- List Notion files: `get_files_by_source(source="notion", limit=20)`

## Example Interactions

### Search for AI-related content
```
Can you search my knowledge base for content related to "artificial intelligence" and show me the most relevant files?
```

### Get knowledge base overview
```
What's in my knowledge base? Can you give me statistics and show me the top tags?
```

### Access specific content
```
Can you read the file about "AIMibots" from my Notion export and summarize the key points?
```

### Research assistance
```
I'm working on a paper about post-labor economics. Can you search my knowledge base for related content and help me identify key themes and references?
```

## Data Structure

The server accesses:
- **Knowledge Index**: `/repo_src/backend/data/index/knowledge_index.json`
- **Processed Files**: `/repo_src/backend/data/processed/current/`
  - `notion/` - Notion exports with YAML frontmatter
  - `obsidian/` - Obsidian exports with simplified metadata
  - `discord/` - Discord chat logs

## Security Features

- **Path Validation**: All file access is restricted to the processed data directory
- **Input Sanitization**: Search queries and parameters are validated
- **Read-Only Access**: Server provides read-only access to your data

## Troubleshooting

### Server Not Appearing in Claude
1. Check that the Python path in the config is correct
2. Verify dependencies are installed: `pip install -r requirements.txt`
3. Test server directly: `python mcp_server.py` (should start without errors)
4. Check Claude Desktop logs for error messages

### Empty Search Results
- Verify the knowledge index files exist and contain data
- Check file paths in the configuration
- Ensure processed files are in the expected locations

### Permission Errors
- Check file permissions on the data directory
- Ensure Python has read access to all data files
- Verify the PYTHONPATH environment variable is set correctly

## Development

### Adding New Features
- Resources: Add new `@mcp.resource()` decorated functions
- Tools: Add new `@mcp.tool()` decorated functions
- Update the resource list in `list_knowledge_resources()`

### Testing Changes
```bash
# Test server startup
python mcp_server.py

# Test specific functions
python -c "from mcp_server import search_knowledge_base; print(search_knowledge_base('AI', limit=5))"
```

## Data Privacy

This MCP server runs locally and only provides access to your own knowledge base files. No data is transmitted to external services beyond what you explicitly share with Claude during conversations.