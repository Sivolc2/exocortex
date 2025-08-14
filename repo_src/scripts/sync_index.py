#!/usr/bin/env python3
"""
Index Sync Script

Syncs the file index by scanning for new files and adding them to the database.
This script only adds new entries - it does not generate descriptions or tags.

Usage:
    python -m repo_src.scripts.sync_index
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from repo_src.backend.database.connection import get_db
from repo_src.backend.database.models import IndexEntry
from sqlalchemy import func

def sync_index():
    """
    Scan the consolidated data directory and add new files to the index.
    """
    print("=== Index Sync Script ===")
    
    # Point to the consolidated data from all sources
    CONSOLIDATED_DATA_DIR = PROJECT_ROOT / "repo_src" / "backend" / "data" / "processed" / "current"
    
    if not CONSOLIDATED_DATA_DIR.exists():
        print(f"ERROR: Consolidated data directory not found at {CONSOLIDATED_DATA_DIR}")
        return False
    
    # Get database session
    db = next(get_db())
    
    try:
        existing_files = {entry.file_path for entry in db.query(IndexEntry.file_path).all()}
        
        found_files = {}  # filepath -> source mapping
        source_dirs = ["obsidian", "notion", "discord"]
        
        print(f"Scanning {CONSOLIDATED_DATA_DIR}...")
        
        for source in source_dirs:
            source_dir = CONSOLIDATED_DATA_DIR / source
            if source_dir.exists() and source_dir.is_dir():
                for root, _, files in os.walk(source_dir):
                    for file in files:
                        if file.endswith(".md"):
                            # Get path relative to CONSOLIDATED_DATA_DIR
                            full_path = Path(root) / file
                            relative_path = str(full_path.relative_to(CONSOLIDATED_DATA_DIR))
                            found_files[relative_path] = source
        
        new_files = set(found_files.keys()) - existing_files
        added_count = 0
        updated_count = 0
        
        print(f"Found {len(found_files)} total files, {len(existing_files)} already indexed")
        
        # Update existing files if their source is unknown/outdated
        for file_path in existing_files:
            if file_path in found_files:
                entry = db.query(IndexEntry).filter(IndexEntry.file_path == file_path).first()
                if entry and (not entry.source or entry.source == "unknown"):
                    entry.source = found_files[file_path]
                    updated_count += 1
        
        if not new_files and updated_count == 0:
            print("✅ Index is up to date - no new files found and all sources are current")
            return True
        
        # Add new files
        if new_files:
            print(f"Adding {len(new_files)} new files...")
            
            for file_path in sorted(list(new_files)):
                new_entry = IndexEntry(
                    file_path=file_path,
                    source=found_files[file_path],
                    description="",  # Will be filled by LLM tagging script
                    tags=""         # Will be filled by LLM tagging script
                )
                db.add(new_entry)
                added_count += 1
        
        db.commit()
        
        # Print summary
        print(f"\n=== Sync Complete ===")
        print(f"✅ Added {added_count} new files")
        if updated_count > 0:
            print(f"✅ Updated source info for {updated_count} existing files")
        
        # Show final counts
        sources = db.query(IndexEntry.source, func.count(IndexEntry.id)).group_by(IndexEntry.source).all()
        print(f"\nFinal index stats:")
        total = 0
        for source, count in sorted(sources):
            print(f"  {source}: {count} files")
            total += count
        print(f"  Total: {total} files")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to sync index: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    success = sync_index()
    sys.exit(0 if success else 1)