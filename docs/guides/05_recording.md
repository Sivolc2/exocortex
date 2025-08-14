I will implement the requested audio recording and transcription feature.

Here is my plan:

1.  **Backend Implementation**:
    *   I will add a new directory `repo_src/backend/transcripts/` to store the output and add it to the `.gitignore` file. I will also ignore a temporary directory for audio uploads.
    *   A new API endpoint `POST /api/transcribe` will be created. This endpoint will accept an audio file upload.
    *   I'll add a `transcription` module to handle the business logic:
        *   `interface.py`: Will contain the function to call the OpenRouter API (using `openai/whisper-1` model) to get the transcription.
        *   `logic.py`: Will contain the function to save the received transcript text. Transcripts will be appended to a daily markdown file (`transcript_YYYY-MM-DD.md`) with a timestamp for each entry.
    *   The main FastAPI app (`main.py`) will be updated to include the new transcription router.

2.  **Frontend Implementation**:
    *   In `App.tsx`, I will add a "Start/Stop Recording" button to the header.
    *   I will add the necessary state and refs (`isRecording`, `mediaRecorderRef`, etc.) to manage the recording process.
    *   Using a `useEffect` hook that responds to changes in the `isRecording` state, I will manage the entire lifecycle of the browser's `MediaRecorder` API.
    *   When recording is active, the frontend will capture audio in 15-second chunks, sending each chunk to the `/api/transcribe` endpoint for processing.
    *   I will add a status message area to provide user feedback (e.g., "Recording...", "Transcribing chunk...", "Recording stopped.").
    *   Finally, I will add CSS styles for the new button, including an animation to indicate when recording is active.

This approach creates a "continual" recording experience by processing audio in chunks, with all transcripts being saved and organized by date on the server.

Let's begin with the implementation.

```diff
--- a/.gitignore
+++ b/.gitignore
@@ -2,6 +2,7 @@
 # --- Global ---
 .DS_Store
 .env
 .env.*
 
 # --- Python ---
 __pycache__/
@@ -49,6 +50,7 @@
 # OS generated files
 Thumbs.db
 .DS_Store
 .directory
 
 # Generated files
 docs/living_context/*.md
@@ -82,6 +84,7 @@
 **/coverage/
 
 # Temporary files at any level
+temp_audio/
 **/tmp/
 **/temp/
 **/.tmp/
@@ -99,7 +102,7 @@
 docs/prd/last_response.json
 docs/prd/last_request.json
 
-repo_src/backend/documents*
+repo_src/backend/documents*
+repo_src/backend/transcripts/
 
--- a/repo_src/backend/main.py
+++ b/repo_src/backend/main.py
@@ -25,6 +25,7 @@
 from repo_src.backend.database.setup import init_db
 from repo_src.backend.database import models, connection # For example endpoints
 from repo_src.backend.routers.index import router as index_router
+from repo_src.backend.routers.transcribe import router as transcribe_router
 from repo_src.backend.routers.chat import router as chat_router # Import the chat router
 
 @asynccontextmanager
@@ -53,6 +54,7 @@
 # Include routers
 app.include_router(index_router)
 app.include_router(chat_router)
+app.include_router(transcribe_router)
 
 @app.get("/")
 async def read_root():

--- /dev/null
+++ b/repo_src/backend/routers/transcribe.py
@@ -0,0 +1,41 @@
+from fastapi import APIRouter, UploadFile, File, HTTPException
+import os
+import shutil
+from pathlib import Path
+
+from ..transcription.interface import transcribe_audio_file
+from ..transcription.logic import save_transcript
+
+router = APIRouter(
+    prefix="/api/transcribe",
+    tags=["transcription"],
+)
+
+@router.post("/")
+async def create_transcription(file: UploadFile = File(...)):
+    """
+    Receives an audio file, transcribes it, and saves the transcript.
+    """
+    if not file.content_type or not file.content_type.startswith("audio/"):
+        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an audio file.")
+
+    # Create a temporary directory to save the upload
+    temp_dir = "temp_audio"
+    os.makedirs(temp_dir, exist_ok=True)
+    temp_file_path = os.path.join(temp_dir, file.filename or "audio.tmp")
+
+    try:
+        with open(temp_file_path, "wb") as buffer:
+            shutil.copyfileobj(file.file, buffer)
+
+        transcript_text = await transcribe_audio_file(temp_file_path)
+
+        if "Error:" in transcript_text or not transcript_text.strip():
+             raise HTTPException(status_code=500, detail=f"Transcription failed: {transcript_text}")
+
+        save_transcript(transcript_text)
+
+        return {"status": "success", "transcript_preview": transcript_text[:100] + "..."}
+    finally:
+        if os.path.exists(temp_file_path):
+            os.remove(temp_file_path)

--- /dev/null
+++ b/repo_src/backend/transcription/__init__.py
@@ -0,0 +1,
+# This file makes Python treat the `transcription` directory as a package.

--- /dev/null
+++ b/repo_src/backend/transcription/interface.py
@@ -0,0 +1,33 @@
+import os
+from openai import OpenAI
+from dotenv import load_dotenv
+
+# Load environment variables from the .env file in the backend directory
+load_dotenv()
+
+OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
+# Using Whisper as a common, high-quality transcription model
+TRANSCRIPTION_MODEL = os.getenv("OPENROUTER_TRANSCRIPTION_MODEL", "openai/whisper-1")
+
+client = None
+if OPENROUTER_API_KEY:
+    client = OpenAI(
+        base_url="https://openrouter.ai/api/v1",
+        api_key=OPENROUTER_API_KEY,
+    )
+
+async def transcribe_audio_file(file_path: str) -> str:
+    """
+    Sends an audio file to OpenRouter for transcription.
+    """
+    if not client:
+        return "Error: OpenRouter client not initialized. Is OPENROUTER_API_KEY set?"
+    
+    try:
+        with open(file_path, "rb") as audio_file:
+            print(f"Transcribing {file_path} with model {TRANSCRIPTION_MODEL}...")
+            transcription = client.audio.transcriptions.create(model=TRANSCRIPTION_MODEL, file=audio_file)
+            return transcription.text
+    except Exception as e:
+        print(f"Error calling OpenRouter for transcription: {e}")
+        return f"Error: Failed to get transcription. Details: {str(e)}"

--- /dev/null
+++ b/repo_src/backend/transcription/logic.py
@@ -0,0 +1,24 @@
+import os
+from pathlib import Path
+from datetime import datetime
+
+TRANSCRIPTS_DIR = Path(__file__).parent.parent / "transcripts"
+
+def save_transcript(text: str):
+    """
+    Saves the transcribed text by appending to a daily file.
+    """
+    # Ensure the transcripts directory exists
+    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
+
+    # Create a filename based on the current date
+    today_str = datetime.now().strftime('%Y-%m-%d')
+    file_path = TRANSCRIPTS_DIR / f"transcript_{today_str}.md"
+
+    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
+
+    # Append the new transcript with a timestamp and separators
+    with open(file_path, "a", encoding="utf-8") as f:
+        f.write(f"\n\n---\n\n**Timestamp: {timestamp_str}**\n\n{text}")
+
+    print(f"Transcript appended to {file_path}")

--- a/repo_src/frontend/src/App.tsx
+++ b/repo_src/frontend/src/App.tsx
@@ -1,6 +1,6 @@
-import { useState, useRef, useEffect, FormEvent } from 'react'
+import { useState, useRef, useEffect, FormEvent } from 'react';
 import './styles/App.css'
-import SettingsModal from './components/SettingsModal';
+import SettingsModal from './components/SettingsModal'
 import IndexEditor from './components/IndexEditor';
 
 interface Message {
@@ -14,6 +14,11 @@
   const [error, setError] = useState<string | null>(null)
   const [currentView, setCurrentView] = useState<'chat' | 'index'>('chat');
   const [isSettingsOpen, setIsSettingsOpen] = useState(false);
+  const [isRecording, setIsRecording] = useState(false);
+  const [transcriptionStatus, setTranscriptionStatus] = useState('');
+
+  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
+  const audioChunksRef = useRef<Blob[]>([]);
+  const recordingIntervalRef = useRef<number | null>(null);
   
   // Move messages state here to persist across views
   const [messages, setMessages] = useState<Message[]>([
@@ -32,6 +37,70 @@
 
   useEffect(() => {
     scrollToBottom();
   }, [messages, isLoading]);
+
+  const handleToggleRecording = () => {
+    setIsRecording(prev => !prev);
+  };
+
+  const sendAudioChunk = async () => {
+    if (audioChunksRef.current.length === 0) {
+      console.log("No audio data in chunk, skipping send.");
+      return;
+    }
+    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
+    audioChunksRef.current = [];
+
+    const formData = new FormData();
+    formData.append('file', audioBlob, `recording-${Date.now()}.webm`);
+
+    try {
+      setTranscriptionStatus('Transcribing chunk...');
+      const response = await fetch('/api/transcribe', {
+        method: 'POST',
+        body: formData,
+      });
+
+      if (!response.ok) throw new Error('Transcription API call failed');
+      const data = await response.json();
+      setTranscriptionStatus(`Chunk saved. Preview: ${data.transcript_preview}`);
+    } catch (err) {
+      console.error('Error sending audio chunk:', err);
+      setTranscriptionStatus('Error saving chunk.');
+      setError(err instanceof Error ? err.message : 'Unknown transcription error');
+    }
+  };
+
+  useEffect(() => {
+    if (isRecording) {
+      navigator.mediaDevices.getUserMedia({ audio: true })
+        .then(stream => {
+          mediaRecorderRef.current = new MediaRecorder(stream);
+          mediaRecorderRef.current.ondataavailable = (event) => {
+            if (event.data.size > 0) audioChunksRef.current.push(event.data);
+          };
+          mediaRecorderRef.current.onstop = sendAudioChunk;
+          mediaRecorderRef.current.start();
+          setTranscriptionStatus('Recording...');
+          recordingIntervalRef.current = window.setInterval(() => {
+            if (mediaRecorderRef.current?.state === 'recording') {
+              mediaRecorderRef.current.stop();
+              mediaRecorderRef.current.start();
+            }
+          }, 15000); // Send a chunk every 15 seconds
+        })
+        .catch(err => {
+          console.error('Failed to start recording:', err);
+          setError('Could not access microphone.');
+          setIsRecording(false);
+        });
+    } else {
+      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current);
+      if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop();
+      mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());
+      setTranscriptionStatus(transcriptionStatus.startsWith('Chunk saved') ? transcriptionStatus : 'Recording stopped.');
+    }
+    return () => { // Cleanup
+      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current);
+      mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());
+    };
   }, [isRecording]);
 
   const handleSubmit = async (e: FormEvent) => {
@@ -95,7 +164 @@
           <button onClick={() => setCurrentView('chat')} className={currentView === 'chat' ? 'active' : ''}>Chat</button>
           <button onClick={() => setCurrentView('index')} className={currentView === 'index' ? 'active' : ''}>Index Editor</button>
         </div>
-        <button className="settings-button" onClick={() => setIsSettingsOpen(true)}>Settings</button>
+        <div className="header-actions">
+          <button onClick={handleToggleRecording} className={`record-button ${isRecording ? 'recording' : ''}`}>
+            {isRecording ? 'Stop Recording' : 'Start Recording'}
+          </button>
+          <button className="settings-button" onClick={() => setIsSettingsOpen(true)}>Settings</button>
+        </div>
       </header>
 
       {currentView === 'chat' && (
@@ -115,6 +248,7 @@
             <div ref={messagesEndRef} />
           </div>
+          <div className="transcription-status">{transcriptionStatus}</div>
           <form onSubmit={handleSubmit} className="chat-input-form">
             <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question about the documentation..." aria-label="Chat input" disabled={isLoading} />
             <button type="submit" disabled={isLoading}>{isLoading ? 'Sending...' : 'Send'}</button>

--- a/repo_src/frontend/src/styles/App.css
+++ b/repo_src/frontend/src/styles/App.css
@@ -13,6 +13,8 @@
   border-bottom: 1px solid #444;
   display: flex;
   justify-content: space-between;
   align-items: center;
+  gap: 1rem;
 }
 
 .chat-header h1 {
@@ -21,6 +23,8 @@
 }
 
 .view-switcher {
+  flex-grow: 1;
+  justify-content: center;
   display: flex;
   background-color: #2c2c2c;
   border-radius: 8px;
@@ -40,6 +44,12 @@
   color: white;
 }
 
+.header-actions {
+    display: flex;
+    align-items: center;
+    gap: 10px;
+}
+
 .settings-button {
   background: #555;
   color: white;
@@ -48,6 +58,35 @@
   border-radius: 6px;
   cursor: pointer;
 }
+.record-button {
+  background-color: #28a745;
+  color: white;
+  border: none;
+  padding: 8px 12px;
+  border-radius: 6px;
+  cursor: pointer;
+  transition: background-color 0.3s;
+}
+
+.record-button.recording {
+  background-color: #dc3545;
+  animation: pulse 1.5s infinite;
+}
+
+@keyframes pulse {
+  0% {
+    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
+  }
+  70% {
+    box-shadow: 0 0 0 10px rgba(220, 53, 69, 0);
+  }
+  100% {
+    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0);
+  }
+}
+
+
 
 .chat-header p {
   margin: 5px 0 0;
@@ -112,6 +151,14 @@
   white-space: pre-wrap; /* Allows line breaks */
   word-wrap: break-word; /* Prevents long words from overflowing */
 }
+.transcription-status {
+  padding: 0 20px 10px;
+  font-size: 0.8em;
+  color: #aaa;
+  text-align: center;
+  min-height: 1.2em;
+  background-color: #2c2c2c;
+}
 
 .chat-input-form {
   display: flex;

```
