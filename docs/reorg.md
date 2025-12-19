This is a significant restructuring. To do this without breaking the application, we must update file paths in the configuration, the Python backend, and the shell scripts immediately after moving the files.

Here is the step-by-step plan and the specific code changes required.

### Phase 1: Directory Structure Setup & File Moves

Run these commands in your terminal to establish the new High-Level (HL) structure.

```bash
# 1. Create new top-level directories
mkdir -p datalake/index
mkdir -p datalake/processed
mkdir -p datalake/documents
mkdir -p scripts/message_decryption
mkdir -p scripts/utils

# 2. Move Documentation to docs/
# (Excluding README.md in root as it's standard convention to keep one there)
mv DISCORD_SETUP.md docs/
mv LICENSE docs/
mv OBSIDIAN_SYNC.md docs/
mv OBSIDIAN_SYNC_DEMO.md docs/
mv README.testing.md docs/
mv repo_src/backend/MCP_CHAT_README.md docs/backend_mcp_chat.md
mv repo_src/backend/MCP_README.md docs/backend_mcp_server.md
mv repo_src/backend/README_backend.md docs/
mv repo_src/frontend/README_frontend.md docs/

# 3. Move Data to datalake/
# Move SQLite DB and Indices
mv repo_src/backend/data/exocortex.db datalake/ 2>/dev/null || true
mv repo_src/backend/data/index/* datalake/index/ 2>/dev/null || true
# Move Processed Data (Notion/Discord exports)
mv repo_src/backend/data/processed/* datalake/processed/ 2>/dev/null || true
# Move Raw Documents (Obsidian Sync target)
mv repo_src/backend/documents/* datalake/documents/ 2>/dev/null || true
# Remove the old data folders (but keep structure if python packages rely on __init__)
rm -rf repo_src/backend/documents
rm -rf repo_src/backend/data/processed
rm -rf repo_src/backend/data/index

# 4. Move Scripts
# Move Message Decryption toolset
mv message_decryption/* scripts/message_decryption/
rm -rf message_decryption

# Move Helper scripts from repo_src/scripts to scripts/utils
mv repo_src/scripts/* scripts/utils/
rm -rf repo_src/scripts

# 5. Clean up openrouter_models.json (Move to utils or backend resource)
mv openrouter_models.json scripts/utils/
```

### Phase 2: Required Code Updates

You must update the following files to point to the new paths.

#### 1. Update `config.yaml`
The application looks here for file paths.

```yaml
# Change these lines in config.yaml
vault_path: "datalake/processed/current" 

data_sources:
  obsidian:
    enabled: true
    vault_path: "datalake/documents" 
```

#### 2. Update Backend Database Connection
**File:** `repo_src/backend/database/connection.py`

```python
from pathlib import Path
import os
# ... imports ...

# UPDATE THIS SECTION
# Get the project root (3 levels up from backend/database/connection.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "datalake"
DATA_DIR.mkdir(exist_ok=True)

DEFAULT_DB_PATH = DATA_DIR / "exocortex.db"
# ... rest of file remains the same ...
```

#### 3. Update File Processing Pipeline
**File:** `repo_src/backend/pipelines/data_processing.py`

```python
# ... imports ...

# UPDATE THESE CONSTANTS
PROJECT_ROOT = Path(__file__).resolve().parents[3] # Adjust based on depth
# OR safer: 
# PROJECT_ROOT = Path(os.getcwd()) # Assuming ran from root
OUTPUT_DIR = PROJECT_ROOT / "datalake" / "processed"

# ... rest of file ...
```

#### 4. Update Index Sync Logic
**File:** `repo_src/backend/functions/index_sync.py`

```python
# ... imports ...

def get_index_file_paths(data_dir: Path) -> Dict[str, Path]:
    # Update to point to datalake/index
    # Note: data_dir passed in might need to be adjusted in the caller
    # ideally, hardcode or config-drive the datalake path
    project_root = Path(__file__).resolve().parents[3]
    index_dir = project_root / "datalake" / "index"
    index_dir.mkdir(exist_ok=True)
    
    return {
        "markdown": index_dir / "knowledge_index.md",
        "json": index_dir / "knowledge_index.json", 
        "csv": index_dir / "knowledge_index.csv",
    }
```

#### 5. Update MCP Server Data Paths
**File:** `repo_src/backend/mcp_server.py`

```python
# ... imports ...

# UPDATE PATHS
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_ROOT = PROJECT_ROOT / "datalake"
PROCESSED_ROOT = DATA_ROOT / "processed" / "current"
INDEX_ROOT = DATA_ROOT / "index"
# ... rest of file ...
```

#### 6. Update Shell Scripts
The scripts moved to `scripts/utils/` need to know where the backend and datalake are now.

**Example: `scripts/utils/setup-env.sh`**
Update the relative paths to `.env` files:
```bash
# Update these paths
FRONTEND_ENV_DIR="repo_src/frontend"
BACKEND_ENV_DIR="repo_src/backend"
```
*(Note: Since this script runs from root, these paths actually stay the same, but you must ensure you execute the script from root as `./scripts/utils/setup-env.sh`)*

**Example: `scripts/utils/sync-obsidian.sh`**
```bash
# Update DOCUMENTS_DIR
DOCUMENTS_DIR="$(dirname "$0")/../../datalake/documents"
```

### Phase 3: Update `package.json`

The root `package.json` contains script shortcuts that will break because `repo_src/scripts` no longer exists. Update the `scripts` section:

```json
{
  "scripts": {
    "ctx:sync": "python scripts/utils/export_context.py",
    "registry:update": "pnpm ctx:sync",
    "chat": "python scripts/utils/chat.py",
    "diagrams:generate": "python scripts/utils/generate_diagrams.py",
    "refresh-docs": "pnpm registry:update && pnpm diagrams:generate",
    "dev": "turbo run dev",
    "dev:frontend": "turbo run dev --filter=@workspace/frontend",
    "dev:backend": "turbo run dev --filter=@workspace/backend",
    "dev:scheduler": "source .venv/bin/activate && python repo_src/backend/scheduler/main.py",
    "build": "turbo run build",
    "lint": "turbo run lint",
    "test": "turbo run test",
    "e2e": "concurrently -k \"pnpm --filter frontend run dev\" \"cd repo_src/backend && source venv/bin/activate && uvicorn main:app --reload\" \"playwright test\"",
    "reset": "./scripts/utils/reset-ports.sh",
    "dev:clean": "pnpm reset && pnpm dev",
    "setup-env": "./scripts/utils/setup-env.sh",
    "setup-project": "pnpm install && python -m venv .venv && . .venv/bin/activate && pip install -r repo_src/backend/requirements.txt && pnpm setup-env",
    "data:combine": "python scripts/utils/combine_sources.py",
    "index:sync": "python -m repo_src.scripts.sync_index", 
    "index:tag": "python -m repo_src.scripts.tag_index",
    "obsidian:sync": "./scripts/utils/sync-obsidian.sh",
    "obsidian:watch": "./scripts/utils/watch-obsidian.sh"
  }
}
```

### Final Directory Layout

```text
/
├── .env
├── .gitignore
├── config.yaml
├── package.json
├── datalake/
│   ├── database/ (exocortex.db)
│   ├── documents/ (raw obsidian files)
│   ├── index/ (json/csv indices)
│   └── processed/ (discord/notion exports)
├── docs/
│   ├── adr/
│   ├── diagrams/
│   ├── guides/
│   ├── pipelines/
│   ├── prd/
│   └── (Moved MD files like DISCORD_SETUP.md)
├── registry/
├── repo_src/
│   ├── backend/
│   │   ├── adapters/
│   │   ├── agents/
│   │   ├── data/ (Only python schemas/__init__.py now)
│   │   ├── database/
│   │   ├── functions/
│   │   ├── routers/
│   │   ├── main.py
│   │   └── ...
│   └── frontend/
└── scripts/
    ├── message_decryption/ (Matrix/Beeper tools)
    └── utils/ (Project maintenance scripts)
```

This structure is much cleaner, separates code from data, and groups all documentation and tooling logically.

