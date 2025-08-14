import { useState, useRef, useEffect, FormEvent } from 'react';
import './styles/App.css'
import SettingsModal from './components/SettingsModal'
import IndexEditor from './components/IndexEditor';

interface Message {
  role: 'user' | 'assistant' | 'tool';
  content: string;
}

function App() {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null)
  const [currentView, setCurrentView] = useState<'chat' | 'index'>('chat');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [transcriptionStatus, setTranscriptionStatus] = useState('');

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingIntervalRef = useRef<number | null>(null);
  
  // Move messages state here to persist across views
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hello! Ask me a question about the documentation in this repository.' }
  ]);
  
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  // State for models, initialized from localStorage or defaults
  const [selectionModel, setSelectionModel] = useState(() => localStorage.getItem('selectionModel') || 'anthropic/claude-3-haiku');
  const [executionModel, setExecutionModel] = useState(() => localStorage.getItem('executionModel') || 'anthropic/claude-3.5-sonnet');

  // Persist model choices to localStorage
  useEffect(() => { localStorage.setItem('selectionModel', selectionModel); }, [selectionModel]);
  useEffect(() => { localStorage.setItem('executionModel', executionModel); }, [executionModel]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleToggleRecording = () => {
    setIsRecording(prev => !prev);
  };

  const sendAudioChunk = async () => {
    if (audioChunksRef.current.length === 0) {
      console.log("No audio data in chunk, skipping send.");
      return;
    }
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    audioChunksRef.current = [];

    const formData = new FormData();
    formData.append('file', audioBlob, `recording-${Date.now()}.webm`);

    try {
      setTranscriptionStatus('Transcribing chunk...');
      const response = await fetch('/api/transcribe', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Transcription API call failed');
      const data = await response.json();
      setTranscriptionStatus(`Chunk saved. Preview: ${data.transcript_preview}`);
    } catch (err) {
      console.error('Error sending audio chunk:', err);
      setTranscriptionStatus('Error saving chunk.');
      setError(err instanceof Error ? err.message : 'Unknown transcription error');
    }
  };

  useEffect(() => {
    if (isRecording) {
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
          mediaRecorderRef.current = new MediaRecorder(stream);
          mediaRecorderRef.current.ondataavailable = (event) => {
            if (event.data.size > 0) audioChunksRef.current.push(event.data);
          };
          mediaRecorderRef.current.onstop = sendAudioChunk;
          mediaRecorderRef.current.start();
          setTranscriptionStatus('Recording...');
          recordingIntervalRef.current = window.setInterval(() => {
            if (mediaRecorderRef.current?.state === 'recording') {
              mediaRecorderRef.current.stop();
              mediaRecorderRef.current.start();
            }
          }, 15000); // Send a chunk every 15 seconds
        })
        .catch(err => {
          console.error('Failed to start recording:', err);
          setError('Could not access microphone.');
          setIsRecording(false);
        });
    } else {
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current);
      if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop();
      mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());
      setTranscriptionStatus(transcriptionStatus.startsWith('Chunk saved') ? transcriptionStatus : 'Recording stopped.');
    }
    return () => { // Cleanup
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current);
      mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());
    };
  }, [isRecording]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          prompt: input,
          selection_model: selectionModel,
          execution_model: executionModel,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
      }

      const data: { selected_files: string[], response: string, total_tokens?: number } = await response.json();
      
      // Add tool message if files were selected
      if (data.selected_files && data.selected_files.length > 0) {
        const filesList = data.selected_files.join('\n');
        const tokenInfo = data.total_tokens ? ` (≈${data.total_tokens.toLocaleString()} tokens)` : '';
        const toolMessage: Message = { 
          role: 'tool', 
          content: `Analyzing documents${tokenInfo}:\n\n${filesList}` 
        };
        setMessages(prev => [...prev, toolMessage]);
      }
      const assistantMessage: Message = { role: 'assistant', content: data.response };
      setMessages(prev => [...prev, assistantMessage]);

    } catch (err: unknown) {
      console.error('Failed to send message:', err);
      setError(err instanceof Error ? err.message : 'Unknown error')
      const errorMessage: Message = { role: 'assistant', content: "Sorry, I encountered an error. Please try again." };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      {isSettingsOpen && (
        <SettingsModal 
          onClose={() => setIsSettingsOpen(false)}
          selectionModel={selectionModel} setSelectionModel={setSelectionModel}
          executionModel={executionModel} setExecutionModel={setExecutionModel}
        />
      )}

      <header className="chat-header">
        <h1>Documentation Chat Agent</h1>
        <div className="view-switcher">
          <button onClick={() => setCurrentView('chat')} className={currentView === 'chat' ? 'active' : ''}>Chat</button>
          <button onClick={() => setCurrentView('index')} className={currentView === 'index' ? 'active' : ''}>Index Editor</button>
        </div>
        <div className="header-actions">
          <button onClick={handleToggleRecording} className={`record-button ${isRecording ? 'recording' : ''}`}>
            {isRecording ? 'Stop Recording' : 'Start Recording'}
          </button>
          <button className="settings-button" onClick={() => setIsSettingsOpen(true)}>Settings</button>
        </div>
      </header>

      {currentView === 'chat' && (
        <>
          <div className="messages-container">
            {messages.map((msg, index) => (
              <div key={index} className={`message-wrapper ${msg.role}`}>
                <div className="message-content">
                  <div className="message-role">{msg.role.charAt(0).toUpperCase() + msg.role.slice(1)}</div>
                  <p>{msg.content}</p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message-wrapper assistant"><div className="message-content"><div className="message-role">Assistant</div><p className="loading-indicator">Thinking...</p></div></div>
            )}
            {error && <div className="error-message">Error: {error}</div>}
            <div ref={messagesEndRef} />
          </div>
          <div className="transcription-status">{transcriptionStatus}</div>
          <form onSubmit={handleSubmit} className="chat-input-form">
            <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question about the documentation..." aria-label="Chat input" disabled={isLoading} />
            <button type="submit" disabled={isLoading}>{isLoading ? 'Sending...' : 'Send'}</button>
          </form>
        </>
      )}

      {currentView === 'index' && (
        <IndexEditor />
      )}
    </div>
  );
}

export default App
