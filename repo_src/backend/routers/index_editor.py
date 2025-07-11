from fastapi import APIRouter, HTTPException
from pathlib import Path

from repo_src.backend.data.schemas import IndexContent

router = APIRouter(
    prefix="/api/index",
    tags=["index"],
)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
DOCUMENTS_DIR = PROJECT_ROOT / "repo_src" / "backend" / "documents"
INDEX_FILE_PATH = DOCUMENTS_DIR / "_index.md"
DEFAULT_INDEX_CONTENT = """# Project Index

This is a manually curated index of important files and topics.
Use it to provide high-level guidance to the file-selection LLM.

## Key Topics

- **Project Overview**: See `README.md` for the main goals.
- **Obsidian Sync**: The logic for syncing notes is in `OBSIDIAN_SYNC.md` and the scripts are in `repo_src/scripts/sync-obsidian-*.sh`.
- **Backend Chat Logic**: The core agent logic is in `repo_src/backend/agents/file_selection_agent.py`.
"""

@router.get("/", response_model=IndexContent)
async def get_index_content():
    if not INDEX_FILE_PATH.exists():
        # Create it with default content if it doesn't exist
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        INDEX_FILE_PATH.write_text(DEFAULT_INDEX_CONTENT, 'utf-8')
        return IndexContent(content=DEFAULT_INDEX_CONTENT)
    
    content = INDEX_FILE_PATH.read_text('utf-8')
    return IndexContent(content=content)

@router.post("/")
async def save_index_content(payload: IndexContent):
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE_PATH.write_text(payload.content, 'utf-8')
    return {"message": "Index saved successfully."} 