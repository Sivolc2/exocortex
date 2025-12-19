#!/usr/bin/env python3
"""
Physical Index Sync Script

Syncs the database index to physical files in the data directory.
Creates markdown, JSON, and CSV versions of the index.

Usage:
    python -m repo_src.scripts.sync_physical_index [--formats markdown,json,csv] [--validate]
"""

import sys
import argparse
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from repo_src.backend.database.connection import get_db
from repo_src.backend.database.models import IndexEntry
from repo_src.backend.functions.index_sync import (
    sync_physical_index, 
    validate_physical_index_consistency,
    get_index_file_paths
)


def main():
    """Main script entry point."""
    parser = argparse.ArgumentParser(
        description="Sync database index to physical files"
    )
    parser.add_argument(
        "--formats",
        default="markdown,json,csv",
        help="Comma-separated list of formats to sync (default: markdown,json,csv)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate physical index consistency instead of syncing"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output"
    )
    
    args = parser.parse_args()
    
    if not args.quiet:
        print("=== Physical Index Sync ===")
    
    # Get database session
    db = next(get_db())
    data_dir = PROJECT_ROOT / "repo_src" / "backend" / "data"
    
    try:
        # Get all entries from database
        all_entries = db.query(IndexEntry).all()
        
        if args.validate:
            # Validation mode
            if not args.quiet:
                print("Validating physical index consistency...")
            
            validation_results = validate_physical_index_consistency(all_entries, data_dir)
            
            if validation_results["consistent"]:
                print("✅ Physical index is consistent with database")
                if not args.quiet:
                    for format_name, count in validation_results["entry_counts"].items():
                        print(f"  {format_name}: {count} entries")
            else:
                print("❌ Physical index inconsistencies found:")
                for error in validation_results["errors"]:
                    print(f"  - {error}")
                return False
            
        else:
            # Sync mode
            formats = [f.strip() for f in args.formats.split(",")]
            
            if not args.quiet:
                print(f"Syncing {len(all_entries)} entries to physical index...")
                print(f"Formats: {', '.join(formats)}")
            
            sync_results = sync_physical_index(all_entries, data_dir, formats)
            
            # Report results
            success_count = sum(1 for success in sync_results.values() if success)
            total_count = len(sync_results)
            
            if not args.quiet:
                print(f"\n=== Sync Results ===")
                file_paths = get_index_file_paths(data_dir)
                for format_name, success in sync_results.items():
                    status = "✅" if success else "❌"
                    file_path = file_paths.get(format_name, "unknown")
                    print(f"{status} {format_name.title()}: {file_path}")
            
            if success_count == total_count:
                if not args.quiet:
                    print(f"✅ All {total_count} formats synced successfully")
                return True
            else:
                if not args.quiet:
                    print(f"⚠️  {success_count}/{total_count} formats synced successfully")
                return False
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)