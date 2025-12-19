# People Context Feature - Architecture Quick Reference

**Version:** 1.0
**Date:** 2025-11-24
**Related:** See `people_context_feature.md` for full PRD

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                             │
│                                                                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │   Chat     │  │  Knowledge │  │   People   │  │   Index    │   │
│  │   View     │  │    Chat    │  │    View    │  │   Editor   │   │
│  │ (existing) │  │ (existing) │  │   (NEW)    │  │ (existing) │   │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────────────┘   │
│        │               │               │                            │
└────────┼───────────────┼───────────────┼────────────────────────────┘
         │               │               │
         │               │               │ REST API
         ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                               │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │  Chat Router    │  │ People Router   │  │  Index Router   │    │
│  │  /api/chat      │  │ /api/people     │  │  /api/index     │    │
│  │  /api/mcp-chat  │  │  (NEW)          │  │  (existing)     │    │
│  │  (existing)     │  │                 │  │                 │    │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────┘    │
│           │                    │                                    │
│           ▼                    │                                    │
│  ┌────────────────────────────┐│                                    │
│  │   MCP Chat Agent           ││                                    │
│  │   (ENHANCED)               ││                                    │
│  │                            ││                                    │
│  │  • Search knowledge base   ││                                    │
│  │  • Detect people mentions  ││◄───────────────────────────────┐  │
│  │  • Enrich with context     ││                                │  │
│  │  • Generate response       ││                                │  │
│  └────────┬───────────────────┘│                                │  │
│           │                    │                                │  │
└───────────┼────────────────────┼────────────────────────────────┼──┘
            │                    │                                │
            │                    │                                │
            ▼                    ▼                                │
    ┌───────────────┐    ┌───────────────┐                      │
    │  MCP Server   │    │   Database    │                      │
    │  (ENHANCED)   │    │   (SQLite)    │                      │
    │               │    │               │                      │
    │  NEW TOOLS:   │    │  NEW TABLES:  │                      │
    │  • search_    │    │  • Person     │                      │
    │    people     │◄───┤    (exists!)  │                      │
    │  • get_person │    │  • PersonFile │                      │
    │  • update_    │    │    Link (NEW) │                      │
    │    person_    │    │               │                      │
    │    context    │    │               │                      │
    │  • link_      │    │               │                      │
    │    person_    │    └───────────────┘                      │
    │    to_file    │                                           │
    └───────┬───────┘                                           │
            │                                                   │
            └───────────────────────────────────────────────────┘
                         MCP Protocol (stdio)
```

---

## Component Breakdown

### 1. Database Layer (SQLAlchemy)

**Existing: Person Model** ✓
```python
class Person(Base):
    __tablename__ = "people"
    id, name, external_link, contact_info, unstructured_context
    created_at, updated_at
```

**New: PersonFileLink Model** (Junction Table)
```python
class PersonFileLink(Base):
    __tablename__ = "person_file_links"
    id, person_id, file_path, relevance_score
    created_at
```

**Purpose**: Link people to knowledge base files for bidirectional queries.

---

### 2. Backend API (FastAPI)

#### New Router: `/api/people`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/people/` | GET | List all people (with search filter) |
| `/api/people/{id}` | GET | Get person by ID (with linked files) |
| `/api/people/` | POST | Create new person |
| `/api/people/{id}` | PUT | Update person |
| `/api/people/{id}` | DELETE | Delete person |
| `/api/people/parse` | POST | **Parse free-text into structured data** |
| `/api/people/apply-parse` | POST | **Apply parsed data to database** |
| `/api/people/{id}/link-file` | POST | Link person to knowledge file |
| `/api/people/{id}/files` | GET | Get files linked to person |
| `/api/people/by-file/{path}` | GET | Get people linked to file |

**Key Innovation**: `/parse` endpoint uses LLM to extract structured data from natural language.

---

### 3. MCP Server Tools

#### New Tools for Model Access

```python
@server.call_tool()
async def call_tool(name, arguments):
    if name == "search_people":
        # Search people database by name/context
        # Returns: List[Person] with relevance scores

    elif name == "get_person":
        # Get full person record by ID or name
        # Returns: Person with optional linked files

    elif name == "update_person_context":
        # Append new information to person's context
        # Returns: Updated Person record

    elif name == "link_person_to_file":
        # Create association between person and file
        # Returns: PersonFileLink record
```

**Purpose**: Allow LLMs to autonomously query and update people context during chat.

---

### 4. MCP Chat Agent Enhancement

#### New Method: `_enrich_with_people_context()`

```python
async def _enrich_with_people_context(
    search_results: List[dict],
    user_prompt: str,
    db: Session
) -> dict:
    """
    1. Detect person names in user prompt (NER or LLM)
    2. Detect person mentions in search results
    3. Query people database for matches
    4. Query PersonFileLink for cross-references
    5. Return enriched context
    """
```

#### Modified: `_generate_response()`

```python
async def _generate_response(
    user_prompt: str,
    file_contents: List[dict],
    people_context: Optional[dict] = None  # NEW
):
    """
    Build system prompt with:
    - File contents (existing)
    - People context (NEW): Name, contact, external link, context

    Call LLM with enriched prompt
    """
```

**Result**: Chat responses now include relevant people context automatically.

---

### 5. Frontend UI

#### New Component: `PeopleView.tsx`

**Three-Panel Layout:**
```
┌────────────┬──────────────────┬────────────────┐
│   LIST     │   INPUT/PARSE    │    DETAILS     │
│            │                  │                │
│ • Alice    │  Paste text:     │  Name: Alice   │
│ • Bob      │  "Met Alice..."  │  Contact: ...  │
│ • Carol    │                  │  Context: ...  │
│            │  [Parse Button]  │  Links: 3 files│
│            │                  │                │
│            │  Preview:        │  [Edit] [Del]  │
│            │  Name: Alice     │                │
│            │  Confidence: 95% │                │
│            │  [Apply] [Cancel]│                │
└────────────┴──────────────────┴────────────────┘
```

**Workflow:**
1. User pastes text in center panel
2. Clicks "Parse and Preview"
3. LLM extracts structured fields
4. System shows preview with confidence score
5. User reviews and clicks "Apply"
6. Person appears in list (left panel)
7. Click person to view details (right panel)

---

## Data Flow Examples

### Example 1: Creating a Person

```
USER → Pastes text
  ↓
FRONTEND → POST /api/people/parse { text: "..." }
  ↓
BACKEND → LLM extracts fields
  ↓
DATABASE → Query existing people (fuzzy match)
  ↓
BACKEND → Return ParsedPersonData with suggested action
  ↓
FRONTEND → Show preview + confidence + suggestion
  ↓
USER → Clicks "Apply"
  ↓
FRONTEND → POST /api/people/apply-parse { parsed_data, action }
  ↓
BACKEND → Insert/Update database
  ↓
FRONTEND → Update list, show success
```

---

### Example 2: Chat with People Context

```
USER → "What did Alice say about AI safety?"
  ↓
FRONTEND → POST /api/mcp-chat { prompt: "..." }
  ↓
AGENT → Extract search terms: ["Alice", "AI safety"]
  ↓
MCP → search_knowledge("Alice") → Returns files mentioning Alice
  ↓
AGENT → _enrich_with_people_context()
  ↓
MCP → search_people("Alice") → Returns Alice Chen's record
  ↓
DATABASE → Query Person + PersonFileLink
  ↓
AGENT → Build enriched prompt:
        • File contents: [meeting_notes.md, ...]
        • Person: Alice Chen, CTO at Anthropic, expert in AI safety
  ↓
LLM → Generate response with full context
  ↓
FRONTEND → Display response + "Context from: Alice Chen 👤"
```

---

## Implementation Phases

### Phase 1: Foundation (Days 1-3)
- ✅ Person model already exists
- [ ] Create PersonFileLink model
- [ ] Implement People router (CRUD only)
- [ ] Create basic PeopleView UI (manual entry)

**Deliverable**: Users can manually create/view/edit people

---

### Phase 2: NLP Parsing (Days 4-6)
- [ ] Implement `/api/people/parse` with LLM
- [ ] Add fuzzy matching for existing people
- [ ] Build parse-preview-apply UI flow

**Deliverable**: Users can paste text for auto-parsing

---

### Phase 3: MCP Integration (Days 7-9)
- [ ] Add 4 MCP tools to `mcp_server.py`
- [ ] Implement `_enrich_with_people_context()` in agent
- [ ] Modify `_generate_response()` to include people

**Deliverable**: Chat includes people context automatically

---

### Phase 4: UI Polish (Days 10-12)
- [ ] Add People tab to navigation
- [ ] Display people badges in chat
- [ ] Implement file-person linking UI

**Deliverable**: Seamless UX across all views

---

### Phase 5: Testing (Days 13-14)
- [ ] Unit tests (backend)
- [ ] Integration tests (full flow)
- [ ] E2E tests (frontend)
- [ ] Documentation

**Deliverable**: Production-ready feature

---

## Key Technical Decisions

### 1. Parsing Strategy: Two-Step Parse-Apply
**Why?** Prevents accidental overwrites, gives user control
- Step 1: Parse text → Show preview
- Step 2: User confirms → Apply to database

### 2. Fuzzy Matching for Existing People
**Why?** Handles name variations ("John Smith" vs "J. Smith")
- Use LLM to detect potential matches
- Show confidence score
- Suggest "create" vs "update" vs "merge"

### 3. Unstructured Context Field
**Why?** Flexibility for diverse information
- Markdown support for rich formatting
- Chronological append (new info added to bottom)
- LLM summarizes on request

### 4. MCP Tools Have Read + Write Access
**Why?** Enable autonomous agent behavior
- Agent can update person context during chat
- Agent can link people to files automatically
- Delete operations require user confirmation (no MCP tool)

### 5. Cross-Reference via Junction Table
**Why?** Enable bidirectional queries
- "Which people mentioned in this file?"
- "Which files mention this person?"
- Relevance scores for ranking

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Parse accuracy | > 90% on well-structured input |
| Parse time | < 3 seconds |
| Chat context injection | < 1 second added latency |
| User effort to add person | < 30 seconds |
| Data persistence | 100% across restarts |

---

## Open Questions (Need Review)

1. **Name Collisions**: Allow duplicate names or enforce uniqueness?
   - **Recommendation**: Allow duplicates, disambiguate via context

2. **Context Format**: Plain text or markdown?
   - **Recommendation**: Markdown for rich formatting

3. **Auto-Linking**: Should agent auto-link people to files or require user approval?
   - **Recommendation**: Auto-link with confidence > 0.9, user can edit

4. **MCP Delete Permission**: Should MCP tools allow deleting people?
   - **Recommendation**: No, read/update only, user must delete manually

5. **Authentication**: V1 assumes single-user, but future multi-user?
   - **Recommendation**: Add JWT auth in V2, out of scope for V1

---

## Security Considerations

| Concern | Mitigation |
|---------|-----------|
| SQL Injection | SQLAlchemy ORM with parameterized queries |
| Prompt Injection | Validate LLM outputs before DB writes |
| Data Leakage | Don't send full database in prompts |
| XSS in UI | Sanitize inputs, use React escaping |
| Unauthorized Access | Add auth middleware (future) |

---

## File Structure

```
repo_src/backend/
├── database/
│   ├── models.py                 # Person + PersonFileLink models
│   └── connection.py             # DB setup (already configured)
├── data/
│   └── schemas.py                # Pydantic schemas (Person* classes)
├── routers/
│   └── people.py                 # NEW: People API endpoints
├── agents/
│   └── mcp_chat_agent.py         # MODIFY: Add _enrich_with_people_context()
├── mcp_server.py                 # MODIFY: Add 4 new MCP tools
└── tests/
    └── test_people.py            # NEW: Unit tests

repo_src/frontend/src/
├── App.tsx                       # MODIFY: Add People tab
├── components/
│   └── PeopleView.tsx            # NEW: People management UI
└── styles/
    └── App.css                   # MODIFY: Style people view
```

---

## Dependencies

**Backend:**
- SQLAlchemy (existing)
- FastAPI (existing)
- OpenRouter / Anthropic SDK for LLM parsing
- MCP Python SDK (existing)

**Frontend:**
- React (existing)
- TypeScript (existing)
- Fetch API (existing)

**No new external dependencies required!**

---

## API Request/Response Examples

### Parse Text Request
```json
POST /api/people/parse
{
  "text": "Met John Smith today, senior engineer at OpenAI. Email: john@openai.com. Expert in reinforcement learning.",
  "existing_context": null
}
```

### Parse Text Response
```json
{
  "name": "John Smith",
  "external_link": null,
  "contact_info": "Email: john@openai.com",
  "unstructured_context": "Senior engineer at OpenAI. Expert in reinforcement learning.",
  "confidence": 0.92,
  "existing_person_match": null,
  "suggested_action": "create"
}
```

### MCP Search People
```json
{
  "name": "search_people",
  "arguments": {
    "query": "John",
    "limit": 5
  }
}
```

**Returns:**
```json
[
  {
    "id": 42,
    "name": "John Smith",
    "contact_info": "Email: john@openai.com",
    "unstructured_context": "Senior engineer at OpenAI...",
    "relevance_score": 0.95
  }
]
```

---

## Testing Examples

### Unit Test: Parse Endpoint
```python
def test_parse_person_text():
    text = "Alice Chen, CTO at Anthropic. alice@anthropic.com"
    response = client.post("/api/people/parse", json={"text": text})

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Alice Chen"
    assert "alice@anthropic.com" in data["contact_info"]
    assert data["confidence"] > 0.8
    assert data["suggested_action"] == "create"
```

### Integration Test: Chat with People Context
```python
def test_chat_includes_people_context():
    # Setup: Create person
    create_person(name="John Smith", context="Expert in RL")

    # Test: Mention in chat
    response = client.post("/api/mcp-chat", json={
        "prompt": "What does John think about alignment?"
    })

    # Verify: Response includes context
    assert "Expert in RL" in response.json()["response"]
```

---

## Next Steps

1. **Review this architecture** and full PRD (`people_context_feature.md`)
2. **Resolve open questions** (see section above)
3. **Approve implementation plan** and timeline
4. **Begin Phase 1** with foundation work

**Estimated Timeline: 10-14 days** (single developer)

---

**END OF ARCHITECTURE QUICK REFERENCE**
