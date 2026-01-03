This is a natural evolution for **Exocortex**. You have successfully built the **Storage** and **Retrieval** layers (Obsidian sync, Vector Search, Audio transcription).

Now you want to move to **Synthesis** and **Action**.

To bridge the gap from "Searchable Archive" to "Life Dashboard," you need to stop thinking of data just as **Documents** (Markdown) and start thinking of it as **structured entities** (Tasks, People, Metrics) hidden *inside* those documents.

Here is a conceptual framework and a concrete ETL pipeline design for your Exocortex.

---

### The Philosophy: "Lake, Warehouse, Mart"

In data engineering, we usually use a tiered approach. For a personal AI OS, it looks like this:

1.  **The Lake (Bronze Layer):** The raw, immutable history.
    *   *Current State:* Your `processed/current/` Markdown files.
    *   *Goal:* capture everything, never delete, maintain source truth.
2.  **The Warehouse (Silver Layer):** Structured, queryable entities.
    *   *Missing Piece:* Extracting "objects" from the text.
    *   *Goal:* Turn a meeting note into rows in a `tasks` table and a `contacts` table.
3.  **The Mart (Gold Layer):** Aggregated insights for Dashboards.
    *   *Missing Piece:* Pre-calculated views.
    *   *Goal:* "Weekly Productivity Score," "People I haven't spoken to in 3 months," "Project Status."

---

### The ETL Pipeline Design

Since you are using a **Functional Core** architecture, this fits perfectly. You need a pipeline that takes a **Document** and applies a **Transformation** to return **Entities**.

#### 1. The Trigger (Delta Processing)
You don't want to re-read 5,000 Obsidian notes every hour.
*   **Mechanism:** In your SQLite index, add a `last_processed_hash` column.
*   **Logic:** When the scheduler runs, query `SELECT path FROM index WHERE current_hash != last_processed_hash`. Only run the ETL on these files.

#### 2. The Transformation (The "Lens" Pipeline)
This is where the magic happens. You need to define specific "Lenses" (Extractors) that run over the text.

**Architecture:**
```python
# repo_src/backend/functions/extractors.py

def extract_tasks(content: str, source_meta: dict) -> List[Task]:
    """Pure function: takes text, returns list of Task objects using LLM."""
    pass

def extract_sentiment(content: str) -> SentimentMetric:
    """Pure function: returns -1.0 to 1.0 sentiment score."""
    pass

def extract_mentions(content: str) -> List[PersonID]:
    """Pure function: identifies people mentioned."""
    pass
```

#### 3. The Loading (Structured Storage)
Your current `app_default.db` is an *Index*. You should expand it (or add a `insights.db`) to hold **Entities**.

**Proposed SQLite Schema:**
```sql
-- For your Dashboard
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    source_file_path TEXT,
    raw_text TEXT,          -- "Buy milk"
    status TEXT,            -- "open", "done"
    due_date DATETIME,
    context_tags TEXT,      -- "home", "shopping"
    extracted_at DATETIME
);

-- For your "Social Neocortex"
CREATE TABLE interactions (
    id TEXT PRIMARY KEY,
    person_name TEXT,
    date DATETIME,
    sentiment_score FLOAT,
    summary TEXT,
    source_file_path TEXT
);

-- For your "Quantified Self"
CREATE TABLE daily_metrics (
    date DATE PRIMARY KEY,
    mood_score FLOAT,
    tasks_completed INT,
    words_written INT,
    meetings_recorded INT
);
```

---

### Implementation Strategy: The "Reflector" Job

You currently have `pnpm data:combine`. You should add `pnpm data:reflect`.

**The Workflow:**
1.  **Ingest:** Scheduler fetches Discord/Notion/Audio -> saves to Markdown (Bronze Layer).
2.  **Reflect:**
    *   Scanner finds new Markdown files.
    *   **LLM Call:** Sends the content to a cheap, fast model (e.g., Haiku, Gemini Flash, or local Mistral) with a specific schema prompt.
    *   **Prompt:** "Analyze this note. Return a JSON object containing: list of tasks found, people mentioned, and overall sentiment."
    *   **Persist:** The JSON result is parsed and inserted/updated into the SQLite tables (Silver Layer).
3.  **Visualize:** The Frontend Dashboard queries SQLite directly (via API) for the Gold Layer. "Show me tasks from all sources created in the last 24 hours."

---

### Specific Use Cases & Solutions

#### A. The "Continual Recording" to "GTD" Pipeline
*   **Input:** Audio file from "Meeting with Bob."
*   **Step 1 (Existing):** Transcribe to `2024-01-02_Meeting_Bob.md`.
*   **Step 2 (New - ETL):**
    *   Run `TaskExtractor` on the transcript.
    *   LLM identifies: "Bob said he will send the email" (Waiting For) and "I need to fix the bug" (Todo).
    *   Write to `tasks` table in SQLite.
*   **Step 3 (Dashboard):** Your frontend `TodoList` component renders rows from the SQL `tasks` table, not the raw markdown.

#### B. The "Social Neocortex"
*   **Input:** Discord logs + Emails + Transcripts.
*   **Step 1:** Run `EntityExtractor`.
*   **Step 2:** Identify unique names.
*   **Step 3:** Calculate `last_interaction_date` for every person in your network.
*   **Dashboard:** A widget showing "People drifting away" (sorted by `last_interaction_date` ASC).

#### C. Automated Workflows (The Agent)
Once the data is in SQLite, you can run logic *without* an LLM.
*   *Logic:* `SELECT * FROM tasks WHERE source='discord' AND status='open' AND created_at < DATE('now', '-3 days')`
*   *Action:* Trigger an LLM Agent: "Draft a follow-up message to the Discord channel checking on these tasks."

---

### Immediate Next Steps for You

1.  **Expand the DB Schema:**
    Modify `repo_src/backend/data/schema.py` (or equivalent) to include tables for `Tasks` and `DailySummary`.
2.  **Build the "Reflector" Pipeline:**
    Create a new pipeline script `repo_src/backend/pipelines/reflect.py`.
    *   Start simple: Just extract **Tasks** from your daily notes.
    *   Use structured output (JSON mode) from OpenRouter.
3.  **Dashboard API:**
    Add a new endpoint `/api/insights/tasks` that reads from the SQL table.
4.  **Frontend View:**
    Create a simple Kanban or List view in React that consumes that API.

This approach lets you keep your files as the "Source of Truth" (Markdown is King) while leveraging SQL for the speed and structure required for dashboards.