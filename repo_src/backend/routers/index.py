from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import os
from pathlib import Path

from repo_src.backend.database.connection import get_db
from repo_src.backend.database.models import IndexEntry
from repo_src.backend.data import schemas

router = APIRouter(
    prefix="/api/index",
    tags=["index"],
)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
DOCUMENTS_DIR = PROJECT_ROOT / "repo_src" / "backend" / "documents"

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
    return db_entry

@router.post("/scan", status_code=status.HTTP_201_CREATED)
def scan_and_populate_index(db: Session = Depends(get_db)):
    """
    Scans the documents directory for markdown files and adds any new
    files to the index.
    """
    if not DOCUMENTS_DIR.exists() or not DOCUMENTS_DIR.is_dir():
        raise HTTPException(status_code=404, detail=f"Documents directory not found at {DOCUMENTS_DIR}")

    existing_files = {entry.file_path for entry in db.query(IndexEntry.file_path).all()}
    
    found_files = set()
    for root, _, files in os.walk(DOCUMENTS_DIR):
        for file in files:
            if file.endswith(".md"):
                # Get path relative to DOCUMENTS_DIR
                full_path = Path(root) / file
                relative_path = str(full_path.relative_to(DOCUMENTS_DIR))
                found_files.add(relative_path)

    new_files = found_files - existing_files
    added_count = 0

    if not new_files:
        return {"message": "Index is already up to date. No new files found."}

    for file_path in sorted(list(new_files)):
        new_entry = IndexEntry(
            file_path=file_path,
            description="",
            tags=""
        )
        db.add(new_entry)
        added_count += 1
    
    db.commit()
    return {"message": f"Successfully added {added_count} new files to the index."} 