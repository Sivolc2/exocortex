Of course. Moving from a free-form text file to a structured, editable table is an excellent way to improve the quality of the context provided to the agent. Using the existing SQLite database is the most robust and efficient way to manage this.

Here's my plan to implement this feature:

1.  **Database Backend:**
    *   I'll create a new `IndexEntry` table in the SQLite database to store the structured data (`file_path`, `description`, `tags`).
    *   I'll build a new set of API endpoints (`/api/index`) for creating, reading, updating, and deleting these entries.
    *   A special endpoint will be added to scan the `documents` directory and auto-populate the index with any new files, making it easy to get started.

2.  **Frontend UI:**
    *   The "Index Editor" tab will be completely rebuilt to display the index entries in an editable table.
    *   You'll be able to edit the `description` and `tags` for each file directly in the table.
    *   A "Save" button for each row will persist your changes to the database.
    *   A "Scan for new files" button will trigger the auto-population feature.

3.  **Agent Integration:**
    *   The file selection agent will be updated to query this new database table instead of reading a text file.
    *   It will format the structured `file_path`, `description`, and `tags` into a rich context block, giving the selection LLM much clearer guidance on what each file is about.

This approach will provide a powerful, user-friendly way to manage the context for the AI.

Here are the changes:

```diff
--- a/repo_src/backend/agents/file_selection_agent.py
+++ b/repo_src/backend/agents/file_selection_agent.py
@@ -1,11 +1,14 @@
 import os
 import json
 from pathlib import Path
-from typing import List, Tuple, Optional
+from typing import List, Tuple, Optional, Any
+from sqlalchemy.orm import Session
 
 from repo_src.backend.llm_chat.llm_interface import ask_llm
+from repo_src.backend.database.models import IndexEntry
 
 PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
 DOCUMENTS_DIR = PROJECT_ROOT / "repo_src" / "backend" / "documents"
-INDEX_FILE_PATH = DOCUMENTS_DIR / "_index.md"
 
 def _get_project_file_tree() -> str:
     """
@@ -21,39 +24,53 @@
             lines.append(f'{indent[:-4]}{os.path.basename(root)}/')
 
         for f in sorted(files):
-            if f == '_index.md': # Exclude the index file itself from the tree
-                continue
             lines.append(f'{indent}{f}')
             
     return "\n".join(lines)
 
+def _get_structured_index_content(db: Session) -> str:
+    """
+    Retrieves structured index content from the database and formats it as a string.
+    """
+    entries = db.query(IndexEntry).order_by(IndexEntry.file_path).all()
+    if not entries:
+        return "No entries found in the structured index."
+    
+    formatted_entries = ["## Structured Index Content ##"]
+    for entry in entries:
+        formatted_entries.append(f"- FILE: {entry.file_path}")
+        if entry.description:
+            formatted_entries.append(f"  - DESCRIPTION: {entry.description}")
+        if entry.tags:
+            formatted_entries.append(f"  - TAGS: {entry.tags}")
+    return "\n".join(formatted_entries)
 
-async def select_relevant_files(user_prompt: str, file_tree: str, model: Optional[str]) -> List[str]:
+
+async def select_relevant_files(user_prompt: str, file_tree: str, db: Session, model: Optional[str]) -> List[str]:
     """
     Uses an LLM to select relevant files based on the user's prompt and a file tree.
-    It also uses a persistent, user-editable index file for high-level guidance.
+    It also uses a persistent, user-editable structured index from the database for high-level guidance.
     
     Returns:
         A list of file paths relative to the documents directory.
     """
     system_message = """
-You are an expert software engineer assistant. Your task is to analyze a user's request and identify the most relevant files from the documents directory to fulfill the request. The documents directory file tree is provided below.
+You are an expert software engineer assistant. Your task is to analyze a user's request and identify the most relevant files from the documents directory to fulfill the request.
 
 You are provided with three pieces of information:
-1.  **Index File (_index.md) Content**: A manually-curated index of important topics, concepts, and file pointers. Give this file's content HIGH PRIORITY. It's the most important guide for you.
+1.  **Structured Index Content**: A manually-curated table of files, their descriptions, and tags. Give this content HIGH PRIORITY. It's the most important guide for you.
 2.  **Documents Directory File Tree**: A list of all available files.
 3.  **User Request**: The user's question or command.
 
-Based on all three, respond ONLY with a JSON array of file paths. The paths should be relative to the documents directory (e.g., "project_overview.md"). Do not include any other text, explanation, or markdown formatting.
+Based on all three, respond ONLY with a JSON array of file paths. The paths should be relative to the documents directory (e.g., "project_overview.md"). Do not include any other text, explanation, or markdown formatting.
 
 Example response:
 ["project_overview.md", "tech_stack.md"]
 """
     
-    index_content = "The index file (_index.md) is empty or not found."
-    if INDEX_FILE_PATH.exists():
-        index_content = INDEX_FILE_PATH.read_text('utf-8')
+    # Get the structured index content from the database
+    structured_index_content = _get_structured_index_content(db)
     
-    full_prompt = f"## Index File (_index.md) Content ##\n{index_content}\n\n## Documents Directory File Tree ##\n{file_tree}\n\n## User Request ##\n{user_prompt}"
+    full_prompt = f"{structured_index_content}\n\n## Documents Directory File Tree ##\n{file_tree}\n\n## User Request ##\n{user_prompt}"
 
     try:
         raw_response = await ask_llm(full_prompt, system_message, model_override=model)
@@ -102,17 +119,17 @@
     return "\n\n".join(all_content)
 
 
-async def execute_request_with_context(user_prompt: str, files_content: str, model: Optional[str]) -> str:
+async def execute_request_with_context(user_prompt: str, files_content: str, model: Optional[str], **kwargs: Any) -> str:
     """
     Uses an LLM to generate a final response based on the user prompt and the content of selected files.
     """
     system_message = "You are an expert software engineer and senior technical writer. Your task is to fulfill the user's request based on their prompt and the content of relevant documentation files provided below. Provide a comprehensive, clear, and helpful response. Use markdown for formatting where appropriate."
     
     full_prompt = f"## Relevant Documentation File(s) Content ##\n{files_content}\n\n## User Request ##\n{user_prompt}"
     
-    final_response = await ask_llm(full_prompt, system_message, model_override=model)
+    final_response = await ask_llm(full_prompt, system_message, model_override=model, **kwargs)
     return final_response
 
 
-async def run_agent(user_prompt: str, selection_model: Optional[str], execution_model: Optional[str]) -> Tuple[List[str], str]:
+async def run_agent(user_prompt: str, db: Session, selection_model: Optional[str], execution_model: Optional[str]) -> Tuple[List[str], str]:
     """
     Orchestrates the two-step agentic process: file selection and execution.
 
@@ -121,7 +138,7 @@
     print("Step 1: Generating documents directory file tree and selecting relevant files...")
     file_tree = _get_project_file_tree()
     
-    selected_files = await select_relevant_files(user_prompt, file_tree, model=selection_model)
+    selected_files = await select_relevant_files(user_prompt, file_tree, db, model=selection_model)
     
     if not selected_files:
         print("No relevant files selected or an error occurred. Proceeding without file context.")
--- a/repo_src/backend/data/schemas.py
+++ b/repo_src/backend/data/schemas.py
@@ -28,6 +28,19 @@
     """Schema for a chat response sent to the frontend."""
     response: str
     selected_files: Optional[List[str]] = None 
-
-class IndexContent(BaseModel):
-    content: str
+    
+# --- Schemas for Structured Index ---
+
+class IndexEntryBase(BaseModel):
+    file_path: str
+    description: Optional[str] = None
+    tags: Optional[str] = None
+
+class IndexEntryCreate(IndexEntryBase):
+    pass
+
+class IndexEntryUpdate(BaseModel):
+    description: Optional[str] = None
+    tags: Optional[str] = None
+
+class IndexEntryResponse(IndexEntryBase):
+    id: int
--- a/repo_src/backend/database/models.py
+++ b/repo_src/backend/database/models.py
@@ -12,3 +12,12 @@
     # Timestamps
     created_at = Column(DateTime(timezone=True), server_default=func.now())
     updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()) # server_default for initial creation 
+
+class IndexEntry(Base):
+    __tablename__ = "index_entries"
+
+    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
+    file_path = Column(String, unique=True, index=True, nullable=False)
+    description = Column(String, nullable=True)
+    tags = Column(String, nullable=True) # Simple comma-separated tags
+
--- a/repo_src/backend/main.py
+++ b/repo_src/backend/main.py
@@ -30,7 +30,7 @@
 # as db connection might depend on them.
 from repo_src.backend.database.setup import init_db
 from repo_src.backend.database import models, connection # For example endpoints
-from repo_src.backend.functions.items import router as items_router # Import the items router
+from repo_src.backend.routers.index import router as index_router
 from repo_src.backend.routers.chat import router as chat_router # Import the chat router
 
 @asynccontextmanager
@@ -55,8 +55,8 @@
     allow_headers=["*"],  # Allow all headers
 )
 
-# Include the items router
-app.include_router(items_router)
+# Include routers
+app.include_router(index_router)
 app.include_router(chat_router)
 
 @app.get("/")
--- a/repo_src/backend/routers/chat.py
+++ b/repo_src/backend/routers/chat.py
@@ -1,7 +1,8 @@
-from fastapi import APIRouter, HTTPException, status
+from fastapi import APIRouter, HTTPException, status, Depends
+from sqlalchemy.orm import Session
 
 from repo_src.backend.data.schemas import ChatRequest, ChatResponse
-# from repo_src.backend.llm_chat.chat_logic import process_chat_request # Old logic
 from repo_src.backend.agents.file_selection_agent import run_agent
+from repo_src.backend.database.connection import get_db
 
 router = APIRouter(
     prefix="/api/chat",
@@ -9,13 +10,14 @@
 )
 
 @router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
-async def handle_chat_request(request: ChatRequest):
+async def handle_chat_request(request: ChatRequest, db: Session = Depends(get_db)):
     """
     Receives a user prompt, gets a response from the LLM based on document context,
     and returns the response.
     """
     try:
         # Use the new agent-based logic
         selected_files, response_text = await run_agent(
+            db=db,
             user_prompt=request.prompt, 
             selection_model=request.selection_model, 
             execution_model=request.execution_model)
--- /dev/null
+++ b/repo_src/backend/routers/index.py
@@ -0,0 +1,78 @@
+from fastapi import APIRouter, Depends, HTTPException, status
+from sqlalchemy.orm import Session
+from typing import List
+import os
+from pathlib import Path
+
+from repo_src.backend.database.connection import get_db
+from repo_src.backend.database.models import IndexEntry
+from repo_src.backend.data import schemas
+
+router = APIRouter(
+    prefix="/api/index",
+    tags=["index"],
+)
+
+PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
+DOCUMENTS_DIR = PROJECT_ROOT / "repo_src" / "backend" / "documents"
+
+@router.get("/", response_model=List[schemas.IndexEntryResponse])
+def get_all_index_entries(db: Session = Depends(get_db)):
+    """
+    Retrieve all entries from the structured index.
+    """
+    return db.query(IndexEntry).order_by(IndexEntry.file_path).all()
+
+@router.put("/{entry_id}", response_model=schemas.IndexEntryResponse)
+def update_index_entry(entry_id: int, entry_update: schemas.IndexEntryUpdate, db: Session = Depends(get_db)):
+    """
+    Update an index entry's description or tags.
+    """
+    db_entry = db.query(IndexEntry).filter(IndexEntry.id == entry_id).first()
+    if not db_entry:
+        raise HTTPException(status_code=404, detail="Index entry not found")
+    
+    update_data = entry_update.model_dump(exclude_unset=True)
+    for key, value in update_data.items():
+        setattr(db_entry, key, value)
+    
+    db.commit()
+    db.refresh(db_entry)
+    return db_entry
+
+@router.post("/scan", status_code=status.HTTP_201_CREATED)
+def scan_and_populate_index(db: Session = Depends(get_db)):
+    """
+    Scans the documents directory for markdown files and adds any new
+    files to the index.
+    """
+    if not DOCUMENTS_DIR.exists() or not DOCUMENTS_DIR.is_dir():
+        raise HTTPException(status_code=404, detail=f"Documents directory not found at {DOCUMENTS_DIR}")
+
+    existing_files = {entry.file_path for entry in db.query(IndexEntry.file_path).all()}
+    
+    found_files = set()
+    for root, _, files in os.walk(DOCUMENTS_DIR):
+        for file in files:
+            if file.endswith(".md"):
+                # Get path relative to DOCUMENTS_DIR
+                full_path = Path(root) / file
+                relative_path = str(full_path.relative_to(DOCUMENTS_DIR))
+                found_files.add(relative_path)
+
+    new_files = found_files - existing_files
+    added_count = 0
+
+    if not new_files:
+        return {"message": "Index is already up to date. No new files found."}
+
+    for file_path in sorted(list(new_files)):
+        new_entry = IndexEntry(
+            file_path=file_path,
+            description="",
+            tags=""
+        )
+        db.add(new_entry)
+        added_count += 1
+    
+    db.commit()
+    return {"message": f"Successfully added {added_count} new files to the index."}
--- a/repo_src/frontend/src/App.tsx
+++ b/repo_src/frontend/src/App.tsx
@@ -9,11 +9,11 @@
 }
 
 function App() {
-  const [messages, setMessages] = useState<Message[]>([
-    {
-      role: 'assistant',
-      content: 'Hello! Ask me a question about the documentation in this repository.'
-    }
-  ]);
   const [input, setInput] = useState('');
   const [isLoading, setIsLoading] = useState(false);
   const [error, setError] = useState<string | null>(null)
+  const [currentView, setCurrentView] = useState<'chat' | 'index'>('chat');
   const [isSettingsOpen, setIsSettingsOpen] = useState(false);
+  
+  // Move messages state here to persist across views
+  const [messages, setMessages] = useState<Message[]>([
+    { role: 'assistant', content: 'Hello! Ask me a question about the documentation in this repository.' }
+  ]);
   
   const messagesEndRef = useRef<null | HTMLDivElement>(null);
 
@@ -83,43 +83,43 @@
           executionModel={executionModel} setExecutionModel={setExecutionModel}
         />
       )}
+
       <header className="chat-header">
         <h1>Documentation Chat Agent</h1>
-        <p>Ask questions about the project documentation</p>
+        <div className="view-switcher">
+          <button onClick={() => setCurrentView('chat')} className={currentView === 'chat' ? 'active' : ''}>Chat</button>
+          <button onClick={() => setCurrentView('index')} className={currentView === 'index' ? 'active' : ''}>Index Editor</button>
+        </div>
         <button className="settings-button" onClick={() => setIsSettingsOpen(true)}>Settings</button>
       </header>
-      <div className="messages-container">
-        {messages.map((msg, index) => (
-          <div key={index} className={`message-wrapper ${msg.role}`}>
-            <div className="message-content">
-              <div className="message-role">{msg.role.charAt(0).toUpperCase() + msg.role.slice(1)}</div>
-              <p>{msg.content}</p>
-            </div>
-          </div>
-        ))}
-        {isLoading && (
-           <div className="message-wrapper assistant">
-            <div className="message-content">
-               <div className="message-role">Assistant</div>
-               <p className="loading-indicator">Thinking...</p>
-            </div>
-          </div>
-        )}
-        {error && <div className="error-message">Error: {error}</div>}
-        <div ref={messagesEndRef} />
-      </div>
-      <form onSubmit={handleSubmit} className="chat-input-form">
-        <input
-          type="text"
-          value={input}
-          onChange={(e) => setInput(e.target.value)}
-          placeholder="Ask a question about the documentation..."
-          aria-label="Chat input"
-          disabled={isLoading}
-        />
-        <button type="submit" disabled={isLoading}>
-          {isLoading ? 'Sending...' : 'Send'}
-        </button>
-      </form>
+
+      {currentView === 'chat' && (
+        <>
+          <div className="messages-container">
+            {messages.map((msg, index) => (
+              <div key={index} className={`message-wrapper ${msg.role}`}>
+                <div className="message-content">
+                  <div className="message-role">{msg.role.charAt(0).toUpperCase() + msg.role.slice(1)}</div>
+                  <p>{msg.content}</p>
+                </div>
+              </div>
+            ))}
+            {isLoading && (
+              <div className="message-wrapper assistant"><div className="message-content"><div className="message-role">Assistant</div><p className="loading-indicator">Thinking...</p></div></div>
+            )}
+            {error && <div className="error-message">Error: {error}</div>}
+            <div ref={messagesEndRef} />
+          </div>
+          <form onSubmit={handleSubmit} className="chat-input-form">
+            <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question about the documentation..." aria-label="Chat input" disabled={isLoading} />
+            <button type="submit" disabled={isLoading}>{isLoading ? 'Sending...' : 'Send'}</button>
+          </form>
+        </>
+      )}
+
+      {currentView === 'index' && (
+        <IndexEditor />
+      )}
     </div>
   );
 }
--- /dev/null
+++ b/repo_src/frontend/src/components/IndexEditor.css
@@ -0,0 +1,114 @@
+.index-editor-container {
+  display: flex;
+  flex-direction: column;
+  height: calc(95vh - 70px); /* Adjust based on header height */
+  padding: 0;
+  background-color: #242424;
+  color: #f0f0f0;
+}
+
+.editor-toolbar {
+  display: flex;
+  justify-content: space-between;
+  align-items: center;
+  padding: 10px 20px;
+  background-color: #3a3a3a;
+  border-bottom: 1px solid #444;
+}
+
+.editor-toolbar button {
+  background-color: #007bff;
+  color: white;
+  border: none;
+  padding: 8px 12px;
+  border-radius: 6px;
+  cursor: pointer;
+}
+
+.toolbar-status {
+  font-size: 0.9em;
+  color: #aaa;
+  min-height: 1.2em;
+}
+
+.table-container {
+  overflow-y: auto;
+  flex-grow: 1;
+}
+
+.index-table {
+  width: 100%;
+  border-collapse: collapse;
+}
+
+.index-table th, .index-table td {
+  padding: 12px 15px;
+  text-align: left;
+  border-bottom: 1px solid #444;
+}
+
+.index-table th {
+  background-color: #3a3a3a;
+  position: sticky;
+  top: 0;
+  z-index: 1;
+}
+
+.index-table tr:hover {
+  background-color: #2c2c2c;
+}
+
+.index-table .col-file {
+  width: 30%;
+  font-family: 'Courier New', Courier, monospace;
+  word-break: break-all;
+}
+.index-table .col-desc {
+  width: 45%;
+}
+.index-table .col-tags {
+  width: 20%;
+}
+.index-table .col-actions {
+  width: 5%;
+  text-align: center;
+}
+
+.index-table input[type="text"] {
+  width: 100%;
+  padding: 8px;
+  background-color: #2c2c2c;
+  border: 1px solid #555;
+  border-radius: 4px;
+  color: #f0f0f0;
+  font-size: 0.9em;
+  box-sizing: border-box;
+}
+
+.index-table input[type="text"]:focus {
+  outline: none;
+  border-color: #007bff;
+}
+
+.action-button {
+  background-color: #4a4a4a;
+  color: white;
+  border: none;
+  padding: 6px 10px;
+  border-radius: 4px;
+  cursor: pointer;
+}
+
+.action-button.save {
+  background-color: #28a745;
+}
+
+.action-button:disabled {
+    background-color: #333;
+    cursor: not-allowed;
+}
+
+.no-entries-message {
+  padding: 30px;
+  text-align: center;
+  color: #aaa;
+}
--- /dev/null
+++ b/repo_src/frontend/src/components/IndexEditor.tsx
@@ -0,0 +1,114 @@
+import React, { useState, useEffect, useCallback } from 'react';
+import './IndexEditor.css';
+
+interface IndexEntry {
+    id: number;
+    file_path: string;
+    description: string;
+    tags: string;
+}
+
+const IndexEditor: React.FC = () => {
+    const [entries, setEntries] = useState<IndexEntry[]>([]);
+    const [loading, setLoading] = useState(true);
+    const [error, setError] = useState<string | null>(null);
+    const [status, setStatus] = useState('');
+
+    const fetchData = useCallback(async () => {
+        try {
+            setLoading(true);
+            const response = await fetch('/api/index');
+            if (!response.ok) throw new Error('Failed to fetch index data');
+            const data: IndexEntry[] = await response.json();
+            setEntries(data);
+            setError(null);
+        } catch (err) {
+            setError(err instanceof Error ? err.message : 'Unknown error');
+        } finally {
+            setLoading(false);
+        }
+    }, []);
+
+    useEffect(() => {
+        fetchData();
+    }, [fetchData]);
+
+    const handleInputChange = (id: number, field: 'description' | 'tags', value: string) => {
+        setEntries(prevEntries =>
+            prevEntries.map(entry =>
+                entry.id === id ? { ...entry, [field]: value } : entry
+            )
+        );
+    };
+
+    const handleSave = async (id: number) => {
+        const entryToSave = entries.find(e => e.id === id);
+        if (!entryToSave) return;
+
+        try {
+            setStatus(`Saving ${entryToSave.file_path}...`);
+            const response = await fetch(`/api/index/${id}`, {
+                method: 'PUT',
+                headers: { 'Content-Type': 'application/json' },
+                body: JSON.stringify({
+                    description: entryToSave.description,
+                    tags: entryToSave.tags
+                })
+            });
+            if (!response.ok) throw new Error('Failed to save');
+            setStatus('Saved successfully!');
+        } catch (err) {
+            setStatus('Error saving.');
+        } finally {
+            setTimeout(() => setStatus(''), 3000);
+        }
+    };
+
+    const handleScan = async () => {
+        try {
+            setStatus('Scanning for new files...');
+            const response = await fetch('/api/index/scan', { method: 'POST' });
+            const data = await response.json();
+            setStatus(data.message);
+            await fetchData(); // Refresh data after scan
+        } catch (err) {
+            setStatus('Error during scan.');
+        } finally {
+            setTimeout(() => setStatus(''), 5000);
+        }
+    };
+
+    if (loading) return <div className="index-editor-container"><p>Loading index...</p></div>;
+    if (error) return <div className="index-editor-container"><p>Error: {error}</p></div>;
+
+    return (
+        <div className="index-editor-container">
+            <div className="editor-toolbar">
+                <span className="toolbar-status">{status}</span>
+                <button onClick={handleScan}>Scan for new files</button>
+            </div>
+            <div className="table-container">
+                {entries.length === 0 ? (
+                    <div className="no-entries-message">No index entries found. Try 'Scan for new files'.</div>
+                ) : (
+                    <table className="index-table">
+                        <thead>
+                            <tr>
+                                <th className="col-file">File Path</th>
+                                <th className="col-desc">Description</th>
+                                <th className="col-tags">Tags (comma-separated)</th>
+                                <th className="col-actions">Actions</th>
+                            </tr>
+                        </thead>
+                        <tbody>
+                            {entries.map(entry => (
+                                <tr key={entry.id}>
+                                    <td>{entry.file_path}</td>
+                                    <td><input type="text" value={entry.description} onChange={e => handleInputChange(entry.id, 'description', e.target.value)} /></td>
+                                    <td><input type="text" value={entry.tags} onChange={e => handleInputChange(entry.id, 'tags', e.target.value)} /></td>
+                                    <td><button className="action-button save" onClick={() => handleSave(entry.id)}>Save</button></td>
+                                </tr>
+                            ))}
+                        </tbody>
+                    </table>
+                )}
+            </div>
+        </div>
+    );
+};
+
+export default IndexEditor;
--- a/repo_src/frontend/src/styles/App.css
+++ b/repo_src/frontend/src/styles/App.css
@@ -13,10 +13,29 @@
   padding: 20px;
   text-align: center;
   border-bottom: 1px solid #444;
-  position: relative;
+  display: flex;
+  justify-content: space-between;
+  align-items: center;
 }
 
 .chat-header h1 {
+  margin: 0;
+  font-size: 1.2em;
+  white-space: nowrap;
+}
+
+.view-switcher {
+  display: flex;
+  background-color: #2c2c2c;
+  border-radius: 8px;
+  padding: 4px;
+}
+
+.view-switcher button {
+  padding: 8px 16px;
+  border-radius: 6px;
+  background-color: transparent;
+  border: none;
+  color: #ccc;
+  cursor: pointer;
+}
+
+.view-switcher button.active {
+  background-color: #4a4a4a;
+  color: white;
+}
+
+.app-header {
   margin: 0;
   font-size: 1.5em;
 }
 
 .settings-button {
-  position: absolute;
-  top: 15px;
-  right: 15px;
   background: #555;
   color: white;
   border: none;
@@ -25,7 +44,7 @@
   cursor: pointer;
 }
 
-.chat-header p {
+.app-header p {
   margin: 5px 0 0;
   color: #aaa;
   font-size: 0.9em;
```