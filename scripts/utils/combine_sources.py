import yaml
from pathlib import Path
from datetime import datetime
import sys

# --- Configuration ---

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH = PROJECT_ROOT / "config.yaml"

from repo_src.backend.pipelines.data_processing import run_source_fetch_pipeline

# --- Main Execution ---

def main():
    """
    Manual script to fetch and combine data from all enabled sources.
    This script now calls the centralized data processing pipeline for each source.
    """
    print("--- Starting Manual Data Combination Process ---")
    print("NOTE: This script fetches all enabled sources. For automated, scheduled fetching, run 'pnpm dev:scheduler'.")

    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        data_sources_config = config.get("data_sources", {})
        sync_options = config.get("sync_options", {})
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: Failed to load configuration. {e}")
        return

    for source_name, source_config in data_sources_config.items():
        if source_config.get("enabled"):
            try:
                run_source_fetch_pipeline(source_name, sync_options)
            except Exception as e:
                print(f"ERROR: A critical error occurred while processing {source_name}: {e}")

    print("\n--- Manual Data Combination Process Complete ---")

if __name__ == "__main__":
    main()