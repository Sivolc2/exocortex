#!/usr/bin/env python3
"""
Physical Index Sync Functions

Pure functions for syncing the database index to a physical file format.
Maintains a human-readable index file alongside the database.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from repo_src.backend.database.models import IndexEntry


def format_index_entry_for_file(entry: IndexEntry) -> Dict[str, Any]:
    """
    Convert a database IndexEntry to a dictionary suitable for file output.
    
    Args:
        entry: IndexEntry model instance
        
    Returns:
        Dictionary with formatted entry data
    """
    return {
        "id": entry.id,
        "file_path": entry.file_path,
        "source": entry.source,
        "description": entry.description or "",
        "tags": entry.tags or "",
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def generate_markdown_index(entries: List[IndexEntry]) -> str:
    """
    Generate a markdown-formatted physical index from database entries.
    
    Args:
        entries: List of IndexEntry instances from database
        
    Returns:
        Markdown-formatted string representing the index
    """
    if not entries:
        return "# Knowledge Index\n\n*No entries found*\n"
    
    # Group by source
    sources = {}
    for entry in entries:
        source = entry.source or "unknown"
        if source not in sources:
            sources[source] = []
        sources[source].append(entry)
    
    # Generate markdown
    lines = [
        "# Knowledge Index",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        f"*Total entries: {len(entries)}*",
        "",
    ]
    
    for source, source_entries in sorted(sources.items()):
        lines.extend([
            f"## {source.title()} ({len(source_entries)} files)",
            "",
        ])
        
        for entry in sorted(source_entries, key=lambda x: x.file_path):
            # File path as header
            lines.append(f"### {entry.file_path}")
            
            # Description if available
            if entry.description and entry.description.strip():
                lines.append(f"**Description:** {entry.description.strip()}")
            
            # Tags if available
            if entry.tags and entry.tags.strip():
                tags_formatted = ", ".join([f"`{tag.strip()}`" for tag in entry.tags.split(",") if tag.strip()])
                lines.append(f"**Tags:** {tags_formatted}")
            
            # Metadata
            if entry.created_at:
                lines.append(f"**Created:** {entry.created_at.strftime('%Y-%m-%d %H:%M')}")
            if entry.updated_at and entry.updated_at != entry.created_at:
                lines.append(f"**Updated:** {entry.updated_at.strftime('%Y-%m-%d %H:%M')}")
                
            lines.append("")  # Empty line between entries
        
        lines.append("")  # Empty line between sources
    
    return "\n".join(lines)


def generate_json_index(entries: List[IndexEntry]) -> str:
    """
    Generate a JSON-formatted physical index from database entries.
    
    Args:
        entries: List of IndexEntry instances from database
        
    Returns:
        JSON-formatted string representing the index
    """
    index_data = {
        "generated_at": datetime.now().isoformat(),
        "total_entries": len(entries),
        "entries": [format_index_entry_for_file(entry) for entry in entries],
        "sources": {}
    }
    
    # Group by source for summary
    for entry in entries:
        source = entry.source or "unknown"
        if source not in index_data["sources"]:
            index_data["sources"][source] = 0
        index_data["sources"][source] += 1
    
    return json.dumps(index_data, indent=2, ensure_ascii=False)


def generate_csv_index(entries: List[IndexEntry]) -> str:
    """
    Generate a CSV-formatted physical index from database entries.
    
    Args:
        entries: List of IndexEntry instances from database
        
    Returns:
        CSV-formatted string representing the index
    """
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "id", "file_path", "source", "description", "tags", "created_at", "updated_at"
    ])
    
    # Data rows
    for entry in sorted(entries, key=lambda x: (x.source or "unknown", x.file_path)):
        writer.writerow([
            entry.id,
            entry.file_path,
            entry.source or "unknown",
            entry.description or "",
            entry.tags or "",
            entry.created_at.isoformat() if entry.created_at else "",
            entry.updated_at.isoformat() if entry.updated_at else "",
        ])
    
    return output.getvalue()


def get_index_file_paths(data_dir: Path) -> Dict[str, Path]:
    """
    Get the file paths where physical indexes should be stored.
    
    Args:
        data_dir: Path to the backend data directory
        
    Returns:
        Dictionary mapping format names to file paths
    """
    index_dir = data_dir / "index"
    index_dir.mkdir(exist_ok=True)
    
    return {
        "markdown": index_dir / "knowledge_index.md",
        "json": index_dir / "knowledge_index.json", 
        "csv": index_dir / "knowledge_index.csv",
    }


def sync_physical_index(entries: List[IndexEntry], data_dir: Path, formats: Optional[List[str]] = None) -> Dict[str, bool]:
    """
    Sync database entries to physical index files.
    
    Args:
        entries: List of IndexEntry instances from database
        data_dir: Path to the backend data directory
        formats: List of formats to generate (default: ["markdown", "json", "csv"])
        
    Returns:
        Dictionary mapping format names to success status
    """
    if formats is None:
        formats = ["markdown", "json", "csv"]
    
    file_paths = get_index_file_paths(data_dir)
    results = {}
    
    # Generate content for each format
    generators = {
        "markdown": generate_markdown_index,
        "json": generate_json_index,
        "csv": generate_csv_index,
    }
    
    for format_name in formats:
        try:
            if format_name not in generators:
                results[format_name] = False
                continue
                
            content = generators[format_name](entries)
            file_path = file_paths[format_name]
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            results[format_name] = True
            
        except Exception as e:
            print(f"Error writing {format_name} index: {e}")
            results[format_name] = False
    
    return results


def validate_physical_index_consistency(entries: List[IndexEntry], data_dir: Path) -> Dict[str, Any]:
    """
    Validate that physical index files are consistent with database entries.
    
    Args:
        entries: List of IndexEntry instances from database
        data_dir: Path to the backend data directory
        
    Returns:
        Dictionary with validation results
    """
    file_paths = get_index_file_paths(data_dir)
    results = {
        "consistent": True,
        "files_exist": {},
        "entry_counts": {},
        "last_modified": {},
        "errors": []
    }
    
    db_count = len(entries)
    
    # Check each format
    for format_name, file_path in file_paths.items():
        try:
            exists = file_path.exists()
            results["files_exist"][format_name] = exists
            
            if not exists:
                results["consistent"] = False
                results["errors"].append(f"{format_name} index file does not exist")
                continue
            
            # Get file modification time
            results["last_modified"][format_name] = datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).isoformat()
            
            # Count entries in file
            if format_name == "json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results["entry_counts"][format_name] = data.get("total_entries", 0)
            elif format_name == "csv":
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    results["entry_counts"][format_name] = sum(1 for _ in reader)
            else:  # markdown
                # Simple count based on file path headers
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    results["entry_counts"][format_name] = content.count("### ")
            
            # Check if count matches database
            file_count = results["entry_counts"][format_name]
            if file_count != db_count:
                results["consistent"] = False
                results["errors"].append(
                    f"{format_name} has {file_count} entries, database has {db_count}"
                )
                
        except Exception as e:
            results["consistent"] = False
            results["errors"].append(f"Error validating {format_name}: {e}")
            results["files_exist"][format_name] = False
            results["entry_counts"][format_name] = 0
    
    return results