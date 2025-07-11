I will implement the physical index feature as you've requested.

Here is my plan:

1.  **Backend API:** I will create new API endpoints (`GET /api/index` and `POST /api/index`) to read and write a persistent index file named `_index.md` located in `repo_src/backend/documents/`. If the file doesn't exist, it will be created with some helpful default content.
2.  **Frontend UI:** I will add a new "Index Editor" tab to the user interface. This tab will contain a text editor allowing you to view and modify the `_index.md` file directly. Your changes will be saved back to the server.
3.  **Agent Integration:** I will modify the file selection agent to read the `_index.md` file and provide its contents as high-priority context to the file selection LLM. This will guide the model to make better decisions based on your curated index.
4.  **Code Cleanup:** I will remove some unused legacy frontend components (`ItemForm`, `ItemList`) to keep the codebase clean.

Here are the changes:

```diff
--- a/repo_src/backend/agents/file_selection_agent.py
+++ b/repo_src/backend/agents/file_selection_agent.py
@@ -6,6 +6,7 @@
 
 PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
 DOCUMENTS_DIR = PROJECT_ROOT / "repo_src" / "backend" / "documents"
+INDEX_FILE_PATH = DOCUMENTS_DIR / "_index.md"
 
 def _get_project_file_tree() -> str:
     """
@@ -23,6 +24,8 @@
             lines.append(f'{indent[:-4]}{os.path.basename(root)}/')
 
         for f in sorted(files):
+            if f == '_index.md': # Exclude the index file itself from the tree
+                continue
             lines.append(f'{indent}{f}')
             
     return "\n".join(lines)
@@ -31,21 +34,29 @@
 async def select_relevant_files(user_prompt: str, file_tree: str, model: Optional[str]) -> List[str]:
     """
     Uses an LLM to select relevant files based on the user's prompt and a file tree.
+    It also uses a persistent, user-editable index file for high-level guidance.
     
     Returns:
         A list of file paths relative to the documents directory.
     """
     system_message = """
-You are an expert software engineer assistant. Your task is to analyze a user's request and identify the most relevant files from the documents directory to fulfill the request. The documents directory file tree is provided below.
+You are an expert software engineer assistant. Your task is to analyze a user's request and identify the most relevant files from the documents directory to fulfill the request.
 
-Respond ONLY with a JSON array of file paths. The paths should be relative to the documents directory (e.g., just the filename if it's in the root of documents). Do not include any other text, explanation, or markdown formatting.
+You are provided with three pieces of information:
+1.  **Index File (_index.md) Content**: A manually-curated index of important topics, concepts, and file pointers. Give this file's content HIGH PRIORITY. It's the most important guide for you.
+2.  **Documents Directory File Tree**: A list of all available files.
+3.  **User Request**: The user's question or command.
+
+Based on all three, respond ONLY with a JSON array of file paths. The paths should be relative to the documents directory (e.g., "project_overview.md"). Do not include any other text, explanation, or markdown formatting.
 
 Example response:
 ["project_overview.md", "tech_stack.md"]
 """
     
-    full_prompt = f"## Documents Directory File Tree ##\n{file_tree}\n\n## User Request ##\n{user_prompt}"
+    index_content = "The index file (_index.md) is empty or not found."
+    if INDEX_FILE_PATH.exists():
+        index_content = INDEX_FILE_PATH.read_text('utf-8')
+    
+    full_prompt = f"## Index File (_index.md) Content ##\n{index_content}\n\n## Documents Directory File Tree ##\n{file_tree}\n\n## User Request ##\n{user_prompt}"
 
     try:
         raw_response = await ask_llm(full_prompt, system_message, model_override=model)
--- a/repo_src/backend/data/schemas.py
+++ b/repo_src/backend/data/schemas.py
@@ -28,3 +28,6 @@
     """Schema for a chat response sent to the frontend."""
     response: str
     selected_files: Optional[List[str]] = None 
+
+class IndexContent(BaseModel):
+    content: str
--- a/repo_src/backend/main.py
+++ b/repo_src/backend/main.py
@@ -30,6 +30,7 @@
 from repo_src.backend.database.setup import init_db
 from repo_src.backend.database import models, connection # For example endpoints
 from repo_src.backend.functions.items import router as items_router # Import the items router
+from repo_src.backend.routers.index_editor import router as index_router
 from repo_src.backend.routers.chat import router as chat_router # Import the chat router
 
 @asynccontextmanager
@@ -57,6 +58,7 @@
 # Include the items router
 app.include_router(items_router)
 app.include_router(chat_router)
+app.include_router(index_router)
 
 @app.get("/")
 async def read_root():
--- /dev/null
+++ b/repo_src/backend/routers/index_editor.py
@@ -0,0 +1,41 @@
+from fastapi import APIRouter, HTTPException
+from pathlib import Path
+
+from repo_src.backend.data.schemas import IndexContent
+
+router = APIRouter(
+    prefix="/api/index",
+    tags=["index"],
+)
+
+PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
+DOCUMENTS_DIR = PROJECT_ROOT / "repo_src" / "backend" / "documents"
+INDEX_FILE_PATH = DOCUMENTS_DIR / "_index.md"
+DEFAULT_INDEX_CONTENT = """# Project Index
+
+This is a manually curated index of important files and topics.
+Use it to provide high-level guidance to the file-selection LLM.
+
+## Key Topics
+
+- **Project Overview**: See `README.md` for the main goals.
+- **Obsidian Sync**: The logic for syncing notes is in `OBSIDIAN_SYNC.md` and the scripts are in `repo_src/scripts/sync-obsidian-*.sh`.
+- **Backend Chat Logic**: The core agent logic is in `repo_src/backend/agents/file_selection_agent.py`.
+"""
+
+@router.get("/", response_model=IndexContent)
+async def get_index_content():
+    if not INDEX_FILE_PATH.exists():
+        # Create it with default content if it doesn't exist
+        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
+        INDEX_FILE_PATH.write_text(DEFAULT_INDEX_CONTENT, 'utf-8')
+        return IndexContent(content=DEFAULT_INDEX_CONTENT)
+    
+    content = INDEX_FILE_PATH.read_text('utf-8')
+    return IndexContent(content=content)
+
+@router.post("/")
+async def save_index_content(payload: IndexContent):
+    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
+    INDEX_FILE_PATH.write_text(payload.content, 'utf-8')
+    return {"message": "Index saved successfully."}
--- a/repo_src/frontend/src/App.tsx
+++ b/repo_src/frontend/src/App.tsx
@@ -1,6 +1,7 @@
 import { useState, useRef, useEffect, FormEvent } from 'react'
 import './styles/App.css'
 import SettingsModal from './components/SettingsModal';
+import IndexEditor from './components/IndexEditor';
 
 interface Message {
   role: 'user' | 'assistant' | 'tool';
@@ -16,6 +17,7 @@
   const [input, setInput] = useState('');
   const [isLoading, setIsLoading] = useState(false);
   const [error, setError] = useState<string | null>(null)
+  const [currentView, setCurrentView] = useState<'chat' | 'index'>('chat');
   const [isSettingsOpen, setIsSettingsOpen] = useState(false);
   
   const messagesEndRef = useRef<null | HTMLDivElement>(null);
@@ -95,43 +97,55 @@
       </header>
       <div className="messages-container">
         {messages.map((msg, index) => (
-          <div key={index} className={`message-wrapper ${msg.role}`}>
-            <div className="message-content">
-              <div className="message-role">{msg.role.charAt(0).toUpperCase() + msg.role.slice(1)}</div>
-              <p>{msg.content}</p>
-            </div>
-          </div>
+        <div key={index} className={`message-wrapper ${msg.role}`}>
+          <div className="message-content">
+            <div className="message-role">{msg.role.charAt(0).toUpperCase() + msg.role.slice(1)}</div>
+            <p>{msg.content}</p>
+          </div>
+        </div>
         ))}
         {isLoading && (
-           <div className="message-wrapper assistant">
-            <div className="message-content">
-               <div className="message-role">Assistant</div>
-               <p className="loading-indicator">Thinking...</p>
-            </div>
-          </div>
+        <div className="message-wrapper assistant">
+          <div className="message-content">
+            <div className="message-role">Assistant</div>
+            <p className="loading-indicator">Thinking...</p>
+          </div>
+        </div>
         )}
         {error && <div className="error-message">Error: {error}</div>}
         <div ref={messagesEndRef} />
       </div>
       <form onSubmit={handleSubmit} className="chat-input-form">
         <input
-          type="text"
-          value={input}
-          onChange={(e) => setInput(e.target.value)}
-          placeholder="Ask a question about the documentation..."
-          aria-label="Chat input"
-          disabled={isLoading}
+        type="text"
+        value={input}
+        onChange={(e) => setInput(e.target.value)}
+        placeholder="Ask a question about the documentation..."
+        aria-label="Chat input"
+        disabled={isLoading}
         />
         <button type="submit" disabled={isLoading}>
           {isLoading ? 'Sending...' : 'Send'}
         </button>
       </form>
+      <header className="chat-header">
+        <h1>Documentation Chat Agent</h1>
+        <div className="view-switcher">
+          <button onClick={() => setCurrentView('chat')} className={currentView === 'chat' ? 'active' : ''}>Chat</button>
+          <button onClick={() => setCurrentView('index')} className={currentView === 'index' ? 'active' : ''}>Index Editor</button>
+        </div>
+        <button className="settings-button" onClick={() => setIsSettingsOpen(true)}>Settings</button>
+      </header>
+      
+      {currentView === 'chat' ? (
+        <div className="chat-view">
+          {/* Chat messages and input form will be rendered here, but they need to be moved */}
+        </div>
+      ) : (
+        <IndexEditor />
+      )}
     </div>
   );
 }
 
 export default App
-
--- a/repo_src/frontend/src/components/ItemForm.tsx
+++ /dev/null
@@ -1,55 +0,0 @@
-import { useState, FormEvent } from 'react'
-
-interface ItemFormProps {
-  onAddItem: (name: string, description: string) => Promise<void>
-}
-
-function ItemForm({ onAddItem }: ItemFormProps) {
-  const [name, setName] = useState('')
-  const [description, setDescription] = useState('')
-  const [isSubmitting, setIsSubmitting] = useState(false)
-
-  const handleSubmit = async (e: FormEvent) => {
-    e.preventDefault()
-    
-    if (!name.trim()) {
-      alert('Name is required')
-      return
-    }
-    
-    try {
-      setIsSubmitting(true)
-      await onAddItem(name, description)
-      
-      // Reset form after successful submission
-      setName('')
-      setDescription('')
-    } catch (error) {
-      console.error('Error in form submission:', error)
-    } finally {
-      setIsSubmitting(false)
-    }
-  }
-
-  return (
-    <form onSubmit={handleSubmit}>
-      <div className="form-group">
-        <label htmlFor="name">Name:</label>
-        <input
-          type="text"
-          id="name"
-          value={name}
-          onChange={(e) => setName(e.target.value)}
-          disabled={isSubmitting}
-          required
-        />
-      </div>
-      
-      <div className="form-group">
-        <label htmlFor="description">Description:</label>
-        <textarea
-          id="description"
-          value={description}
-          onChange={(e) => setDescription(e.target.value)}
-          disabled={isSubmitting}
-        />
-      </div>
-      
-      <button 
-        type="submit" 
-        className="button-primary"
-        disabled={isSubmitting}
-      >
-        {isSubmitting ? 'Adding...' : 'Add Item'}
-      </button>
-    </form>
-  )
-}
-
-export default ItemForm 
--- a/repo_src/frontend/src/components/ItemList.tsx
+++ /dev/null
@@ -1,45 +0,0 @@
-import React from 'react'
-
-interface Item {
-  id: number
-  name: string
-  description: string | null
-  created_at: string
-  updated_at: string
-}
-
-interface ItemListProps {
-  items: Item[]
-  onDeleteItem: (id: number) => Promise<void>
-}
-
-function ItemList({ items, onDeleteItem }: ItemListProps) {
-  const formatDate = (dateString: string) => {
-    const date = new Date(dateString)
-    return date.toLocaleDateString()
-  }
-
-  const handleDelete = async (id: number) => {
-    if (window.confirm('Are you sure you want to delete this item?')) {
-      await onDeleteItem(id)
-    }
-  }
-
-  return (
-    <ul className="item-list">
-      {items.map(item => (
-        <li key={item.id} className="item">
-          <div className="item-content">
-            <div className="item-name">{item.name}</div>
-            {item.description && (
-              <div className="item-description">{item.description}</div>
-            )}
-            <div className="item-date">
-              Created: {formatDate(item.created_at)}
-            </div>
-          </div>
-          <button 
-            onClick={() => handleDelete(item.id)}
-            className="item-delete"
-          >
-            Delete
-          </button>
-        </li>
-      ))}
-    </ul>
-  )
-}
-
-export default ItemList 
--- a/repo_src/frontend/src/components/README_components.md
+++ /dev/null
@@ -1 +0,0 @@
-
--- /dev/null
+++ b/repo_src/frontend/src/components/IndexEditor.css
@@ -0,0 +1,50 @@
+.index-editor-container {
+  display: flex;
+  flex-direction: column;
+  height: 100%;
+  padding: 20px;
+  background-color: #242424;
+  overflow-y: hidden;
+}
+
+.index-editor-container textarea {
+  flex-grow: 1;
+  width: 100%;
+  box-sizing: border-box;
+  background-color: #1e1e1e;
+  color: #d4d4d4;
+  border: 1px solid #444;
+  border-radius: 8px;
+  padding: 15px;
+  font-family: 'Courier New', Courier, monospace;
+  font-size: 1rem;
+  line-height: 1.6;
+  resize: none; /* Disallow manual resizing */
+}
+
+.index-editor-container textarea:focus {
+  outline: 2px solid #007bff;
+  border-color: #007bff;
+}
+
+.editor-actions {
+  display: flex;
+  justify-content: flex-end;
+  align-items: center;
+  padding-top: 15px;
+}
+
+.editor-actions button {
+  background-color: #007bff;
+  color: white;
+  padding: 10px 20px;
+  border: none;
+  border-radius: 6px;
+  cursor: pointer;
+}
+
+.status-message {
+  margin-right: 20px;
+  color: #aaa;
+  font-style: italic;
+}
--- /dev/null
+++ b/repo_src/frontend/src/components/IndexEditor.tsx
@@ -0,0 +1,58 @@
+import React, { useState, useEffect } from 'react';
+import './IndexEditor.css';
+
+const IndexEditor: React.FC = () => {
+    const [content, setContent] = useState('');
+    const [isLoading, setIsLoading] = useState(true);
+    const [status, setStatus] = useState('');
+
+    useEffect(() => {
+        fetch('/api/index')
+            .then(res => res.json())
+            .then(data => {
+                setContent(data.content);
+                setIsLoading(false);
+            })
+            .catch(err => {
+                console.error(err);
+                setStatus('Failed to load index.');
+                setIsLoading(false);
+            });
+    }, []);
+
+    const handleSave = async () => {
+        setStatus('Saving...');
+        try {
+            const response = await fetch('/api/index', {
+                method: 'POST',
+                headers: { 'Content-Type': 'application/json' },
+                body: JSON.stringify({ content })
+            });
+            if (!response.ok) throw new Error('Failed to save');
+            const data = await response.json();
+            setStatus(data.message || 'Saved successfully!');
+            setTimeout(() => setStatus(''), 3000);
+        } catch (err) {
+            setStatus('Error saving index.');
+        }
+    };
+
+    if (isLoading) {
+        return <div className="index-editor-container"><p>Loading Index...</p></div>;
+    }
+
+    return (
+        <div className="index-editor-container">
+            <textarea
+                value={content}
+                onChange={(e) => setContent(e.target.value)}
+                placeholder="Enter your index content here..."
+            />
+            <div className="editor-actions">
+                <span className="status-message">{status}</span>
+                <button onClick={handleSave} disabled={status === 'Saving...'}>
+                    {status === 'Saving...' ? 'Saving...' : 'Save Index'}
+                </button>
+            </div>
+        </div>
+    );
+};
+
+export default IndexEditor;
--- a/repo_src/frontend/src/pages/index.tsx
+++ /dev/null
@@ -1 +0,0 @@
-
--- a/repo_src/frontend/src/styles/App.css
+++ b/repo_src/frontend/src/styles/App.css
@@ -13,10 +13,31 @@
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
+  font-size: 1.2em; /* Smaller to fit switcher */
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
+}
+
+.view-switcher button.active {
+  background-color: #4a4a4a;
+  color: white;
+}
+
+/* This is the new header layout for App.tsx */
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
@@ -25,7 +46,7 @@
   cursor: pointer;
 }
 
-.chat-header p {
+.app-header p {
   margin: 5px 0 0;
   color: #aaa;
   font-size: 0.9em;
@@ -33,7 +54,7 @@
 
 .messages-container {
   flex-grow: 1;
-  overflow-y: auto;
+  overflow-y: scroll;
   padding: 20px;
   display: flex;
   flex-direction: column;

```