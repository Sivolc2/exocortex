I will implement the requested features. Here is my plan:

I'll start with the backend changes to support the new two-step, model-configurable agentic workflow. Then I will update the frontend to include the model configuration UI and to display the agent's intermediate steps.

### Backend Changes

1.  **New Agent Logic**: I will create a new file `repo_src/backend/agents/file_selection_agent.py` to house the new two-step process (file selection, then execution). This will keep the new, more complex logic separate from the existing simple chat functionality.
2.  **Updated Schemas**: I'll modify `repo_src/backend/data/schemas.py`.
    *   The `ChatRequest` schema will be updated to include optional `selection_model` and `execution_model` fields.
    *   The `ChatResponse` schema will be updated to include a `selected_files` list, so the frontend can show which files the agent chose to analyze.
3.  **Modified Router**: I will update the `/api/chat` endpoint in `repo_src/backend/routers/chat.py` to use the new agent logic, passing the models from the request and returning the structured response.
4.  **Flexible LLM Interface**: I will ensure the `ask_llm` function in `repo_src/backend/llm_chat/llm_interface.py` can accept a `model_override` parameter, allowing the agent to use different models for the selection and execution steps.

### Frontend Changes

1.  **New Components**: I'll create a new `SettingsModal.tsx` component to provide the UI for model configuration.
2.  **UI for Model Configuration**: In `repo_src/frontend/src/App.tsx`, I will add:
    *   A "Settings" button to open the configuration modal.
    *   State management (`useState`) for the selection and execution model names, with their values persisted to `localStorage`.
3.  **Displaying Agent Steps**: I will update `App.tsx` to handle the new structured response from the backend.
    *   The `Message` interface will be updated to support a new `tool` role.
    *   When a response is received, the app will first display a `tool` message showing the files the agent selected, and then display the final `assistant` message. This provides transparency into the agent's process.
4.  **Styling**: I'll add the necessary CSS to `repo_src/frontend/src/styles/App.css` to style the new settings button, modal, and `tool` messages.

I will now proceed with these changes.

```diff
--- a/repo_src/backend/data/schemas.py
+++ b/repo_src/backend/data/schemas.py
@@ -19,8 +19,10 @@
 
 class ChatRequest(BaseModel):
     """Schema for a chat request from the frontend."""
-    prompt: str
+    prompt: str
+    selection_model: Optional[str] = None
+    execution_model: Optional[str] = None
 
 class ChatResponse(BaseModel):
     """Schema for a chat response sent to the frontend."""
-    response: str 
+    response: str
+    selected_files: Optional[List[str]] = None
--- a/repo_src/backend/llm_chat/llm_interface.py
+++ b/repo_src/backend/llm_chat/llm_interface.py
@@ -21,12 +21,13 @@
         api_key=OPENROUTER_API_KEY,
     )
 
-async def ask_llm(prompt_text: str, system_message: str = "You are a helpful assistant.") -> str:
+async def ask_llm(prompt_text: str, system_message: str = "You are a helpful assistant.", model_override: Optional[str] = None) -> str:
     """
     Sends a prompt to the configured LLM via OpenRouter and returns the response.
     """
     if not client:
         return "Error: OpenRouter client not initialized. Is OPENROUTER_API_KEY set in repo_src/backend/.env?"
     
+    model_to_use = model_override or DEFAULT_MODEL_NAME
     try:
         messages = [
             {"role": "system", "content": system_message},
@@ -34,7 +35,7 @@
         ]
         
         response = client.chat.completions.create(
-            model=DEFAULT_MODEL_NAME,
+            model=model_to_use,
             messages=messages,
             temperature=0.2, # Lower temperature for more factual answers based on context
             max_tokens=2048,
@@ -43,5 +44,5 @@
         
         return response.choices[0].message.content
     except Exception as e:
-        print(f"Error calling OpenRouter API with model {DEFAULT_MODEL_NAME}: {e}")
+        print(f"Error calling OpenRouter API with model {model_to_use}: {e}")
         return f"Error: Failed to get response from LLM. Details: {str(e)}"
--- a/repo_src/backend/routers/chat.py
+++ b/repo_src/backend/routers/chat.py
@@ -1,8 +1,8 @@
 from fastapi import APIRouter, HTTPException, status
 
 from repo_src.backend.data.schemas import ChatRequest, ChatResponse
-from repo_src.backend.llm_chat.chat_logic import process_chat_request
-
+# from repo_src.backend.llm_chat.chat_logic import process_chat_request # Old logic
+from repo_src.backend.agents.file_selection_agent import run_agent
 router = APIRouter(
     prefix="/api/chat",
     tags=["chat"],
@@ -15,10 +15,12 @@
     and returns the response.
     """
     try:
-        llm_response = await process_chat_request(request.prompt)
-        return ChatResponse(response=llm_response)
+        # Use the new agent-based logic
+        selected_files, response_text = await run_agent(
+            user_prompt=request.prompt, 
+            selection_model=request.selection_model, 
+            execution_model=request.execution_model)
+        return ChatResponse(response=response_text, selected_files=selected_files)
     except Exception as e:
         print(f"Error processing chat request: {e}")
         raise HTTPException(status_code=500, detail="An error occurred while processing your request.") 
--- /dev/null
+++ b/repo_src/backend/agents/file_selection_agent.py
@@ -0,0 +1,137 @@
+import os
+import json
+from pathlib import Path
+from typing import List, Tuple, Optional
+
+from repo_src.backend.llm_chat.llm_interface import ask_llm
+
+PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
+
+def _get_project_file_tree() -> str:
+    """
+    Generates a string representation of the project's file tree, ignoring common temporary/build directories.
+    """
+    lines = []
+    ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'dist', 'build', '.DS_Store', '.pytest_cache', '.mypy_cache', '.idea', '.vscode'}
+    
+    for root, dirs, files in os.walk(PROJECT_ROOT):
+        # Modify dirs in-place to prune the search
+        dirs[:] = [d for d in dirs if d not in ignore_dirs]
+        
+        level = root.replace(str(PROJECT_ROOT), '').count(os.sep)
+        indent = ' ' * 4 * level
+        
+        # Prepend a marker for the directory itself if it's not the root
+        if root != str(PROJECT_ROOT):
+            lines.append(f'{indent[:-4]}{os.path.basename(root)}/')
+
+        for f in sorted(files):
+            lines.append(f'{indent}{f}')
+            
+    return "\n".join(lines)
+
+
+async def select_relevant_files(user_prompt: str, file_tree: str, model: Optional[str]) -> List[str]:
+    """
+    Uses an LLM to select relevant files based on the user's prompt and a file tree.
+    
+    Returns:
+        A list of file paths relative to the project root.
+    """
+    system_message = """
+You are an expert software engineer assistant. Your task is to analyze a user's request and identify the most relevant files from the repository to fulfill the request. The repository file tree is provided below.
+
+Respond ONLY with a JSON array of file paths. The paths should be relative to the project root. Do not include any other text, explanation, or markdown formatting.
+
+Example response:
+["repo_src/frontend/src/App.tsx", "repo_src/backend/routers/chat.py"]
+"""
+    
+    full_prompt = f"## Repository File Tree ##\n{file_tree}\n\n## User Request ##\n{user_prompt}"
+
+    try:
+        raw_response = await ask_llm(full_prompt, system_message, model_override=model)
+        
+        # Clean up response: remove markdown code block fences
+        cleaned_response = raw_response.strip().replace('```json', '').replace('```', '').strip()
+        
+        selected_files = json.loads(cleaned_response)
+        if isinstance(selected_files, list):
+            # Ensure all paths are valid and exist
+            valid_files = [f for f in selected_files if (PROJECT_ROOT / f).is_file()]
+            return valid_files
+        return []
+    except (json.JSONDecodeError, TypeError) as e:
+        print(f"Error decoding file selection response: {e}\nRaw response: {raw_response}")
+        # Fallback or error handling can be improved here
+        return []
+    except Exception as e:
+        print(f"An unexpected error occurred during file selection: {e}")
+        return []
+
+
+def _read_files_content(file_paths: List[str]) -> str:
+    """
+    Reads the content of the given files and concatenates them into a single string.
+    """
+    all_content = []
+    for file_path in file_paths:
+        try:
+            full_path = PROJECT_ROOT / file_path
+            content = full_path.read_text('utf-8')
+            all_content.append(f"--- START OF FILE: {file_path} ---\n{content}\n--- END OF FILE: {file_path} ---\n")
+        except FileNotFoundError:
+            print(f"Warning: File selected by LLM not found: {file_path}")
+        except Exception as e:
+            print(f"Error reading file {file_path}: {e}")
+    
+    return "\n\n".join(all_content)
+
+
+async def execute_request_with_context(user_prompt: str, files_content: str, model: Optional[str]) -> str:
+    """
+    Uses an LLM to generate a final response based on the user prompt and the content of selected files.
+    """
+    system_message = "You are an expert software engineer and senior technical writer. Your task is to fulfill the user's request based on their prompt and the content of relevant repository files provided below. Provide a comprehensive, clear, and helpful response. Use markdown for formatting where appropriate."
+    
+    full_prompt = f"## Relevant File(s) Content ##\n{files_content}\n\n## User Request ##\n{user_prompt}"
+    
+    final_response = await ask_llm(full_prompt, system_message, model_override=model)
+    return final_response
+
+
+async def run_agent(user_prompt: str, selection_model: Optional[str], execution_model: Optional[str]) -> Tuple[List[str], str]:
+    """
+    Orchestrates the two-step agentic process: file selection and execution.
+
+    Returns:
+        A tuple containing the list of selected files and the final response string.
+    """
+    print("Step 1: Generating file tree and selecting relevant files...")
+    file_tree = _get_project_file_tree()
+    
+    selected_files = await select_relevant_files(user_prompt, file_tree, model=selection_model)
+    
+    if not selected_files:
+        print("No relevant files selected or an error occurred. Proceeding without file context.")
+        final_response = await execute_request_with_context(user_prompt, "No files were selected as context.", model=execution_model)
+        return [], final_response
+
+    print(f"Selected files: {selected_files}")
+
+    print("Step 2: Reading file contents and executing final request...")
+    files_content = _read_files_content(selected_files)
+    
+    if not files_content:
+        print("Could not read content from any selected files. Proceeding without file context.")
+        final_response = await execute_request_with_context(user_prompt, "The selected files could not be read.", model=execution_model)
+        return selected_files, final_response
+
+    final_response = await execute_request_with_context(user_prompt, files_content, model=execution_model)
+    
+    print("Agent execution complete.")
+    return selected_files, final_response
--- a/repo_src/frontend/src/App.tsx
+++ b/repo_src/frontend/src/App.tsx
@@ -1,10 +1,12 @@
 import { useState, useRef, useEffect, FormEvent } from 'react'
 import './styles/App.css'
+import SettingsModal from './components/SettingsModal';
 
 interface Message {
-  role: 'user' | 'assistant';
+  role: 'user' | 'assistant' | 'tool';
   content: string;
 }
 
 function App() {
   const [messages, setMessages] = useState<Message[]>([
@@ -16,8 +18,17 @@
   const [input, setInput] = useState('');
   const [isLoading, setIsLoading] = useState(false);
   const [error, setError] = useState<string | null>(null)
+  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
   
   const messagesEndRef = useRef<null | HTMLDivElement>(null);
+
+  // State for models, initialized from localStorage or defaults
+  const [selectionModel, setSelectionModel] = useState(() => localStorage.getItem('selectionModel') || 'anthropic/claude-3-haiku-20240307');
+  const [executionModel, setExecutionModel] = useState(() => localStorage.getItem('executionModel') || 'anthropic/claude-3.5-sonnet');
+
+  // Persist model choices to localStorage
+  useEffect(() => { localStorage.setItem('selectionModel', selectionModel); }, [selectionModel]);
+  useEffect(() => { localStorage.setItem('executionModel', executionModel); }, [executionModel]);
 
   const scrollToBottom = () => {
     messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
@@ -39,17 +50,26 @@
         headers: {
           'Content-Type': 'application/json',
         },
-        body: JSON.stringify({ prompt: input }),
+        body: JSON.stringify({ 
+          prompt: input,
+          selection_model: selectionModel,
+          execution_model: executionModel,
+        }),
       });
 
       if (!response.ok) {
         const errorData = await response.json();
         throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
       }
 
-      const data = await response.json();
-      const assistantMessage: Message = { role: 'assistant', content: data.response };
-      setMessages(prev => [...prev, assistantMessage]);
+      const data: { selected_files: string[], response: string } = await response.json();
+      
+      // Add tool message if files were selected
+      if (data.selected_files && data.selected_files.length > 0) {
+        const toolMessage: Message = { role: 'tool', content: `Analyzing files: ${data.selected_files.join(', ')}` };
+        setMessages(prev => [...prev, toolMessage]);
+      }
+      const assistantMessage: Message = { role: 'assistant', content: data.response };
+      setMessages(prev => [...prev, assistantMessage]);
 
     } catch (err: unknown) {
       console.error('Failed to send message:', err);
@@ -62,10 +82,14 @@
 
   return (
     <div className="chat-container">
+      {isSettingsOpen && (
+        <SettingsModal 
+          onClose={() => setIsSettingsOpen(false)}
+          selectionModel={selectionModel} setSelectionModel={setSelectionModel}
+          executionModel={executionModel} setExecutionModel={setExecutionModel}
+        />
+      )}
       <header className="chat-header">
-        <h1>Chat with your Docs</h1>
-        <p>Using OpenRouter and a local knowledge base</p>
+        <h1>File Selection Agent</h1>
+        <p>Using OpenRouter Models</p>
+        <button className="settings-button" onClick={() => setIsSettingsOpen(true)}>Settings</button>
       </header>
       <div className="messages-container">
         {messages.map((msg, index) => (
           <div key={index} className={`message-wrapper ${msg.role}`}>
             <div className="message-content">
-              <div className="message-role">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
+              <div className="message-role">{msg.role.charAt(0).toUpperCase() + msg.role.slice(1)}</div>
               <p>{msg.content}</p>
             </div>
           </div>
@@ -96,5 +120,4 @@
 }
 
 export default App
-
+ 
--- /dev/null
+++ b/repo_src/frontend/src/components/SettingsModal.tsx
@@ -0,0 +1,59 @@
+import React from 'react';
+import './SettingsModal.css';
+
+interface SettingsModalProps {
+  onClose: () => void;
+  selectionModel: string;
+  setSelectionModel: (model: string) => void;
+  executionModel: string;
+  setExecutionModel: (model: string) => void;
+}
+
+const SettingsModal: React.FC<SettingsModalProps> = ({
+  onClose,
+  selectionModel,
+  setSelectionModel,
+  executionModel,
+  setExecutionModel
+}) => {
+  return (
+    <div className="modal-overlay" onClick={onClose}>
+      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
+        <h2>Configure Models</h2>
+        <p>Set which OpenRouter models to use for each step.</p>
+        
+        <div className="form-group">
+          <label htmlFor="selection-model">File Selection Model</label>
+          <input
+            type="text"
+            id="selection-model"
+            value={selectionModel}
+            onChange={(e) => setSelectionModel(e.target.value)}
+            placeholder="e.g., anthropic/claude-3-haiku-20240307"
+          />
+          <small>A fast, cheap model is recommended for this step.</small>
+        </div>
+
+        <div className="form-group">
+          <label htmlFor="execution-model">Execution/Chat Model</label>
+          <input
+            type="text"
+            id="execution-model"
+            value={executionModel}
+            onChange={(e) => setExecutionModel(e.target.value)}
+            placeholder="e.g., anthropic/claude-3.5-sonnet"
+          />
+          <small>A more powerful model is recommended for generating the final response.</small>
+        </div>
+
+        <div className="modal-actions">
+          <button onClick={onClose} className="button-primary">
+            Save and Close
+          </button>
+        </div>
+      </div>
+    </div>
+  );
+};
+
+export default SettingsModal;
--- a/repo_src/frontend/src/styles/App.css
+++ b/repo_src/frontend/src/styles/App.css
@@ -14,14 +14,26 @@
   background-color: #3a3a3a;
   padding: 20px;
   text-align: center;
   border-bottom: 1px solid #444;
+  position: relative;
 }
 
 .chat-header h1 {
   margin: 0;
   font-size: 1.5em;
+}
+
+.settings-button {
+  position: absolute;
+  top: 15px;
+  right: 15px;
+  background: #555;
+  color: white;
+  border: none;
+  padding: 8px 12px;
+  border-radius: 6px;
+  cursor: pointer;
 }
 
 .chat-header p {
   margin: 5px 0 0;
@@ -58,6 +70,11 @@
   background-color: #4a4a4a;
   border-bottom-left-radius: 4px;
 }
+.message-wrapper.tool .message-content {
+  background-color: #3d3d3d;
+  border: 1px solid #5a5a5a;
+  color: #ccc;
+}
 
 .message-role {
   font-weight: bold;
@@ -69,6 +86,10 @@
 .message-wrapper.user .message-role {
   text-align: right;
   color: #e0e0e0;
+}
+
+.message-wrapper.tool .message-role {
+  color: #a0e0ff;
 }
 
 .message-content p {
--- /dev/null
+++ b/repo_src/frontend/src/components/SettingsModal.css
@@ -0,0 +1,71 @@
+.modal-overlay {
+  position: fixed;
+  top: 0;
+  left: 0;
+  right: 0;
+  bottom: 0;
+  background-color: rgba(0, 0, 0, 0.7);
+  display: flex;
+  justify-content: center;
+  align-items: center;
+  z-index: 1000;
+}
+
+.modal-content {
+  background-color: #3a3a3a;
+  padding: 2rem;
+  border-radius: 12px;
+  width: 90%;
+  max-width: 500px;
+  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
+  border: 1px solid #555;
+  color: #f0f0f0;
+}
+
+.modal-content h2 {
+  margin-top: 0;
+  border-bottom: 1px solid #555;
+  padding-bottom: 1rem;
+}
+
+.form-group {
+  margin-bottom: 1.5rem;
+}
+
+.form-group label {
+  display: block;
+  margin-bottom: 0.5rem;
+  font-weight: bold;
+  color: #ccc;
+}
+
+.form-group input[type="text"] {
+  width: 100%;
+  padding: 10px;
+  background-color: #2c2c2c;
+  border: 1px solid #555;
+  border-radius: 6px;
+  color: #f0f0f0;
+  font-size: 1rem;
+  box-sizing: border-box;
+}
+
+.form-group small {
+  display: block;
+  margin-top: 0.5rem;
+  color: #aaa;
+}
+
+.modal-actions {
+  text-align: right;
+  margin-top: 2rem;
+}
+
+.button-primary {
+  background-color: #007bff;
+  color: white;
+  padding: 10px 20px;
+  border: none;
+  border-radius: 6px;
+  cursor: pointer;
+}

```