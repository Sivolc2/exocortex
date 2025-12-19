import os
from pathlib import Path
from typing import List, Dict, Any
from .base_fetcher import BaseFetcher

class ObsidianFetcher(BaseFetcher):
    """Fetches documents from a local Obsidian vault (a directory of markdown files)."""

    def __init__(self, config: Dict[str, Any]):
        self.vault_path = Path(config.get("vault_path", ""))

    def fetch(self) -> List[Dict[str, Any]]:
        if not self.vault_path.is_dir():
            print(f"WARN: Obsidian vault path not found or not a directory: {self.vault_path}")
            return []

        print(f"INFO: Fetching documents from Obsidian vault at {self.vault_path}...")
        documents = []
        for file_path in self.vault_path.rglob("*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                doc_id = str(file_path.relative_to(self.vault_path))
                # Create human-readable file path for searching (convert underscores back to spaces)
                readable_file_path = file_path.name.replace('_', ' ').replace(' - ', ' - ').replace(' (', ' (').replace(') ', ') ')
                documents.append({
                    "source": "obsidian",
                    "id": doc_id,
                    "content": content,
                    "metadata": {
                        "file_path": readable_file_path,  # Use readable name for search
                        "actual_file_path": doc_id,  # Keep actual path for file reading
                        "last_modified": os.path.getmtime(file_path)
                    }
                })
            except Exception as e:
                print(f"ERROR: Failed to read or process file {file_path}: {e}")
        print(f"INFO: Found {len(documents)} documents in Obsidian vault.")
        return documents