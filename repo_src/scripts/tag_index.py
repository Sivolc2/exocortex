#!/usr/bin/env python3
"""
Index LLM Tagging Script

Uses LLM calls to generate descriptions and tags for files in the index.
Processes files that don't have descriptions/tags or have empty ones.

Usage:
    python -m repo_src.scripts.tag_index [--limit N] [--force] [--source SOURCE]
    
Options:
    --limit N       Process at most N files (default: unlimited)
    --force         Reprocess files that already have descriptions/tags
    --source SOURCE Only process files from specific source (obsidian, notion, discord)
"""

import sys
import os
import argparse
import requests
import json
from pathlib import Path
from time import sleep
from typing import Optional

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from repo_src.backend.database.connection import get_db
from repo_src.backend.database.models import IndexEntry
from repo_src.backend.functions.index_sync import sync_physical_index
from dotenv import load_dotenv

# Load environment variables
load_dotenv(PROJECT_ROOT / "repo_src" / "backend" / ".env")

def get_file_content(file_path: str) -> Optional[str]:
    """Read the content of a file."""
    try:
        CONSOLIDATED_DATA_DIR = PROJECT_ROOT / "repo_src" / "backend" / "data" / "processed" / "current"
        full_path = CONSOLIDATED_DATA_DIR / file_path
        
        if not full_path.exists():
            print(f"  WARNING: File not found: {full_path}")
            return None
            
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Skip frontmatter if present
        if content.startswith('---\n'):
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                content = parts[2]  # Content after frontmatter
        
        # Truncate very long files
        if len(content) > 8000:
            content = content[:8000] + "\n\n[Content truncated...]"
            
        return content
        
    except Exception as e:
        print(f"  ERROR: Could not read file {file_path}: {e}")
        return None

def call_llm(content: str, file_path: str) -> tuple[Optional[str], Optional[str]]:
    """
    Call LLM to generate description and tags for file content.
    Returns (description, tags) tuple.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in environment variables")
        return None, None
    
    # Determine file context based on source
    source_context = ""
    if "discord/" in file_path:
        source_context = "This is a Discord chat log file containing conversations from a specific channel and date."
    elif "notion/" in file_path:
        source_context = "This is a Notion page exported as markdown, containing structured notes or documentation."
    elif "obsidian/" in file_path:
        source_context = "This is an Obsidian vault note, containing personal notes, thoughts, or documentation."
    else:
        source_context = "This is a markdown file containing notes or documentation."
    
    prompt = f"""You are helping to organize and index a knowledge base. {source_context}

Please analyze the following content and provide:
1. A concise description (1-2 sentences) summarizing what this file contains
2. Relevant tags (3-5 keywords) that would help categorize and find this content

File: {file_path}

Content:
{content}

Please respond in this exact JSON format:
{{
    "description": "Brief description of the file contents",
    "tags": "tag1, tag2, tag3, tag4"
}}"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "anthropic/claude-3-5-sonnet-20241022",  # Good balance of speed and quality
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.1
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"  ERROR: API call failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return None, None
        
        result = response.json()
        if "choices" not in result or len(result["choices"]) == 0:
            print(f"  ERROR: No choices in API response: {result}")
            return None, None
            
        content = result["choices"][0]["message"]["content"]
        
        # Try to parse JSON response
        try:
            parsed = json.loads(content)
            description = parsed.get("description", "").strip()
            tags = parsed.get("tags", "").strip()
            return description, tags
        except json.JSONDecodeError:
            # Fallback: try to extract from text
            lines = content.split('\n')
            description = ""
            tags = ""
            
            for line in lines:
                if '"description"' in line and ':' in line:
                    description = line.split(':', 1)[1].strip(' ",')
                elif '"tags"' in line and ':' in line:
                    tags = line.split(':', 1)[1].strip(' ",')
            
            return description or None, tags or None
            
    except requests.exceptions.Timeout:
        print(f"  ERROR: API call timed out")
        return None, None
    except Exception as e:
        print(f"  ERROR: API call failed: {e}")
        return None, None

def tag_index(limit: Optional[int] = None, force: bool = False, source_filter: Optional[str] = None):
    """
    Tag files in the index using LLM calls.
    """
    print("=== Index LLM Tagging Script ===")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Build query for files that need tagging
        query = db.query(IndexEntry)
        
        if source_filter:
            query = query.filter(IndexEntry.source == source_filter)
            print(f"Filtering by source: {source_filter}")
        
        if not force:
            # Only process files without descriptions or tags
            query = query.filter(
                (IndexEntry.description == None) | 
                (IndexEntry.description == "") |
                (IndexEntry.tags == None) | 
                (IndexEntry.tags == "")
            )
            print("Processing files without descriptions or tags")
        else:
            print("Force mode: reprocessing all files")
        
        if limit:
            query = query.limit(limit)
            print(f"Limiting to {limit} files")
        
        entries = query.all()
        
        if not entries:
            print("✅ No files need tagging")
            return True
        
        print(f"Found {len(entries)} files to process")
        
        processed = 0
        updated = 0
        errors = 0
        
        for i, entry in enumerate(entries):
            print(f"\nProcessing [{i+1}/{len(entries)}]: {entry.file_path}")
            
            # Read file content
            content = get_file_content(entry.file_path)
            if not content:
                errors += 1
                continue
                
            if len(content.strip()) < 10:
                print(f"  SKIP: File too short or empty")
                continue
            
            # Call LLM
            description, tags = call_llm(content, entry.file_path)
            
            if description and tags:
                entry.description = description
                entry.tags = tags
                updated += 1
                print(f"  ✅ Description: {description}")
                print(f"  ✅ Tags: {tags}")
            else:
                errors += 1
                print(f"  ❌ Failed to generate description/tags")
            
            processed += 1
            
            # Rate limiting: small delay between calls
            if i < len(entries) - 1:  # Don't sleep after last item
                sleep(0.5)
            
            # Commit periodically to save progress
            if processed % 10 == 0:
                db.commit()
                print(f"  💾 Saved progress ({processed} processed)")
        
        # Final commit
        db.commit()
        
        print(f"\n=== Tagging Complete ===")
        print(f"✅ Processed: {processed} files")
        print(f"✅ Updated: {updated} files")
        print(f"❌ Errors: {errors} files")
        
        # Sync physical index after tagging
        if updated > 0:
            print(f"\n=== Syncing Physical Index ===")
            try:
                all_entries = db.query(IndexEntry).all()
                data_dir = PROJECT_ROOT / "repo_src" / "backend" / "data"
                sync_results = sync_physical_index(all_entries, data_dir)
                
                for format_name, success in sync_results.items():
                    status = "✅" if success else "❌"
                    print(f"{status} {format_name.title()} index: {'synced' if success else 'failed'}")
                
                if all(sync_results.values()):
                    print("✅ All physical index files synced successfully")
                else:
                    print("⚠️  Some physical index files failed to sync")
                    
            except Exception as e:
                print(f"⚠️  Warning: Physical index sync failed: {e}")
        
        return errors == 0
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrupted by user")
        db.commit()  # Save any progress
        return False
        
    except Exception as e:
        print(f"ERROR: Failed to tag index: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Tag index files with LLM-generated descriptions and tags")
    parser.add_argument("--limit", type=int, help="Process at most N files")
    parser.add_argument("--force", action="store_true", help="Reprocess files that already have descriptions/tags")
    parser.add_argument("--source", choices=["obsidian", "notion", "discord"], help="Only process files from specific source")
    
    args = parser.parse_args()
    
    success = tag_index(
        limit=args.limit,
        force=args.force,
        source_filter=args.source
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()