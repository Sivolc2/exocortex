from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
from pathlib import Path
import csv
import io
from fastapi.responses import StreamingResponse

from repo_src.backend.database.connection import get_db
from repo_src.backend.database.models import IndexEntry
from repo_src.backend.data import schemas
from repo_src.backend.functions.index_sync import sync_physical_index

router = APIRouter(
    prefix="/api/index",
    tags=["index"],
)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
# Point to the consolidated data from all sources
CONSOLIDATED_DATA_DIR = PROJECT_ROOT / "repo_src" / "backend" / "data" / "processed" / "current"

@router.get("/", response_model=List[schemas.IndexEntryResponse])
def get_all_index_entries(db: Session = Depends(get_db)):
    """
    Retrieve all entries from the structured index.
    """
    return db.query(IndexEntry).order_by(IndexEntry.file_path).all()

@router.put("/{entry_id}", response_model=schemas.IndexEntryResponse)
def update_index_entry(entry_id: int, entry_update: schemas.IndexEntryUpdate, db: Session = Depends(get_db)):
    """
    Update an index entry's description or tags.
    """
    db_entry = db.query(IndexEntry).filter(IndexEntry.id == entry_id).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Index entry not found")
    
    update_data = entry_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_entry, key, value)
    
    db.commit()
    db.refresh(db_entry)
    
    # Sync physical index after update
    try:
        all_entries = db.query(IndexEntry).all()
        data_dir = PROJECT_ROOT / "repo_src" / "backend" / "data"
        sync_physical_index(all_entries, data_dir)
    except Exception as e:
        # Don't fail the request if physical sync fails
        print(f"Warning: Physical index sync failed after update: {e}")
    
    return db_entry

@router.post("/scan", status_code=status.HTTP_201_CREATED)
def scan_and_populate_index(db: Session = Depends(get_db)):
    """
    Scans the consolidated data directory for markdown files from all sources
    and adds any new files to the index with proper source attribution.
    """
    if not CONSOLIDATED_DATA_DIR.exists() or not CONSOLIDATED_DATA_DIR.is_dir():
        raise HTTPException(status_code=404, detail=f"Consolidated data directory not found at {CONSOLIDATED_DATA_DIR}")

    existing_files = {entry.file_path for entry in db.query(IndexEntry.file_path).all()}
    
    found_files = {}  # filepath -> source mapping
    source_dirs = ["obsidian", "notion", "discord", "chat_exports"]
    
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

    # Also update existing files if their source is unknown/outdated
    for file_path in existing_files:
        if file_path in found_files:
            entry = db.query(IndexEntry).filter(IndexEntry.file_path == file_path).first()
            if entry and (not entry.source or entry.source == "unknown"):
                entry.source = found_files[file_path]
                updated_count += 1

    if not new_files and updated_count == 0:
        # Even if no changes, ensure physical index files exist
        try:
            all_entries = db.query(IndexEntry).all()
            data_dir = PROJECT_ROOT / "repo_src" / "backend" / "data"
            file_paths = data_dir / "index"
            # Check if index files exist
            if not (file_paths / "knowledge_index.json").exists():
                sync_physical_index(all_entries, data_dir)
                return {"message": "Index is already up to date. Physical index files created."}
        except Exception as e:
            print(f"Warning: Physical index sync failed: {e}")
        return {"message": "Index is already up to date. No new files found and all sources are current."}

    for file_path in sorted(list(new_files)):
        new_entry = IndexEntry(
            file_path=file_path,
            source=found_files[file_path],
            description="",
            tags=""
        )
        db.add(new_entry)
        added_count += 1
    
    db.commit()
    
    # Sync physical index after bulk changes
    try:
        all_entries = db.query(IndexEntry).all()
        data_dir = PROJECT_ROOT / "repo_src" / "backend" / "data"
        sync_results = sync_physical_index(all_entries, data_dir)
        physical_sync_status = "synced" if all(sync_results.values()) else "partial"
    except Exception as e:
        print(f"Warning: Physical index sync failed after scan: {e}")
        physical_sync_status = "failed"
    
    message = f"Successfully added {added_count} new files to the index"
    if updated_count > 0:
        message += f" and updated source info for {updated_count} existing files"
    message += f". Physical index {physical_sync_status}."
    
    return {"message": message}

@router.get("/export", response_class=StreamingResponse)
def export_index_to_csv(db: Session = Depends(get_db)):
    """
    Exports the current index from the database to a CSV file.
    """
    stream = io.StringIO()
    writer = csv.writer(stream)
    
    # Write header
    writer.writerow(["file_path", "source", "description", "tags"])
    
    entries = db.query(IndexEntry).order_by(IndexEntry.source, IndexEntry.file_path).all()
    for entry in entries:
        writer.writerow([entry.file_path, entry.source, entry.description, entry.tags])
        
    stream.seek(0)
    
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=index_export.csv"
    return response

@router.post("/import", status_code=status.HTTP_200_OK)
async def import_index_from_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Imports index entries from a CSV file, updating existing entries and adding new ones.
    """
    # Check file extension and content type (be more lenient with content type)
    if not (file.filename and file.filename.lower().endswith('.csv')) and file.content_type != "text/csv":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV file.")

    contents = await file.read()
    decoded_content = contents.decode('utf-8')
    stream = io.StringIO(decoded_content)
    reader = csv.DictReader(stream)

    created_count = 0
    updated_count = 0

    for row in reader:
        file_path = row.get("file_path")
        if not file_path:
            continue

        entry = db.query(IndexEntry).filter(IndexEntry.file_path == file_path).first()
        if entry:
            # Update existing entry
            entry.source = row.get("source", entry.source or "unknown")
            entry.description = row.get("description", entry.description)
            entry.tags = row.get("tags", entry.tags)
            updated_count += 1
        else:
            # Create new entry with source fallback
            new_entry_data = {
                "file_path": file_path,
                "source": row.get("source", "unknown"),
                "description": row.get("description", ""),
                "tags": row.get("tags", "")
            }
            new_entry = IndexEntry(**new_entry_data)
            db.add(new_entry)
            created_count += 1

    db.commit()
    
    # Sync physical index after import
    try:
        all_entries = db.query(IndexEntry).all()
        data_dir = PROJECT_ROOT / "repo_src" / "backend" / "data"
        sync_results = sync_physical_index(all_entries, data_dir)
        physical_sync_status = "synced" if all(sync_results.values()) else "partial"
    except Exception as e:
        print(f"Warning: Physical index sync failed after import: {e}")
        physical_sync_status = "failed"
    
    return {"message": f"Import complete. Updated: {updated_count}, Created: {created_count}. Physical index {physical_sync_status}."} 