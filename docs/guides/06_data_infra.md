Of course. I will plan and implement a script that pulls data from Discord, Notion, and Obsidian, and combines them into a single data source. The design will be modular to allow for easy extension with new data sources in the future.

### Plan

1.  **Create a New Directory for Data Source Adapters:** I'll create `repo_src/backend/data_sources/` to house the individual fetcher modules (adapters). This keeps the logic organized and separate from general-purpose scripts.

2.  **Develop Individual Fetcher Modules (Adapters):**
    *   **`fetch_obsidian.py`:** This adapter will read `.md` files from a specified local directory (the Obsidian vault). This can be fully implemented as it only requires local file access.
    *   **`fetch_notion.py`:** This adapter will be a placeholder demonstrating how to connect to the Notion API. It will include comments on required dependencies (`notion-client`), environment variables (`NOTION_API_KEY`), and configuration (`database_id`).
    *   **`fetch_discord.py`:** Similar to the Notion adapter, this will be a placeholder for fetching chat logs. It will outline the need for `discord.py`, a `DISCORD_BOT_TOKEN`, and server/channel IDs.
    *   **`base_fetcher.py`:** I'll define a simple abstract base class to establish a contract for what each fetcher should do, promoting consistency.

3.  **Define a Standardized Data Structure:** Each adapter will return a list of dictionaries with a consistent structure: `{ "source": str, "id": str, "content": str, "metadata": dict }`. This allows the main script to process data from any source uniformly.

4.  **Implement the Main Orchestrator Script:**
    *   I'll create `repo_src/scripts/combine_sources.py`.
    *   This script will load configuration from `config.yaml`.
    *   It will dynamically import and run all configured data source adapters.
    *   It will aggregate the results from all adapters.
    *   Finally, it will save the combined data into a single timestamped JSON file in a new `repo_src/backend/data/processed/` directory.

5.  **Update Configuration:**
    *   I'll add a `data_sources` section to `config.yaml` to enable/disable and configure each source.
    *   I'll add `NOTION_API_KEY` and `DISCORD_BOT_TOKEN` to the `repo_src/scripts/setup-env.sh` script so users are prompted to configure them.
    *   New dependencies (`notion-client`, `discord.py`) will be added to `repo_src/backend/requirements.txt`.

6.  **Add Documentation and a `pnpm` Script:**
    *   A `README.md` will be added to the `repo_src/backend/data_sources/` directory.
    *   A new script `data:combine` will be added to the root `package.json`.

Here are the file creations and modifications.

```diff
--- a/.gitignore
+++ b/.gitignore
@@ -34,6 +34,9 @@
 .cache/
 .pytest_cache/
 
+# Processed data
+repo_src/backend/data/processed/
+
 # Jupyter
 .ipynb_checkpoints/
 *.ipynb
--- a/config.yaml
+++ b/config.yaml
@@ -7,6 +7,16 @@
   - "project_goals.md"
 
 vault_extensions:
-  - ".md"
+- ".md"
 exclude_patterns:
-  - ".obsidian" 
+  - ".obsidian"
+
+data_sources:
+  obsidian:
+    enabled: true
+    vault_path: "repo_src/backend/documents" # Path relative to project root
+  notion:
+    enabled: false # Set to true and fill in details below to enable
+    database_id: "your_notion_database_id"
+  discord:
+    enabled: false # Set to true and fill in details below to enable
+    server_id: "your_discord_server_id" # Also called Guild ID
+    channel_ids:
+      - "your_channel_id_1"
+      - "your_channel_id_2"
--- a/package.json
+++ b/package.json
@@ -19,6 +19,7 @@
     "ci": "pnpm lint && pnpm typecheck && pnpm test",
     "docs:serve": "mkdocs serve",
     "docs:build": "mkdocs build",
+    "data:combine": "python repo_src/scripts/combine_sources.py",
     "obsidian:sync": "./repo_src/scripts/sync-obsidian.sh",
     "obsidian:sync-incremental": "./repo_src/scripts/sync-obsidian-incremental.sh",
     "obsidian:watch": "./repo_src/scripts/watch-obsidian.sh",
--- a/repo_src/backend/requirements.txt
+++ b/repo_src/backend/requirements.txt
@@ -6,4 +6,6 @@
 psycopg2-binary # Keep if you plan to support PostgreSQL, otherwise remove for pure SQLite 
 anthropic
 pyyaml
-tiktoken 
+tiktoken
+notion-client # For Notion data source
+discord.py # For Discord data source
--- a/repo_src/scripts/setup-env.sh
+++ b/repo_src/scripts/setup-env.sh
@@ -23,6 +23,13 @@
 # Optional: For OpenRouter analytics/tracking
 YOUR_SITE_URL="http://localhost:5173"
 YOUR_APP_NAME="AI-Friendly Repo Chat"
+
+# --- Data Source API Keys (Optional) ---
+# Get your key from https://www.notion.so/my-integrations
+NOTION_API_KEY="secret_..."
+
+# Get your bot token from the Discord Developer Portal
+DISCORD_BOT_TOKEN="your_discord_bot_token_here"
 EOF
 
     echo "${BACKEND_ENV_FILE} created."
```
```diff
--- /dev/null
+++ b/repo_src/backend/data_sources/README.md
@@ -0,0 +1,52 @@
+# Data Source Adapters
+
+This directory contains modular "fetcher" scripts that act as adapters to pull data from various sources (e.g., Obsidian, Notion, Discord). The goal is to create a plug-and-play system for aggregating information into a unified format.
+
+## Architecture
+
+- **`base_fetcher.py`**: Defines an abstract base class (`BaseFetcher`) that all other fetchers should inherit from. This ensures a consistent interface.
+- **`fetch_*.py`**: Each file is an adapter for a specific data source. It implements the logic to connect to the service, fetch the data, and transform it into the standard format.
+- **Orchestrator (`repo_src/scripts/combine_sources.py`)**: A central script that reads the project's `config.yaml`, determines which data sources are enabled, and runs the corresponding fetchers.
+
+## Standardized Data Format
+
+Each fetcher's `fetch()` method must return a list of dictionaries, where each dictionary represents a single document or data entry. The structure is as follows:
+
+```json
+{
+  "source": "string",
+  "id": "string (unique within the source)",
+  "content": "string (the main body of the document)",
+  "metadata": {
+    "key": "value"
+  }
+}
+```
+
+- `source`: A unique identifier for the data source (e.g., "obsidian", "notion").
+- `id`: A unique identifier for the item within its source (e.g., file path for Obsidian, page ID for Notion).
+- `content`: The full text content of the item, preferably in Markdown format.
+- `metadata`: A dictionary containing any other relevant information, such as `title`, `created_at`, `author`, `url`, etc.
+
+## How to Add a New Data Source
+
+1.  **Create the Adapter File**: Create a new file `fetch_mynewsource.py` in this directory.
+2.  **Implement the Fetcher Class**:
+    ```python
+    from .base_fetcher import BaseFetcher
+    from typing import List, Dict, Any
+
+    class MyNewSourceFetcher(BaseFetcher):
+        def __init__(self, config: Dict[str, Any]):
+            self.config = config
+            # Initialize API clients, etc. here
+
+        def fetch(self) -> List[Dict[str, Any]]:
+            # Your logic to fetch and format data goes here
+            # Return a list of dictionaries in the standard format
+            pass
+    ```
+3.  **Update `config.yaml`**: Add a new entry for `mynewsource` under the `data_sources` key in the root `config.yaml`.
+4.  **Update Orchestrator**: The main script `combine_sources.py` should automatically detect and run your new fetcher if it's enabled in the config. No changes should be needed if you follow the naming convention.
+5.  **Add Dependencies**: If your new adapter requires any new Python packages, add them to `repo_src/backend/requirements.txt`.
+6.  **Add Credentials**: If it requires API keys, add them to `repo_src/backend/.env` and the `repo_src/scripts/setup-env.sh` template.
--- /dev/null
+++ b/repo_src/backend/data_sources/__init__.py
@@ -0,0 +1 @@
+# This file makes Python treat the data_sources directory as a package.
--- /dev/null
+++ b/repo_src/backend/data_sources/base_fetcher.py
@@ -0,0 +1,18 @@
+from abc import ABC, abstractmethod
+from typing import List, Dict, Any
+
+class BaseFetcher(ABC):
+    """
+    Abstract base class for data source fetchers.
+    
+    Each fetcher is responsible for connecting to a specific data source,
+    retrieving data, and formatting it into a standardized structure.
+    """
+
+    @abstractmethod
+    def __init__(self, config: Dict[str, Any]):
+        """Initializes the fetcher with its specific configuration."""
+        pass
+
+    @abstractmethod
+    def fetch(self) -> List[Dict[str, Any]]:
+        """Fetches data and returns it in the standard format."""
+        pass
--- /dev/null
+++ b/repo_src/backend/data_sources/fetch_discord.py
@@ -0,0 +1,41 @@
+import os
+from typing import List, Dict, Any
+from .base_fetcher import BaseFetcher
+
+# Note: To use this fetcher, you need to install discord.py:
+# pip install discord.py
+
+# import discord
+
+class DiscordFetcher(BaseFetcher):
+    """
+    Fetches chat logs from Discord channels.
+    
+    This is a placeholder implementation. To make it functional, you would need to:
+    1. Uncomment the discord.py imports and related code.
+    2. Ensure your DISCORD_BOT_TOKEN is set in the .env file.
+    3. Implement the fetching logic within an `async` method, as discord.py is asynchronous.
+    """
+    def __init__(self, config: Dict[str, Any]):
+        self.config = config
+        self.token = os.getenv("DISCORD_BOT_TOKEN")
+        self.server_id = config.get("server_id")
+        self.channel_ids = config.get("channel_ids", [])
+
+    def fetch(self) -> List[Dict[str, Any]]:
+        print("INFO: Skipping Discord fetcher. It is a placeholder and not fully implemented.")
+        if not self.token or "your_discord_bot_token_here" in self.token:
+            print("WARN: DISCORD_BOT_TOKEN not configured. Cannot fetch from Discord.")
+            return []
+        if not self.server_id or not self.channel_ids:
+            print("WARN: Discord server_id or channel_ids not configured in config.yaml.")
+            return []
+
+        # The actual implementation would be asynchronous.
+        # For simplicity in this synchronous orchestrator, you might run the async
+        # code in a separate event loop.
+        # e.g., import asyncio; asyncio.run(self.async_fetch())
+        
+        print("INFO: Returning dummy data for Discord.")
+        return [{
+            "source": "discord",
+            "id": f"{self.server_id}-{self.channel_ids[0]}",
+            "content": "# Discord Chat Log\n\n- User1: Hello!\n- User2: Hi there!\n\n(This is placeholder content)",
+            "metadata": {
+                "server_id": self.server_id,
+                "channel_id": self.channel_ids[0],
+                "message_count": 2
+            }
+        }]
--- /dev/null
+++ b/repo_src/backend/data_sources/fetch_notion.py
@@ -0,0 +1,38 @@
+import os
+from typing import List, Dict, Any
+from .base_fetcher import BaseFetcher
+
+# Note: To use this fetcher, you need to install the Notion client:
+# pip install notion-client
+
+# from notion_client import Client
+
+class NotionFetcher(BaseFetcher):
+    """
+    Fetches content from a Notion database.
+    
+    This is a placeholder implementation. To make it functional, you would need to:
+    1. Uncomment the `notion_client` import and related code.
+    2. Ensure your NOTION_API_KEY is set in the .env file.
+    3. Implement the logic to query the database and convert Notion blocks to Markdown.
+    """
+    def __init__(self, config: Dict[str, Any]):
+        self.config = config
+        self.api_key = os.getenv("NOTION_API_KEY")
+        self.database_id = config.get("database_id")
+        # self.notion = Client(auth=self.api_key) if self.api_key else None
+
+    def fetch(self) -> List[Dict[str, Any]]:
+        print("INFO: Skipping Notion fetcher. It is a placeholder and not fully implemented.")
+        if not self.api_key or "secret_" not in self.api_key:
+            print("WARN: NOTION_API_KEY not configured. Cannot fetch from Notion.")
+            return []
+        
+        print("INFO: Returning dummy data for Notion.")
+        return [{
+            "source": "notion",
+            "id": self.database_id,
+            "content": "# Notion Page Title\n\nThis is the content of the notion page. (Placeholder)",
+            "metadata": {
+                "url": f"https://www.notion.so/{self.database_id}",
+                "title": "Placeholder Notion Page"
+            }
+        }]
--- /dev/null
+++ b/repo_src/backend/data_sources/fetch_obsidian.py
@@ -0,0 +1,36 @@
+import os
+from pathlib import Path
+from typing import List, Dict, Any
+from .base_fetcher import BaseFetcher
+
+class ObsidianFetcher(BaseFetcher):
+    """Fetches documents from a local Obsidian vault (a directory of markdown files)."""
+
+    def __init__(self, config: Dict[str, Any]):
+        self.vault_path = Path(config.get("vault_path", ""))
+
+    def fetch(self) -> List[Dict[str, Any]]:
+        if not self.vault_path.is_dir():
+            print(f"WARN: Obsidian vault path not found or not a directory: {self.vault_path}")
+            return []
+
+        print(f"INFO: Fetching documents from Obsidian vault at {self.vault_path}...")
+        documents = []
+        for file_path in self.vault_path.rglob("*.md"):
+            try:
+                with open(file_path, "r", encoding="utf-8") as f:
+                    content = f.read()
+                
+                doc_id = str(file_path.relative_to(self.vault_path))
+                documents.append({
+                    "source": "obsidian",
+                    "id": doc_id,
+                    "content": content,
+                    "metadata": {
+                        "file_path": doc_id,
+                        "last_modified": os.path.getmtime(file_path)
+                    }
+                })
+            except Exception as e:
+                print(f"ERROR: Failed to read or process file {file_path}: {e}")
+        print(f"INFO: Found {len(documents)} documents in Obsidian vault.")
+        return documents
--- /dev/null
+++ b/repo_src/scripts/combine_sources.py
@@ -0,0 +1,93 @@
+import os
+import json
+import yaml
+from pathlib import Path
+from datetime import datetime
+import importlib
+from dotenv import load_dotenv
+
+# --- Configuration ---
+
+# Set the project root and load environment variables from the backend .env file
+PROJECT_ROOT = Path(__file__).parent.parent.parent
+ENV_PATH = PROJECT_ROOT / "repo_src" / "backend" / ".env"
+load_dotenv(dotenv_path=ENV_PATH)
+
+CONFIG_PATH = PROJECT_ROOT / "config.yaml"
+SOURCES_DIR = PROJECT_ROOT / "repo_src" / "backend" / "data_sources"
+OUTPUT_DIR = PROJECT_ROOT / "repo_src" / "backend" / "data" / "processed"
+
+# --- Helper Functions ---
+
+def load_config() -> dict:
+    """Loads the main YAML configuration file."""
+    print(f"Loading configuration from {CONFIG_PATH}...")
+    with open(CONFIG_PATH, 'r') as f:
+        config = yaml.safe_load(f)
+    if "data_sources" not in config:
+        raise ValueError("Configuration file must contain a 'data_sources' key.")
+    return config["data_sources"]
+
+def get_fetcher_class(source_name: str):
+    """Dynamically imports and returns the fetcher class for a given source."""
+    try:
+        module_name = f"repo_src.backend.data_sources.fetch_{source_name}"
+        class_name = f"{source_name.capitalize()}Fetcher"
+        
+        module = importlib.import_module(module_name)
+        return getattr(module, class_name)
+    except (ImportError, AttributeError) as e:
+        print(f"ERROR: Could not find fetcher for source '{source_name}'. "
+              f"Ensure 'repo_src/backend/data_sources/fetch_{source_name}.py' exists "
+              f"and contains a class named '{class_name}'.\nDetails: {e}")
+        return None
+
+# --- Main Execution ---
+
+def main():
+    """
+    Orchestrates the data fetching and combination process.
+    1. Loads configuration.
+    2. Iterates through enabled data sources.
+    3. Initializes and runs the corresponding fetcher for each source.
+    4. Combines all fetched data.
+    5. Saves the result to a timestamped JSON file.
+    """
+    print("--- Starting Data Combination Process ---")
+    
+    try:
+        data_sources_config = load_config()
+    except (FileNotFoundError, ValueError) as e:
+        print(f"ERROR: Failed to load configuration. {e}")
+        return
+
+    all_data = []
+    
+    for source_name, source_config in data_sources_config.items():
+        if source_config.get("enabled"):
+            print(f"\n>>> Processing enabled source: {source_name}")
+            FetcherClass = get_fetcher_class(source_name)
+            if FetcherClass:
+                try:
+                    fetcher = FetcherClass(source_config)
+                    source_data = fetcher.fetch()
+                    all_data.extend(source_data)
+                    print(f"--- Fetched {len(source_data)} items from {source_name}")
+                except Exception as e:
+                    print(f"ERROR: An error occurred while fetching data from {source_name}: {e}")
+        else:
+            print(f"\n... Skipping disabled source: {source_name}")
+
+    # Ensure the output directory exists
+    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
+
+    # Save the combined data to a file
+    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
+    output_filename = f"combined_data_{timestamp}.json"
+    output_path = OUTPUT_DIR / output_filename
+
+    print(f"\n>>> Writing {len(all_data)} total items to {output_path}...")
+    with open(output_path, "w", encoding="utf-8") as f:
+        json.dump(all_data, f, indent=2, ensure_ascii=False)
+
+    print("\n--- Data Combination Process Complete ---")
+
+if __name__ == "__main__":
+    main()
```