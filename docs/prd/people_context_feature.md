# PRD: People Context Management System

**Project:** Exocortex - People Context Integration
**Version:** 1.0
**Date:** 2025-11-24
**Status:** Proposal - Awaiting Review
**Author:** Architecture Planning Agent

---

## Executive Summary

This PRD outlines the implementation of a **People Context Management System** for the Exocortex knowledge base platform. The system will enable users to maintain a persistent dossier of individuals they encounter, augmented by external sources, and make this contextual information available across all chat interactions.

The feature consists of four major components:
1. **Database Layer** - Already implemented `Person` model with CRUD API
2. **MCP Tool Integration** - Model-accessible tools for querying and updating people records
3. **Frontend UI** - Dedicated "People" view for managing entries via natural language
4. **Context Integration** - Automatic injection of relevant people context into chat responses

---

## 1. Goals and Objectives

### Primary Goals
- **Context Persistence**: Store structured and unstructured information about people across application restarts
- **Natural Language Interface**: Allow users to add/update people entries by pasting free-form text that gets parsed by LLM
- **Universal Context Access**: Make people context available in all chat windows (repository chat, knowledge chat)
- **Zero-Friction Capture**: Minimize user effort to capture and maintain people information

### Success Metrics
- Users can create/update person entries in < 30 seconds
- 90%+ accuracy in LLM parsing of pasted text into structured fields
- People context appears in relevant chat responses automatically
- Database persists indefinitely between restarts

### Non-Goals (Out of Scope for V1)
- Social graph visualization
- Automatic extraction of people from existing knowledge base
- Integration with external contact management systems (LinkedIn, contacts)
- Real-time collaboration on people records
- Advanced search/filtering in UI (basic search only)

---

## 2. Current State Analysis

### Existing Infrastructure

#### Database Layer ✓ (COMPLETE)
- `Person` model exists in `repo_src/backend/database/models.py`
- Fields: `id`, `name`, `external_link`, `contact_info`, `unstructured_context`, timestamps
- Pydantic schemas exist: `PersonBase`, `PersonCreate`, `PersonUpdate`, `PersonResponse`
- Database persists at `repo_src/backend/data/exocortex.db`

#### MCP Architecture ✓ (READY FOR EXTENSION)
- MCP server at `repo_src/backend/mcp_server.py` with existing tools:
  - `search_knowledge`, `get_knowledge_stats`, `read_file`, `get_files_by_source`
- MCP client interface at `repo_src/backend/mcp_client.py`
- Pattern established: `@server.call_tool()` decorator → Direct function implementation

#### Chat System ✓ (READY FOR INTEGRATION)
- Two chat modes: Repository chat (`/api/chat`) and Knowledge chat (`/api/mcp-chat`)
- Agent architecture supports context augmentation via `mcp_chat_agent.py`
- `ChatRequest` schema has `enabled_sources` for filtering

#### Frontend ✓ (READY FOR NEW VIEW)
- React + TypeScript (Vite)
- View switcher pattern in `App.tsx` with 4 existing views: `chat`, `knowledge-chat`, `index`, `todo`
- Established patterns: `TodoView.tsx`, `IndexEditor.tsx` for UI components

### Gap Analysis

| Component | Current State | Required State | Gap |
|-----------|--------------|----------------|-----|
| Person CRUD API | Not implemented | REST endpoints | Need router implementation |
| MCP People Tools | Not implemented | 3-4 MCP tools | Need tool definitions |
| People UI | Not implemented | Full CRUD interface + NLP parser | Need React component |
| Context Injection | Not implemented | Agent integration | Need agent enhancement |
| Cross-referencing | Not implemented | Link people ↔ files | Need junction table |

---

## 3. Proposed Solution

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Chat Views   │  │ People View  │  │ Index View   │      │
│  │ (Existing)   │  │ (NEW)        │  │ (Existing)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘      │
│         │                  │                                 │
└─────────┼──────────────────┼─────────────────────────────────┘
          │                  │
          │ /api/chat        │ /api/people
          │ /api/mcp-chat    │ /api/people/parse
          ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Chat Router  │  │ People Router│  │ MCP Router   │      │
│  │ (Existing)   │  │ (NEW)        │  │ (Existing)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘      │
│         │                  │                                 │
│         ▼                  ▼                                 │
│  ┌──────────────────────────────────────────────────┐       │
│  │          MCP Chat Agent (ENHANCED)                │       │
│  │  - Search knowledge base                          │       │
│  │  - Detect people mentions (NEW)                   │       │
│  │  - Fetch people context (NEW)                     │       │
│  │  - Inject into LLM context (NEW)                  │       │
│  └──────────────┬───────────────────┬────────────────┘       │
│                 │                   │                        │
└─────────────────┼───────────────────┼────────────────────────┘
                  │                   │
                  ▼                   ▼
          ┌──────────────┐    ┌──────────────┐
          │  MCP Server  │    │   Database   │
          │  (ENHANCED)  │    │   (SQLite)   │
          │              │    │              │
          │ - search_people  │ │ - Person    │
          │ - get_person     │ │ - IndexEntry│
          │ - update_person  │ │ - PersonFile│
          │ - link_person    │ │   (NEW)     │
          └──────────────┘    └──────────────┘
```

### User Workflow

1. **Creating a Person Entry** (Natural Language)
   ```
   User navigates to "People" tab
   → Pastes text: "Met John Smith today, he's a senior engineer at OpenAI.
                   Email: john@openai.com. Twitter: @johnsmith.
                   Really knowledgeable about reinforcement learning and scaling laws."
   → Clicks "Parse and Create"
   → LLM extracts:
       - name: "John Smith"
       - contact_info: "Email: john@openai.com, Twitter: @johnsmith"
       - external_link: "https://twitter.com/johnsmith"
       - unstructured_context: "Senior engineer at OpenAI. Knowledgeable about
                                 reinforcement learning and scaling laws."
   → Creates database entry
   → Shows preview with edit option before saving
   ```

2. **Updating an Existing Entry**
   ```
   User pastes: "John Smith gave a talk at NeurIPS 2024 about alignment"
   → LLM searches for existing "John Smith"
   → If found: Updates unstructured_context (appends new info)
   → If not found: Prompts to create new entry or clarify which person
   ```

3. **Context Available in Chat**
   ```
   User asks in knowledge chat: "What did John mention about alignment?"
   → Agent searches knowledge base for relevant files
   → Agent detects "John" mention → Searches people database
   → Finds "John Smith" entry
   → Injects context: "John Smith is a senior engineer at OpenAI,
                       knowledgeable about reinforcement learning.
                       He gave a talk at NeurIPS 2024 about alignment."
   → LLM generates response with full context
   ```

---

## 4. Technical Architecture

### 4.1 Database Schema

#### Existing Table: `people`
```sql
CREATE TABLE people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    external_link VARCHAR,
    contact_info VARCHAR,
    unstructured_context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_people_name ON people(name);
```

#### New Table: `person_file_links` (For Cross-Referencing)
```sql
CREATE TABLE person_file_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    file_path VARCHAR NOT NULL,
    relevance_score FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE,
    UNIQUE(person_id, file_path)
);
CREATE INDEX idx_pfl_person ON person_file_links(person_id);
CREATE INDEX idx_pfl_file ON person_file_links(file_path);
```

**Rationale**: Links people to knowledge base files, enabling bidirectional queries:
- "Which people are mentioned in this file?"
- "Which files mention this person?"

#### New Pydantic Schemas
```python
# In repo_src/backend/data/schemas.py

class PersonFileLinkBase(BaseModel):
    person_id: int
    file_path: str
    relevance_score: Optional[float] = 1.0

class PersonFileLinkCreate(PersonFileLinkBase):
    pass

class PersonFileLinkResponse(PersonFileLinkBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PersonWithFiles(PersonResponse):
    """Person record with linked files"""
    linked_files: List[PersonFileLinkResponse] = []

class ParsedPersonData(BaseModel):
    """Result of LLM parsing free-form text"""
    name: str
    external_link: Optional[str] = None
    contact_info: Optional[str] = None
    unstructured_context: Optional[str] = None
    confidence: float  # 0.0-1.0 parsing confidence
    existing_person_match: Optional[int] = None  # ID if match found
    suggested_action: str  # "create", "update", "merge", "clarify"
```

---

### 4.2 Backend API Design

#### New Router: `repo_src/backend/routers/people.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from repo_src.backend.database import models
from repo_src.backend.data import schemas
from repo_src.backend.database.connection import get_db

router = APIRouter(prefix="/api/people", tags=["people"])

# === CRUD Endpoints ===

@router.get("/", response_model=List[schemas.PersonResponse])
async def list_people(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all people with optional search filter"""
    # Implementation: Query database with optional name/context search
    pass

@router.get("/{person_id}", response_model=schemas.PersonWithFiles)
async def get_person(person_id: int, db: Session = Depends(get_db)):
    """Get specific person with linked files"""
    # Implementation: Fetch person + related file links
    pass

@router.post("/", response_model=schemas.PersonResponse)
async def create_person(
    person: schemas.PersonCreate,
    db: Session = Depends(get_db)
):
    """Create new person entry"""
    # Implementation: Insert into database
    pass

@router.put("/{person_id}", response_model=schemas.PersonResponse)
async def update_person(
    person_id: int,
    person: schemas.PersonUpdate,
    db: Session = Depends(get_db)
):
    """Update existing person entry"""
    # Implementation: Update database record
    pass

@router.delete("/{person_id}")
async def delete_person(person_id: int, db: Session = Depends(get_db)):
    """Delete person entry"""
    # Implementation: Delete from database (cascades to links)
    pass

# === NLP Parsing Endpoints ===

@router.post("/parse", response_model=schemas.ParsedPersonData)
async def parse_person_text(
    text: str,
    existing_context: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Parse free-form text into structured person data using LLM.

    Args:
        text: User-pasted text about a person
        existing_context: Optional ID or name to update existing record

    Returns:
        Parsed structured data with suggested action
    """
    # Implementation:
    # 1. Call LLM with structured output schema
    # 2. Extract: name, contact_info, external_link, unstructured_context
    # 3. Search database for potential matches (fuzzy name matching)
    # 4. Return parsed data + suggestion (create/update/merge)
    pass

@router.post("/apply-parse", response_model=schemas.PersonResponse)
async def apply_parsed_data(
    parsed_data: schemas.ParsedPersonData,
    action: str,  # "create", "update", "merge"
    db: Session = Depends(get_db)
):
    """Apply the parsed data to database based on user confirmation"""
    # Implementation: Execute the suggested action
    pass

# === Cross-Referencing Endpoints ===

@router.post("/{person_id}/link-file")
async def link_person_to_file(
    person_id: int,
    file_path: str,
    relevance_score: Optional[float] = 1.0,
    db: Session = Depends(get_db)
):
    """Link a person to a knowledge base file"""
    # Implementation: Create PersonFileLink entry
    pass

@router.get("/{person_id}/files")
async def get_person_files(person_id: int, db: Session = Depends(get_db)):
    """Get all files linked to this person"""
    # Implementation: Query PersonFileLink by person_id
    pass

@router.get("/by-file/{file_path:path}")
async def get_people_by_file(file_path: str, db: Session = Depends(get_db)):
    """Get all people linked to a specific file"""
    # Implementation: Query PersonFileLink by file_path
    pass
```

**Key Design Decisions:**
- **Two-step parsing**: Parse first, show preview, then apply (prevents accidental overwrites)
- **Fuzzy matching**: Use LLM to detect existing person matches (handles variations like "John Smith" vs "J. Smith")
- **Confidence scores**: LLM returns confidence to flag ambiguous parses for user review

---

### 4.3 MCP Tool Integration

#### New Tools in `repo_src/backend/mcp_server.py`

```python
# === Tool Definitions ===

@server.list_tools()
async def list_tools():
    return [
        # ... existing tools ...

        Tool(
            name="search_people",
            description="Search for people in the personal dossier database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (name, organization, keywords)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),

        Tool(
            name="get_person",
            description="Get full details about a specific person by ID or name",
            inputSchema={
                "type": "object",
                "properties": {
                    "person_identifier": {
                        "type": "string",
                        "description": "Person ID or full name"
                    },
                    "include_linked_files": {
                        "type": "boolean",
                        "description": "Include list of linked knowledge base files",
                        "default": False
                    }
                },
                "required": ["person_identifier"]
            }
        ),

        Tool(
            name="update_person_context",
            description="Add new information to a person's context",
            inputSchema={
                "type": "object",
                "properties": {
                    "person_identifier": {
                        "type": "string",
                        "description": "Person ID or full name"
                    },
                    "new_context": {
                        "type": "string",
                        "description": "New information to append to context"
                    },
                    "source": {
                        "type": "string",
                        "description": "Source of information (optional)"
                    }
                },
                "required": ["person_identifier", "new_context"]
            }
        ),

        Tool(
            name="link_person_to_file",
            description="Associate a person with a knowledge base file",
            inputSchema={
                "type": "object",
                "properties": {
                    "person_identifier": {
                        "type": "string",
                        "description": "Person ID or full name"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Relative path to knowledge base file"
                    },
                    "relevance_score": {
                        "type": "number",
                        "description": "Relevance score 0.0-1.0",
                        "default": 1.0
                    }
                },
                "required": ["person_identifier", "file_path"]
            }
        ),
    ]

# === Tool Implementations ===

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_people":
        return await _search_people(
            query=arguments["query"],
            limit=arguments.get("limit", 10)
        )

    elif name == "get_person":
        return await _get_person(
            person_identifier=arguments["person_identifier"],
            include_linked_files=arguments.get("include_linked_files", False)
        )

    elif name == "update_person_context":
        return await _update_person_context(
            person_identifier=arguments["person_identifier"],
            new_context=arguments["new_context"],
            source=arguments.get("source")
        )

    elif name == "link_person_to_file":
        return await _link_person_to_file(
            person_identifier=arguments["person_identifier"],
            file_path=arguments["file_path"],
            relevance_score=arguments.get("relevance_score", 1.0)
        )

    # ... existing tool handlers ...

# === Helper Functions ===

async def _search_people(query: str, limit: int) -> List[dict]:
    """Search people database with fuzzy matching"""
    # Implementation:
    # 1. Query Person table with name LIKE %query%
    # 2. Also search in unstructured_context
    # 3. Return top N matches with relevance scores
    pass

async def _get_person(person_identifier: str, include_linked_files: bool) -> dict:
    """Get person by ID or name"""
    # Implementation:
    # 1. Try to parse as int (ID) or search by name
    # 2. Fetch Person record
    # 3. Optionally join with PersonFileLink
    # 4. Return full record
    pass

async def _update_person_context(
    person_identifier: str,
    new_context: str,
    source: Optional[str]
) -> dict:
    """Append new information to person's context"""
    # Implementation:
    # 1. Find person
    # 2. Append to unstructured_context with timestamp and source
    # 3. Update updated_at timestamp
    # 4. Return updated record
    pass

async def _link_person_to_file(
    person_identifier: str,
    file_path: str,
    relevance_score: float
) -> dict:
    """Create link between person and file"""
    # Implementation:
    # 1. Find person
    # 2. Validate file exists in knowledge base
    # 3. Create PersonFileLink entry
    # 4. Return confirmation
    pass
```

**Design Rationale:**
- **Model-accessible**: LLMs can proactively search and update people context during chat
- **Read + Write**: Tools support both querying and updating (enables autonomous agent behavior)
- **Validation**: Tools validate identifiers and file paths before making changes

---

### 4.4 Agent Enhancement

#### Modified: `repo_src/backend/agents/mcp_chat_agent.py`

Add new method: `_enrich_with_people_context()`

```python
async def _enrich_with_people_context(
    self,
    search_results: List[dict],
    user_prompt: str,
    db: Session
) -> dict:
    """
    Detect people mentions in search results and user prompt,
    fetch their context from database, and return enriched context.

    Args:
        search_results: Knowledge base search results
        user_prompt: User's original query
        db: Database session

    Returns:
        {
            "people_mentioned": List[PersonResponse],
            "relevant_files_with_people": List[tuple[file_path, people_in_file]]
        }
    """
    # Implementation:
    # 1. Extract potential person names from user_prompt using NER or LLM
    # 2. Extract potential person names from file descriptions/content
    # 3. Query people database for matches
    # 4. Query PersonFileLink for files in search_results
    # 5. Return enriched context
    pass

# Modify existing _generate_response() method:
async def _generate_response(
    self,
    user_prompt: str,
    file_contents: List[dict],
    people_context: Optional[dict] = None  # NEW PARAMETER
):
    """Generate response with file context AND people context"""

    # Build enhanced system prompt
    system_prompt = f"""You are a knowledgeable assistant...

    **Relevant Files:**
    {format_file_contents(file_contents)}
    """

    # NEW: Add people context if available
    if people_context and people_context["people_mentioned"]:
        system_prompt += "\n\n**Relevant People Context:**\n"
        for person in people_context["people_mentioned"]:
            system_prompt += f"""
            - **{person.name}**
              Contact: {person.contact_info or 'N/A'}
              External: {person.external_link or 'N/A'}
              Context: {person.unstructured_context or 'No additional context'}
            """

    # Call LLM with enhanced prompt
    # ...
```

**Modified Flow:**
```
User Prompt
  ↓
Extract Search Terms
  ↓
Search Knowledge Base (existing)
  ↓
_enrich_with_people_context()  ← NEW STEP
  ↓
Generate Response with both file + people context
  ↓
Return to User
```

---

### 4.5 Frontend UI Design

#### New Component: `repo_src/frontend/src/components/PeopleView.tsx`

```typescript
interface Person {
  id: number;
  name: string;
  external_link?: string;
  contact_info?: string;
  unstructured_context?: string;
  created_at: string;
  updated_at: string;
}

interface ParsedPersonData {
  name: string;
  external_link?: string;
  contact_info?: string;
  unstructured_context?: string;
  confidence: number;
  existing_person_match?: number;
  suggested_action: "create" | "update" | "merge" | "clarify";
}

const PeopleView: React.FC = () => {
  // === State ===
  const [people, setPeople] = useState<Person[]>([]);
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null);
  const [inputText, setInputText] = useState("");
  const [parsedData, setParsedData] = useState<ParsedPersonData | null>(null);
  const [isParseMode, setIsParseMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // === API Calls ===
  const fetchPeople = async () => {
    const response = await fetch("/api/people/");
    const data = await response.json();
    setPeople(data);
  };

  const parseText = async () => {
    const response = await fetch("/api/people/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: inputText })
    });
    const data = await response.json();
    setParsedData(data);
  };

  const applyParsedData = async () => {
    const response = await fetch("/api/people/apply-parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        parsed_data: parsedData,
        action: parsedData.suggested_action
      })
    });
    const newPerson = await response.json();
    setPeople([...people, newPerson]);
    setParsedData(null);
    setInputText("");
  };

  // === Render ===
  return (
    <div className="people-view">
      {/* Left Sidebar: People List */}
      <div className="people-list-sidebar">
        <input
          type="text"
          placeholder="Search people..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <ul>
          {people
            .filter(p => p.name.toLowerCase().includes(searchQuery.toLowerCase()))
            .map(person => (
              <li
                key={person.id}
                onClick={() => setSelectedPerson(person)}
                className={selectedPerson?.id === person.id ? "selected" : ""}
              >
                {person.name}
              </li>
            ))}
        </ul>
      </div>

      {/* Center Panel: Input / Parse Mode */}
      <div className="people-center-panel">
        {!isParseMode ? (
          <div className="add-person-section">
            <h2>Add or Update Person</h2>
            <textarea
              placeholder="Paste any text about a person here..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              rows={10}
            />
            <button onClick={parseText}>Parse and Preview</button>
          </div>
        ) : (
          <div className="parse-preview-section">
            <h2>Parsed Data - Review Before Saving</h2>

            {parsedData && (
              <>
                <div className="confidence-indicator">
                  Confidence: {(parsedData.confidence * 100).toFixed(0)}%
                </div>

                <div className="suggested-action">
                  Suggested Action: <strong>{parsedData.suggested_action}</strong>
                  {parsedData.existing_person_match && (
                    <span> - Will update existing record #{parsedData.existing_person_match}</span>
                  )}
                </div>

                <div className="parsed-fields">
                  <label>Name:</label>
                  <input value={parsedData.name} readOnly />

                  <label>Contact Info:</label>
                  <input value={parsedData.contact_info || ""} readOnly />

                  <label>External Link:</label>
                  <input value={parsedData.external_link || ""} readOnly />

                  <label>Context:</label>
                  <textarea value={parsedData.unstructured_context || ""} readOnly rows={5} />
                </div>

                <div className="action-buttons">
                  <button onClick={applyParsedData}>Apply Changes</button>
                  <button onClick={() => { setParsedData(null); setIsParseMode(false); }}>
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Right Panel: Person Details */}
      <div className="people-detail-panel">
        {selectedPerson ? (
          <>
            <h2>{selectedPerson.name}</h2>
            <div className="person-field">
              <strong>Contact:</strong> {selectedPerson.contact_info || "N/A"}
            </div>
            <div className="person-field">
              <strong>External Link:</strong>
              {selectedPerson.external_link ? (
                <a href={selectedPerson.external_link} target="_blank" rel="noreferrer">
                  {selectedPerson.external_link}
                </a>
              ) : "N/A"}
            </div>
            <div className="person-field">
              <strong>Context:</strong>
              <div className="context-text">
                {selectedPerson.unstructured_context || "No additional context"}
              </div>
            </div>
            <div className="person-field">
              <strong>Last Updated:</strong> {new Date(selectedPerson.updated_at).toLocaleDateString()}
            </div>
            <button onClick={() => {
              setInputText(`Update ${selectedPerson.name}: `);
              setIsParseMode(false);
            }}>
              Add More Context
            </button>
          </>
        ) : (
          <div className="no-selection">
            Select a person to view details
          </div>
        )}
      </div>
    </div>
  );
};

export default PeopleView;
```

#### Modified: `repo_src/frontend/src/App.tsx`

```typescript
// Add to view state type
type ViewMode = 'chat' | 'knowledge-chat' | 'index' | 'todo' | 'people';  // Add 'people'

// Add to view switcher buttons
<button
  onClick={() => setCurrentView('people')}
  className={currentView === 'people' ? 'active' : ''}
>
  People
</button>

// Add to view rendering
{currentView === 'people' && <PeopleView />}
```

**UI Design Principles:**
- **Three-panel layout**: List (left), Input/Parse (center), Detail (right)
- **Parse-then-apply**: Two-step process prevents accidental data loss
- **Visual confidence**: Show parsing confidence to alert user to review low-confidence parses
- **Quick updates**: Selected person can be quickly updated with new context

---

## 5. Scope of Work

### 5.1 Backend Tasks

| Task | Component | Estimated Complexity | Dependencies |
|------|-----------|---------------------|--------------|
| Create PersonFileLink model | `database/models.py` | Low | None |
| Create PersonFileLink schemas | `data/schemas.py` | Low | Model complete |
| Implement People router | `routers/people.py` | Medium | Schemas complete |
| Add LLM parsing endpoint | `routers/people.py` | High | Router foundation |
| Implement MCP people tools | `mcp_server.py` | Medium | Database models |
| Enhance MCP agent | `agents/mcp_chat_agent.py` | High | MCP tools complete |
| Write unit tests | `tests/test_people.py` | Medium | Router complete |

**Total Backend: ~3-5 days of development**

---

### 5.2 Frontend Tasks

| Task | Component | Estimated Complexity | Dependencies |
|------|-----------|---------------------|--------------|
| Create PeopleView component | `components/PeopleView.tsx` | High | API endpoints live |
| Add people tab to App.tsx | `App.tsx` | Low | None |
| Style people view | `styles/App.css` | Medium | Component structure |
| Add people sidebar to chat | `App.tsx` | Medium | People API |
| Implement search/filter | `PeopleView.tsx` | Low | Component complete |
| Add loading states | `PeopleView.tsx` | Low | Component complete |

**Total Frontend: ~2-3 days of development**

---

### 5.3 Integration Tasks

| Task | Description | Complexity | Dependencies |
|------|-------------|-----------|--------------|
| Context injection | Agent auto-fetches people context | Medium | Agent + MCP tools |
| File linking UI | Link people from chat to files | Medium | Both FE + BE complete |
| Cross-reference display | Show linked files in people view | Low | Link API complete |
| Error handling | Graceful failures for all flows | Medium | All components |
| Documentation | API docs, user guide | Low | Features complete |

**Total Integration: ~2-3 days**

---

### 5.4 Total Effort Estimate

- **Backend**: 3-5 days
- **Frontend**: 2-3 days
- **Integration**: 2-3 days
- **Testing + Polish**: 2 days
- **Documentation**: 1 day

**Total: 10-14 days** (single developer)

---

## 6. Implementation Phases

### Phase 1: Foundation (Days 1-3)
**Goal**: Basic CRUD functionality

- [ ] Create `PersonFileLink` model and migration
- [ ] Implement People router with basic CRUD endpoints
- [ ] Write basic tests for CRUD operations
- [ ] Create simple PeopleView frontend (list, create, view)
- [ ] Manual entry only (no parsing yet)

**Deliverable**: Users can manually create/view/edit people entries

---

### Phase 2: NLP Parsing (Days 4-6)
**Goal**: Natural language interface

- [ ] Implement `/api/people/parse` endpoint with LLM integration
- [ ] Add fuzzy matching for existing person detection
- [ ] Implement two-step parse-preview-apply flow
- [ ] Add parsing UI to PeopleView
- [ ] Handle confidence thresholds and ambiguous cases

**Deliverable**: Users can paste text and have it auto-parsed

---

### Phase 3: MCP Integration (Days 7-9)
**Goal**: Make people context available to LLMs

- [ ] Implement 4 MCP tools: `search_people`, `get_person`, `update_person_context`, `link_person_to_file`
- [ ] Add `_enrich_with_people_context()` to mcp_chat_agent
- [ ] Modify `_generate_response()` to include people context
- [ ] Test MCP tools via MCP client
- [ ] Verify context appears in chat responses

**Deliverable**: Chat agents can query and reference people context

---

### Phase 4: UI Integration (Days 10-12)
**Goal**: Seamless UX across views

- [ ] Add People tab to main navigation
- [ ] Display people context in chat responses (badges/cards)
- [ ] Implement file-person linking from chat
- [ ] Add cross-reference display in PeopleView
- [ ] Polish UI/UX, add loading states

**Deliverable**: Cohesive experience across all views

---

### Phase 5: Testing & Documentation (Days 13-14)
**Goal**: Production-ready

- [ ] Comprehensive unit tests (backend)
- [ ] Integration tests (full flow)
- [ ] E2E tests (frontend)
- [ ] API documentation
- [ ] User guide / tutorial
- [ ] Performance testing

**Deliverable**: Stable, documented feature

---

## 7. Data Flow Diagrams

### 7.1 Create/Update Person Flow

```
┌──────────────────────────────────────────────────────────────┐
│  USER                                                         │
└────┬─────────────────────────────────────────────────────────┘
     │
     │ 1. Pastes text about person
     ▼
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (PeopleView)                                       │
│  - User clicks "Parse and Preview"                          │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 2. POST /api/people/parse { text: "..." }
     ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND (People Router)                                     │
│  - Receive text                                             │
│  - Call LLM with structured output schema                   │
│  - Extract: name, contact_info, external_link, context     │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 3. Query database for existing matches
     ▼
┌─────────────────────────────────────────────────────────────┐
│  DATABASE (SQLite)                                           │
│  - Search Person table by name (fuzzy match)                │
│  - Return existing records if found                         │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 4. Return ParsedPersonData { ..., suggested_action }
     ▼
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (PeopleView)                                       │
│  - Display parsed fields                                    │
│  - Show confidence score                                    │
│  - Show suggested action ("create", "update", etc.)         │
│  - User reviews and clicks "Apply"                          │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 5. POST /api/people/apply-parse { parsed_data, action }
     ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND (People Router)                                     │
│  - Validate action                                          │
│  - Execute: INSERT or UPDATE in database                    │
│  - Return PersonResponse                                    │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 6. Return PersonResponse (created/updated record)
     ▼
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (PeopleView)                                       │
│  - Update people list                                       │
│  - Clear input                                              │
│  - Show success message                                     │
└─────────────────────────────────────────────────────────────┘
```

---

### 7.2 Chat with People Context Flow

```
┌──────────────────────────────────────────────────────────────┐
│  USER                                                         │
└────┬─────────────────────────────────────────────────────────┘
     │
     │ 1. "What did John mention about alignment?"
     ▼
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (Chat View)                                        │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 2. POST /api/mcp-chat { prompt: "..." }
     ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND (MCP Chat Agent)                                    │
│  - Extract search terms: ["John", "alignment"]              │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 3. Search knowledge base (existing flow)
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MCP Server                                                  │
│  - search_knowledge("John") → Returns relevant files        │
│  - search_knowledge("alignment") → Returns more files       │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 4. NEW: _enrich_with_people_context()
     ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND (MCP Chat Agent)                                    │
│  - Detect "John" in prompt                                  │
│  - Call MCP: search_people("John")                          │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 5. MCP search_people tool
     ▼
┌─────────────────────────────────────────────────────────────┐
│  DATABASE (SQLite)                                           │
│  - Query Person WHERE name LIKE '%John%'                    │
│  - Return: John Smith (ID 42, context: "...")               │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 6. NEW: Query PersonFileLink
     ▼
┌─────────────────────────────────────────────────────────────┐
│  DATABASE (SQLite)                                           │
│  - Query PersonFileLink WHERE person_id = 42                │
│  - Return: [file1.md, file2.md] linked to John             │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 7. Build enriched context
     ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND (MCP Chat Agent)                                    │
│  - Combine: File contents + John Smith's person record      │
│  - System prompt includes:                                  │
│    * Selected file contents (existing)                      │
│    * Person context: "John Smith is a senior engineer at   │
│      OpenAI, expert in RL. Mentioned in files: [...]"      │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 8. Generate response
     ▼
┌─────────────────────────────────────────────────────────────┐
│  LLM (OpenRouter)                                            │
│  - Receives enriched prompt                                 │
│  - Generates contextual response about John and alignment   │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 9. Return ChatResponse
     ▼
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (Chat View)                                        │
│  - Display response                                         │
│  - Optionally show badge: "Context from: John Smith"        │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Security and Privacy Considerations

### 8.1 Data Sensitivity
- **Highly Sensitive**: People records contain personal information (contact, context)
- **Risk**: Unauthorized access, data leakage, prompt injection

### 8.2 Security Measures

| Risk | Mitigation |
|------|-----------|
| SQL Injection | Use SQLAlchemy ORM with parameterized queries |
| Unauthorized API access | Add authentication middleware (future: JWT/OAuth) |
| XSS in UI | Sanitize all user inputs, use React's default escaping |
| MCP tool abuse | Rate limiting on write operations, audit logs |
| Prompt injection | Validate LLM outputs before database writes |
| Data leakage via LLM | Do not send full database in prompts; query selectively |

### 8.3 Privacy Controls (Future Enhancements)
- [ ] Encryption at rest for sensitive fields (contact_info, unstructured_context)
- [ ] User authentication and multi-user support with access control
- [ ] Audit log for all person record modifications
- [ ] GDPR compliance: Export/delete person data on request

**V1 Assumption**: Single-user local deployment with no authentication

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Backend (`tests/test_people.py`)**
```python
def test_create_person():
    """Test POST /api/people/"""

def test_list_people():
    """Test GET /api/people/"""

def test_update_person():
    """Test PUT /api/people/{id}"""

def test_parse_person_text():
    """Test POST /api/people/parse with sample text"""

def test_parse_detects_existing():
    """Verify parsing identifies existing person matches"""

def test_link_person_to_file():
    """Test POST /api/people/{id}/link-file"""

def test_mcp_search_people():
    """Test MCP search_people tool"""

def test_mcp_update_person_context():
    """Test MCP update_person_context tool"""
```

**Frontend (`src/components/__tests__/PeopleView.test.tsx`)**
```typescript
describe('PeopleView', () => {
  test('renders people list', () => { ... });
  test('parses text and shows preview', async () => { ... });
  test('applies parsed data on confirmation', async () => { ... });
  test('handles parse errors gracefully', async () => { ... });
});
```

---

### 9.2 Integration Tests

```python
def test_full_create_flow():
    """
    End-to-end test: Parse text → Preview → Apply → Verify in database
    """

def test_chat_with_people_context():
    """
    Test that chat agent includes people context when person is mentioned
    """
    # 1. Create person "John Smith"
    # 2. Send chat: "What does John think about AI?"
    # 3. Verify response includes John's context
    # 4. Verify MCP search_people was called
```

---

### 9.3 E2E Tests (Playwright/Cypress)

```typescript
test('user can add person via paste', async ({ page }) => {
  await page.goto('/people');
  await page.fill('textarea', 'John Smith, engineer at OpenAI...');
  await page.click('button:has-text("Parse and Preview")');
  await expect(page.locator('.parsed-fields')).toBeVisible();
  await page.click('button:has-text("Apply Changes")');
  await expect(page.locator('text=John Smith')).toBeVisible();
});

test('person context appears in chat', async ({ page }) => {
  // Setup: Create person first
  await createPerson({ name: 'John Smith', context: 'Expert in RL' });

  // Test: Mention in chat
  await page.goto('/knowledge-chat');
  await page.fill('input[type="text"]', 'What does John think about alignment?');
  await page.press('input[type="text"]', 'Enter');

  // Verify: Response includes context
  await expect(page.locator('text=Expert in RL')).toBeVisible({ timeout: 10000 });
});
```

---

## 10. Success Metrics

### 10.1 Functional Metrics
- [ ] Users can create person entries in < 30 seconds
- [ ] Parsing accuracy > 90% on well-structured input
- [ ] People context appears in chat within 2 seconds
- [ ] Zero data loss across application restarts

### 10.2 Performance Metrics
- [ ] Parse endpoint responds in < 3 seconds
- [ ] List people endpoint responds in < 500ms (for 1000 records)
- [ ] Chat with people context adds < 1 second to response time
- [ ] MCP tools respond in < 500ms

### 10.3 User Experience Metrics
- [ ] 80%+ of parsed records require no manual edits
- [ ] Users reference people context in 30%+ of chats
- [ ] 90%+ success rate on first parse attempt

---

## 11. Future Enhancements (Out of Scope for V1)

### 11.1 Advanced Features
- **Social Graph Visualization**: D3.js network graph showing person-file-person relationships
- **Automatic Extraction**: Background job to extract people mentions from knowledge base
- **External Integrations**:
  - LinkedIn API for enriching profiles
  - Email client integration for automatic contact sync
  - Calendar integration for meeting notes
- **Smart Suggestions**: "You mentioned 'Sarah' - did you mean Sarah Johnson or Sarah Chen?"
- **Relationship Types**: Tag relationships (colleague, mentor, friend, etc.)

### 11.2 Collaboration Features
- **Multi-user support**: Shared people database with access control
- **Collaborative editing**: Multiple users can update same person
- **Comments/notes**: Thread discussions on person records

### 11.3 AI Enhancements
- **Proactive context**: Agent suggests relevant people before user asks
- **Timeline view**: Chronological view of all interactions with a person
- **Sentiment analysis**: Track sentiment of mentions over time
- **Auto-summarization**: Daily digest of new information about key people

---

## 12. Open Questions for Review

### 12.1 Design Decisions Requiring Input

1. **Person Uniqueness**:
   - How should we handle name collisions (two "John Smith"s)?
   - Should we add a unique constraint or allow duplicates?
   - Suggestion: Allow duplicates, use context to disambiguate

2. **Context Formatting**:
   - Should `unstructured_context` be plain text or support markdown?
   - Suggestion: Support markdown for rich formatting (links, lists)

3. **Parsing Confidence Threshold**:
   - What confidence threshold triggers a warning?
   - Suggestion: < 70% shows yellow warning, < 50% requires manual review

4. **File Linking Strategy**:
   - Should file links be created automatically by agent or manually by user?
   - Suggestion: Both - agent creates automatically, user can edit

5. **MCP Tool Permissions**:
   - Should MCP tools be able to DELETE people records?
   - Suggestion: No - read and update only, user must manually delete

### 12.2 Technical Questions

1. **Database Migration**:
   - Use Alembic for migrations or continue with `create_all()`?
   - For V1: `create_all()` is fine, add Alembic in V2

2. **LLM Provider**:
   - Use existing OpenRouter integration or add dedicated parsing model?
   - Suggestion: Reuse OpenRouter, optionally allow local model for privacy

3. **Search Strategy**:
   - Full-text search, fuzzy matching, or vector embeddings?
   - Suggestion: Start with SQL LIKE, add embeddings in V2 if needed

---

## 13. Risks and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| LLM parsing inaccuracy | High | Medium | Two-step parse-preview-apply, confidence scores |
| Performance degradation with many people | Medium | Medium | Database indexing, pagination, lazy loading |
| MCP tool conflicts with existing tools | Low | High | Thorough integration testing |
| User confusion about parse suggestions | Medium | Low | Clear UI labels, help tooltips |
| Data loss during updates | Low | High | Backup strategy, soft deletes |

---

## 14. Conclusion and Next Steps

### Summary
The People Context Management System is a well-scoped feature that leverages existing architecture (database, MCP, agents, frontend) to add a valuable new dimension to the Exocortex knowledge base. The implementation is feasible within 10-14 days and follows established patterns in the codebase.

### Key Strengths
- ✅ Foundation already exists (Person model, schemas)
- ✅ Clear integration points with existing systems
- ✅ Natural language interface reduces friction
- ✅ Universal context availability via MCP tools

### Recommended Next Steps
1. **Review and approve** this PRD with stakeholder feedback
2. **Prioritize open questions** (Section 12) and make design decisions
3. **Set up development environment** with test database
4. **Begin Phase 1** (Foundation) implementation
5. **Iterate** with user feedback after each phase

---

## Appendix A: API Endpoint Reference

### People CRUD Endpoints

```
GET    /api/people/                      List all people
GET    /api/people/{id}                  Get person by ID
POST   /api/people/                      Create person
PUT    /api/people/{id}                  Update person
DELETE /api/people/{id}                  Delete person
```

### People Parsing Endpoints

```
POST   /api/people/parse                 Parse text into structured data
POST   /api/people/apply-parse           Apply parsed data to database
```

### People Linking Endpoints

```
POST   /api/people/{id}/link-file        Link person to file
GET    /api/people/{id}/files            Get files linked to person
GET    /api/people/by-file/{path}        Get people linked to file
```

---

## Appendix B: Database Schema Reference

### Tables

**people**
```sql
CREATE TABLE people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    external_link VARCHAR,
    contact_info VARCHAR,
    unstructured_context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_people_name ON people(name);
```

**person_file_links**
```sql
CREATE TABLE person_file_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    file_path VARCHAR NOT NULL,
    relevance_score FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE,
    UNIQUE(person_id, file_path)
);
CREATE INDEX idx_pfl_person ON person_file_links(person_id);
CREATE INDEX idx_pfl_file ON person_file_links(file_path);
```

---

## Appendix C: Example User Flows

### Flow 1: First-time user adds a person
```
1. User clicks "People" tab
2. Sees empty list with prompt: "Add your first person"
3. Pastes: "Met Alice Chen today, CTO at Anthropic. Email: alice@anthropic.com.
            Expert in AI safety and constitutional AI."
4. Clicks "Parse and Preview"
5. System shows:
   - Name: Alice Chen
   - Contact: Email: alice@anthropic.com
   - External Link: (empty - could add)
   - Context: CTO at Anthropic. Expert in AI safety and constitutional AI.
   - Confidence: 95%
   - Action: CREATE
6. User clicks "Apply"
7. Alice Chen appears in people list
```

### Flow 2: User updates existing person
```
1. User pastes: "Alice gave a talk at the AI Safety conference about RLHF"
2. System parses and shows:
   - Name: Alice Chen
   - Existing Match: Found (ID: 1, Alice Chen)
   - New Context: "Gave a talk at AI Safety conference about RLHF"
   - Confidence: 88%
   - Action: UPDATE (append to existing context)
3. User clicks "Apply"
4. Alice's record updated with new information
```

### Flow 3: User asks about person in chat
```
1. User in Knowledge Chat: "What did Alice say about RLHF?"
2. Agent:
   - Searches knowledge base for "RLHF"
   - Detects "Alice" → Searches people database
   - Finds Alice Chen: "CTO at Anthropic, expert in AI safety, gave talk about RLHF"
   - Includes this context in LLM prompt
3. LLM response: "Based on Alice Chen's recent talk at the AI Safety conference,
                  she discussed RLHF in the context of..."
4. UI shows small badge: "Context from: Alice Chen 👤"
```

---

## Appendix D: Configuration Options

```yaml
# config/people_feature.yaml (future)

parsing:
  llm_model: "openrouter/claude-3.5-sonnet"  # Model for parsing
  confidence_threshold_warning: 0.7
  confidence_threshold_reject: 0.5
  max_context_length: 5000  # characters

search:
  fuzzy_match_threshold: 0.8  # Levenshtein distance
  max_results: 20
  enable_semantic_search: false  # Future: vector embeddings

linking:
  auto_link_confidence: 0.9  # Auto-link files if confidence > this
  max_links_per_person: 100

ui:
  people_per_page: 50
  show_confidence_scores: true
  enable_markdown: true
```

---

**END OF PRD**

---

## Review Checklist

- [ ] Architecture aligns with existing codebase patterns
- [ ] Scope is achievable within estimated timeline
- [ ] Security and privacy concerns are addressed
- [ ] Open questions (Section 12) are resolved
- [ ] Success metrics (Section 10) are agreed upon
- [ ] Implementation phases (Section 6) are approved
- [ ] Ready to proceed with Phase 1 implementation
