# Data Source Adapters

This directory contains modular "fetcher" scripts that act as adapters to pull data from various sources (e.g., Obsidian, Notion, Discord). The goal is to create a plug-and-play system for aggregating information into a unified format.

## Architecture

- **`base_fetcher.py`**: Defines an abstract base class (`BaseFetcher`) that all other fetchers should inherit from. This ensures a consistent interface.
- **`fetch_*.py`**: Each file is an adapter for a specific data source. It implements the logic to connect to the service, fetch the data, and transform it into the standard format.
- **Orchestrator (`repo_src/scripts/combine_sources.py`)**: A central script that reads the project's `config.yaml`, determines which data sources are enabled, and runs the corresponding fetchers.

## Standardized Data Format

Each fetcher's `fetch()` method must return a list of dictionaries, where each dictionary represents a single document or data entry. The structure is as follows:

```json
{
  "source": "string",
  "id": "string (unique within the source)",
  "content": "string (the main body of the document)",
  "metadata": {
    "key": "value"
  }
}
```

- `source`: A unique identifier for the data source (e.g., "obsidian", "notion").
- `id`: A unique identifier for the item within its source (e.g., file path for Obsidian, page ID for Notion).
- `content`: The full text content of the item, preferably in Markdown format.
- `metadata`: A dictionary containing any other relevant information, such as `title`, `created_at`, `author`, `url`, etc.

## How to Add a New Data Source

1.  **Create the Adapter File**: Create a new file `fetch_mynewsource.py` in this directory.
2.  **Implement the Fetcher Class**:
    ```python
    from .base_fetcher import BaseFetcher
    from typing import List, Dict, Any

    class MyNewSourceFetcher(BaseFetcher):
        def __init__(self, config: Dict[str, Any]):
            self.config = config
            # Initialize API clients, etc. here

        def fetch(self) -> List[Dict[str, Any]]:
            # Your logic to fetch and format data goes here
            # Return a list of dictionaries in the standard format
            pass
    ```
3.  **Update `config.yaml`**: Add a new entry for `mynewsource` under the `data_sources` key in the root `config.yaml`.
4.  **Update Orchestrator**: The main script `combine_sources.py` should automatically detect and run your new fetcher if it's enabled in the config. No changes should be needed if you follow the naming convention.
5.  **Add Dependencies**: If your new adapter requires any new Python packages, add them to `repo_src/backend/requirements.txt`.
6.  **Add Credentials**: If it requires API keys, add them to `repo_src/backend/.env` and the `repo_src/scripts/setup-env.sh` template.