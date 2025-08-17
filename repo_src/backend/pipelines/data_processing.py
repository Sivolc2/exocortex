import os
import sys
import json
import yaml
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import importlib
from dotenv import load_dotenv

# --- Configuration ---

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH = PROJECT_ROOT / "config.yaml"
OUTPUT_DIR = PROJECT_ROOT / "repo_src" / "backend" / "data" / "processed"

# --- Helper Functions ---

def _get_fetcher_class(source_name: str):
    """Dynamically imports and returns the fetcher class for a given source."""
    try:
        module_name = f"repo_src.backend.data_sources.fetch_{source_name}"
        class_name = f"{source_name.capitalize()}Fetcher"
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        print(f"ERROR: Could not find fetcher for source '{source_name}'. Details: {e}")
        return None

def _get_content_hash(content: str) -> str:
    """Generate a hash of the content for change detection."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def _should_update_file(filepath: Path, content: str) -> bool:
    """Check if file should be updated based on content changes."""
    if not filepath.exists():
        return True
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        if existing_content.startswith('---\n'):
            parts = existing_content.split('---\n', 2)
            if len(parts) >= 3:
                existing_content = parts[2]
        return _get_content_hash(content) != _get_content_hash(existing_content)
    except Exception as e:
        print(f"    WARNING: Could not read existing file {filepath}: {e}")
        return True

def _get_date_chunk(date_str: str, chunk_days: int) -> str:
    """Get the chunk identifier for a given date based on chunk_days."""
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    if chunk_days == 1:
        return date_str
    epoch = datetime(1970, 1, 1)
    days_since_epoch = (date_obj - epoch).days
    chunk_start_days = (days_since_epoch // chunk_days) * chunk_days
    chunk_start = epoch + timedelta(days=chunk_start_days)
    chunk_end = chunk_start + timedelta(days=chunk_days - 1)
    return f"{chunk_start.strftime('%Y-%m-%d')}_to_{chunk_end.strftime('%Y-%m-%d')}"

def _write_discord_files(discord_items: list, output_folder: Path, chunk_days: int = 1):
    """Write Discord items to files organized by channel and chunked by date."""
    from collections import defaultdict
    channel_chunk_groups = defaultdict(lambda: defaultdict(list))

    for item in discord_items:
        channel_name = item.get('metadata', {}).get('channel_name', 'unknown')
        content = item['content']
        date_sections = re.split(r'\n## (\d{4}-\d{2}-\d{2})\n', content)

        if len(date_sections) > 1:
            for i in range(1, len(date_sections), 2):
                if i + 1 < len(date_sections):
                    date_str = date_sections[i]
                    messages_content = date_sections[i+1]
                    chunk_id = _get_date_chunk(date_str, chunk_days)
                    daily_doc = {
                        'date': date_str,
                        'chunk_id': chunk_id,
                        'content': f"## {date_str}\n\n{messages_content.strip()}"
                    }
                    channel_chunk_groups[channel_name][chunk_id].append(daily_doc)

    for channel_name, chunk_groups in channel_chunk_groups.items():
        channel_folder = output_folder / channel_name
        channel_folder.mkdir(exist_ok=True)
        for chunk_id, docs in chunk_groups.items():
            docs.sort(key=lambda x: x['date'])
            if chunk_days == 1:
                title = f"# {channel_name} - {docs[0]['date']}"
            else:
                dates = sorted(set(doc['date'] for doc in docs))
                date_range = f"{dates[0]} to {dates[-1]}" if len(dates) > 1 else dates[0]
                title = f"# {channel_name} - {date_range}"

            combined_content = f"{title}\n\n" + "\n\n".join(doc['content'] for doc in docs)
            filename = f"{chunk_id}.md"
            filepath = channel_folder / filename

            if _should_update_file(filepath, combined_content.strip()):
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(combined_content.strip())
                print(f"    Updated: {channel_name}/{filename}")

def _write_source_files(items: list, output_folder: Path, source_name: str):
    """Write non-Discord source items to individual files."""
    for item in items:
        item_id = item.get('id', f'item_{hashlib.md5(item["content"].encode()).hexdigest()[:8]}')
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', str(item_id)).replace(' ', '_')[:100]
        filename = f"{safe_filename}.md" if not safe_filename.endswith('.md') else safe_filename
        filepath = output_folder / filename

        full_content = "---\n"
        full_content += f"source: {source_name}\n"
        full_content += f"id: {item['id']}\n"
        if item.get('metadata'):
            for key, value in item['metadata'].items():
                value_str = str(value).replace('"', '\\"')
                full_content += f'{key}: "{value_str}"\n' if any(c in str(value) for c in [':', '"', "'"]) else f"{key}: {value}\n"
        full_content += "---\n\n"
        full_content += item['content']

        if _should_update_file(filepath, item['content']):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_content)
            print(f"    Updated: {filename}")

def run_source_fetch_pipeline(source_name: str, sync_options: dict):
    """
    Orchestrates the data fetching and processing for a single data source.
    """
    print(f"\n>>> Processing source: {source_name}")
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        source_config = config.get("data_sources", {}).get(source_name)
        if not source_config or not source_config.get("enabled"):
            print(f"... Skipping {source_name}: not enabled or configured.")
            return
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: Failed to load configuration for {source_name}. {e}")
        return

    FetcherClass = _get_fetcher_class(source_name)
    if not FetcherClass:
        return

    try:
        fetcher = FetcherClass(source_config)
        fetched_data = fetcher.fetch()
        if not fetched_data:
            print(f"--- No new data fetched from {source_name}")
            return
        print(f"--- Fetched {len(fetched_data)} items from {source_name}")
    except Exception as e:
        print(f"ERROR: An error occurred while fetching data from {source_name}: {e}")
        return

    # Determine output directory (always 'current' for incremental updates)
    run_folder = OUTPUT_DIR / "current"
    run_folder.mkdir(parents=True, exist_ok=True)

    source_folder = run_folder / source_name
    source_folder.mkdir(exist_ok=True)

    print(f"  Writing data for {source_name} to {source_folder}...")
    if source_name == "discord":
        chunk_days = source_config.get("chunk_days", 1)
        _write_discord_files(fetched_data, source_folder, chunk_days)
    else:
        _write_source_files(fetched_data, source_folder, source_name)

    # After processing, sync the index
    try:
        from repo_src.scripts.sync_index import sync_index
        print(f"\n--- Syncing index after {source_name} update ---")
        sync_index()
    except Exception as e:
        print(f"ERROR: Failed to sync index after fetching {source_name}: {e}")

    print(f">>> Finished processing {source_name}")