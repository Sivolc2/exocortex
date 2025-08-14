import os
import sys
import json
import yaml
import re
import hashlib
from pathlib import Path
from datetime import datetime
import importlib
from dotenv import load_dotenv

# --- Configuration ---

# Set the project root and load environment variables from the backend .env file
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_PATH = PROJECT_ROOT / "repo_src" / "backend" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Add project root to Python path for imports
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH = PROJECT_ROOT / "config.yaml"
SOURCES_DIR = PROJECT_ROOT / "repo_src" / "backend" / "data_sources"
OUTPUT_DIR = PROJECT_ROOT / "repo_src" / "backend" / "data" / "processed"

# --- Helper Functions ---

def load_config() -> tuple:
    """Loads the main YAML configuration file."""
    print(f"Loading configuration from {CONFIG_PATH}...")
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    if "data_sources" not in config:
        raise ValueError("Configuration file must contain a 'data_sources' key.")
    
    # Load sync options with defaults
    sync_options = config.get("sync_options", {})
    sync_defaults = {
        "mode": "incremental",
        "backup_on_sync": True,
        "skip_unchanged": True
    }
    sync_options = {**sync_defaults, **sync_options}
    
    return config["data_sources"], sync_options

def get_fetcher_class(source_name: str):
    """Dynamically imports and returns the fetcher class for a given source."""
    try:
        module_name = f"repo_src.backend.data_sources.fetch_{source_name}"
        class_name = f"{source_name.capitalize()}Fetcher"
        
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        print(f"ERROR: Could not find fetcher for source '{source_name}'. "
              f"Ensure 'repo_src/backend/data_sources/fetch_{source_name}.py' exists "
              f"and contains a class named '{class_name}'.\\nDetails: {e}")
        return None

def get_content_hash(content: str) -> str:
    """Generate a hash of the content for change detection."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def should_update_file(filepath: Path, content: str) -> bool:
    """Check if file should be updated based on content changes."""
    if not filepath.exists():
        return True  # File doesn't exist, should create
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        # Extract content after frontmatter for comparison
        if existing_content.startswith('---\n'):
            parts = existing_content.split('---\n', 2)
            if len(parts) >= 3:
                existing_content = parts[2]  # Content after frontmatter
        
        # Compare hashes to detect changes
        current_hash = get_content_hash(content)
        existing_hash = get_content_hash(existing_content)
        
        return current_hash != existing_hash
        
    except Exception as e:
        print(f"    WARNING: Could not read existing file {filepath}: {e}")
        return True  # If we can't read, assume we should update

def write_discord_files(discord_items: list, output_folder: Path):
    """Write Discord items to daily files organized by channel."""
    from collections import defaultdict
    import re
    
    # Group messages by channel and date
    channel_date_groups = defaultdict(lambda: defaultdict(list))
    
    for item in discord_items:
        # Extract channel info from metadata
        channel_name = item.get('metadata', {}).get('channel_name', 'unknown')
        channel_id = item.get('metadata', {}).get('channel_id', 'unknown')
        
        # Parse the content to extract individual messages by date
        content = item['content']
        
        # Split content by date headers (## YYYY-MM-DD)
        date_sections = re.split(r'\n## (\d{4}-\d{2}-\d{2})\n', content)
        
        if len(date_sections) > 1:
            # Process each date section
            for i in range(1, len(date_sections), 2):
                if i + 1 < len(date_sections):
                    date_str = date_sections[i]
                    messages_content = date_sections[i + 1]
                    
                    # Create a document for this channel-date combination
                    daily_doc = {
                        'channel_name': channel_name,
                        'channel_id': channel_id,
                        'date': date_str,
                        'content': f"# {channel_name} - {date_str}\n\n{messages_content.strip()}"
                    }
                    channel_date_groups[channel_name][date_str].append(daily_doc)
        else:
            # Fallback: use the fetched_at date if no date sections found
            fetched_date = item.get('metadata', {}).get('fetched_at', '')
            if fetched_date:
                date_str = fetched_date[:10]  # Extract YYYY-MM-DD
            else:
                date_str = datetime.now().strftime('%Y-%m-%d')
            
            daily_doc = {
                'channel_name': channel_name,
                'channel_id': channel_id,
                'date': date_str,
                'content': content
            }
            channel_date_groups[channel_name][date_str].append(daily_doc)
    
    # Write files for each channel-date combination
    for channel_name, date_groups in channel_date_groups.items():
        channel_folder = output_folder / channel_name
        channel_folder.mkdir(exist_ok=True)
        
        for date_str, docs in date_groups.items():
            # Combine all documents for this date
            combined_content = ""
            for doc in docs:
                combined_content += doc['content'] + "\n\n"
            
            filename = f"{date_str}.md"
            filepath = channel_folder / filename
            
            # Only write if content has changed
            if should_update_file(filepath, combined_content.strip()):
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(combined_content.strip())
                print(f"    Updated: {channel_name}/{filename}")
            else:
                print(f"    Unchanged: {channel_name}/{filename}")

def write_source_files(items: list, output_folder: Path, source_name: str):
    """Write non-Discord source items to individual files."""
    for i, item in enumerate(items):
        # Create a safe filename from the item ID
        item_id = item.get('id', f'item_{i}')
        # Clean filename (remove invalid characters)
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', str(item_id))
        safe_filename = safe_filename.replace(' ', '_')[:100]  # Limit length
        
        filename = f"{safe_filename}.md"
        filepath = output_folder / filename
        
        # Prepare full content with frontmatter
        full_content = "---\n"
        full_content += f"source: {source_name}\n"
        full_content += f"id: {item['id']}\n"
        
        if item.get('metadata'):
            for key, value in item['metadata'].items():
                # Escape special characters in YAML values
                if isinstance(value, str) and any(c in value for c in [':', '"', "'"]):
                    full_content += f"{key}: \"{str(value).replace('\"', '\\\"')}\"\n"
                else:
                    full_content += f"{key}: {value}\n"
        
        full_content += "---\n\n"
        full_content += item['content']
        
        # Only write if content has changed
        if should_update_file(filepath, item['content']):  # Compare just content, not frontmatter
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_content)
            
            if i < 5:  # Only show first 5 filenames to avoid spam
                print(f"    Updated: {filename}")
        else:
            if i < 5:
                print(f"    Unchanged: {filename}")
    
    # Summary
    updated_count = sum(1 for item in items if should_update_file(output_folder / f"{re.sub(r'[<>:\"/\\\\|?*]', '_', str(item.get('id', 'item')))[:100]}.md", item['content']))
    unchanged_count = len(items) - updated_count
    
    if len(items) > 5:
        print(f"    Summary: {updated_count} updated, {unchanged_count} unchanged")

# --- Main Execution ---

def main():
    """
    Orchestrates the data fetching and combination process.
    1. Loads configuration.
    2. Iterates through enabled data sources.
    3. Initializes and runs the corresponding fetcher for each source.
    4. Combines all fetched data.
    5. Saves the result using incremental or full sync as configured.
    """
    print("--- Starting Data Combination Process ---")
    
    try:
        data_sources_config, sync_options = load_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: Failed to load configuration. {e}")
        return
    
    print(f"Sync mode: {sync_options['mode']}")

    all_data = []
    source_data_by_source = {}
    
    for source_name, source_config in data_sources_config.items():
        if source_config.get("enabled"):
            print(f"\\n>>> Processing enabled source: {source_name}")
            FetcherClass = get_fetcher_class(source_name)
            if FetcherClass:
                try:
                    fetcher = FetcherClass(source_config)
                    source_data = fetcher.fetch()
                    all_data.extend(source_data)
                    source_data_by_source[source_name] = source_data
                    print(f"--- Fetched {len(source_data)} items from {source_name}")
                except Exception as e:
                    print(f"ERROR: An error occurred while fetching data from {source_name}: {e}")
        else:
            print(f"\\n... Skipping disabled source: {source_name}")

    # Ensure the output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Choose folder based on sync mode
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if sync_options['mode'] == "incremental":
        # Use persistent folder for incremental syncing
        run_folder = OUTPUT_DIR / "current"
        run_folder.mkdir(exist_ok=True)
        
        # Create backup if requested
        if sync_options['backup_on_sync'] and (OUTPUT_DIR / "current").exists():
            backup_folder = OUTPUT_DIR / f"backup_{timestamp}"
            import shutil
            try:
                shutil.copytree(OUTPUT_DIR / "current", backup_folder)
                print(f"Created backup: {backup_folder}")
            except Exception as e:
                print(f"WARNING: Could not create backup: {e}")
        
        print(f"\\n>>> Performing incremental sync in {run_folder}...")
        
    else:  # full_overwrite mode
        run_folder = OUTPUT_DIR / f"data_export_{timestamp}"
        run_folder.mkdir(exist_ok=True)
        print(f"\\n>>> Creating full export in {run_folder}...")

    # Create a README for the export
    readme_path = run_folder / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"# Data Export - {timestamp}\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total items: {len(all_data)}\n\n")
        f.write("## Contents\n\n")
        
        for source_name, items in source_data_by_source.items():
            f.write(f"### {source_name.title()}\n")
            f.write(f"- Items: {len(items)}\n")
            f.write(f"- Location: `./{source_name}/`\n\n")

    # Write each source to its own folder/files
    for source_name, items in source_data_by_source.items():
        source_folder = run_folder / source_name
        source_folder.mkdir(exist_ok=True)
        
        print(f"  Processing {len(items)} items from {source_name}...")
        
        if source_name == "discord":
            # Special handling for Discord: chunk by date and channel
            write_discord_files(items, source_folder)
        else:
            # For other sources (Obsidian, Notion): write each item as separate file
            write_source_files(items, source_folder, source_name)

    print("\\n--- Data Combination Process Complete ---")

if __name__ == "__main__":
    main()