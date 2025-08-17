import React, { useState } from 'react';
import './TodoView.css';

type TodoStatus = 'pending' | 'scheduled' | 'in_progress' | 'done' | 'error';

interface TodoItem {
  text: string;
  status: TodoStatus;
  id: string;
  taskId?: string; // Backend task ID for tracking
  userCompleted: boolean; // User manually marked as completed
}

interface FileTokenInfo {
  file_path: string;
  token_count: number;
}

const TodoView: React.FC = () => {
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [selectedLogTask, setSelectedLogTask] = useState<string | null>(null);
  const [taskLogs, setTaskLogs] = useState<any>(null);
  const [filesUsed, setFilesUsed] = useState<FileTokenInfo[]>([]);
  const [showFilesUsed, setShowFilesUsed] = useState(false);
  const [totalTokens, setTotalTokens] = useState<number>(0);
  const [selectedGuideTask, setSelectedGuideTask] = useState<string | null>(null);
  const [guideData, setGuideData] = useState<any>(null);
  const [isLoadingGuide, setIsLoadingGuide] = useState(false);
  const [customTodoInput, setCustomTodoInput] = useState('');
  const [isRunningCustomTodo, setIsRunningCustomTodo] = useState(false);

  const parseAndSetTodos = (markdownText: string) => {
    console.log('Raw markdown text:', markdownText); // Debug log
    
    const lines = markdownText.split('\n').map(line => line.trim()).filter(line => line.length > 0);
    
    let todoItems: TodoItem[] = [];
    
    // Enhanced parsing strategies
    for (const line of lines) {
      let todoText = '';
      let isCompleted = false;
      
      // Strategy 1: Standard checkbox format (primary format from MCP agent)
      if (line.match(/^- \[[ x]\]/)) {
        todoText = line.replace(/^- \[[ x]\]\s*/, '');
        isCompleted = line.startsWith('- [x]');
      }
      // Strategy 2: Numbered list
      else if (line.match(/^\d+\./)) {
        todoText = line.replace(/^\d+\.\s*/, '');
      }
      // Strategy 3: Simple dash list
      else if (line.startsWith('- ') && !line.startsWith('- [')) {
        todoText = line.replace(/^- /, '');
      }
      // Strategy 4: Any line that looks like a task (contains action words)
      else if (line.match(/\b(add|create|update|fix|implement|write|build|test|deploy|setup|configure|install|remove|delete|refactor|improve|enhance)\b/i)) {
        todoText = line;
      }
      // Strategy 5: Lines that contain file paths or specific technical terms
      else if (line.match(/\.(js|ts|tsx|jsx|py|java|cpp|c|h|css|html|md|json|yml|yaml|xml|sql)\b/i) || 
               line.match(/\b(function|class|component|module|endpoint|route|api|database|config)\b/i)) {
        todoText = line;
      }
      
      // Clean up the todo text
      if (todoText.trim()) {
        // Remove any remaining markdown artifacts
        todoText = todoText
          .replace(/^\*\*|\*\*$/g, '') // Remove bold markers
          .replace(/^`|`$/g, '') // Remove code markers
          .replace(/^\d+\.\s*/, '') // Remove any remaining numbers
          .trim();
        
        console.log(`Parsed: "${todoText}" (completed: ${isCompleted})`); // Debug log
        todoItems.push({
          text: todoText,
          status: 'pending' as TodoStatus,
          id: `todo-${Date.now()}-${todoItems.length}`,
          userCompleted: isCompleted,
        });
      }
    }
    
    console.log('Final todos:', todoItems); // Debug log
    
    if (todoItems.length === 0) {
      // If no todos found, show the raw content for debugging
      console.log('Full markdown content for debugging:', markdownText);
      setStatusMessage(`No TODO items found. Generated content may need parsing review. Check console for details.`);
    }
    
    setTodos(todoItems);
  };

  const handleGenerateTodos = async () => {
    setIsLoading(true);
    setStatusMessage('Generating to-do list from knowledge base...');
    setTodos([]);
    // Reset files section
    setFilesUsed([]);
    setShowFilesUsed(false);
    setTotalTokens(0);
    
    try {
      const response = await fetch('/api/todos/generate', { method: 'POST' });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate to-do list');
      }
      const data = await response.json();
      console.log('Generate response:', data); // Debug log
      
      parseAndSetTodos(data.todos);
      
      // Store file information - always show files section if any files were used
      console.log('File token info:', data.file_token_info); // Debug log
      if (data.file_token_info && Array.isArray(data.file_token_info) && data.file_token_info.length > 0) {
        console.log('Setting files used:', data.file_token_info); // Debug log
        setFilesUsed(data.file_token_info);
        setTotalTokens(data.total_tokens || 0);
        setShowFilesUsed(true); // Start expanded
        setStatusMessage(`To-do list generated successfully using ${data.file_token_info.length} files (${(data.total_tokens || 0).toLocaleString()} tokens).`);
      } else {
        console.log('No file info received or invalid format'); // Debug log
        setFilesUsed([]);
        setShowFilesUsed(false);
        setStatusMessage('To-do list generated successfully.');
      }
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : 'An unknown error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  const executeAllTodos = async () => {
    const pendingTodos = todos.filter(todo => todo.status === 'pending' && !todo.userCompleted);
    if (pendingTodos.length === 0) {
      setStatusMessage('No pending todos to execute (all are either completed or user-marked as done).');
      return;
    }

    setStatusMessage(`Starting execution for ${pendingTodos.length} to-do items...`);
    
    // Mark all pending todos as scheduled (excluding user-completed ones)
    setTodos(todos.map(todo => 
      (todo.status === 'pending' && !todo.userCompleted) ? { ...todo, status: 'scheduled' as TodoStatus } : todo
    ));

    // Execute each todo individually
    for (const todo of pendingTodos) {
      await executeSingleTodo(todo.id, todo.text);
    }

    // Update the exported file with current completion states
    await updateExportedTodoList();
  };

  const executeSingleTodo = async (todoId: string, todoText: string) => {
    // Skip if user marked as completed
    const todo = todos.find(t => t.id === todoId);
    if (todo?.userCompleted) {
      setStatusMessage('Skipping user-completed todo.');
      return;
    }

    // Mark as scheduled first
    setTodos(prev => prev.map(todo => 
      todo.id === todoId ? { ...todo, status: 'scheduled' as TodoStatus } : todo
    ));

    try {
      const response = await fetch('/api/todos/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ todos: [todoText] }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to start execution');
      }

      const data = await response.json();
      const taskId = data.task_ids[0]; // Get the first task ID
      
      // Update the todo with the backend task ID
      setTodos(prev => prev.map(todo => 
        todo.id === todoId ? { ...todo, taskId: taskId } : todo
      ));

      // Start polling for status updates
      pollTaskStatus(todoId, taskId);

    } catch (error) {
      setTodos(prev => prev.map(todo => 
        todo.id === todoId ? { ...todo, status: 'error' as TodoStatus } : todo
      ));
      setStatusMessage(error instanceof Error ? error.message : 'An error occurred during execution.');
    }
  };

  const handleUserCompletionToggle = async (todoId: string) => {
    setTodos(prev => prev.map(todo => 
      todo.id === todoId ? { ...todo, userCompleted: !todo.userCompleted } : todo
    ));
    
    // Update the exported file whenever user toggles completion
    await updateExportedTodoList();
  };

  const updateExportedTodoList = async () => {
    try {
      const markdownContent = todos.map(todo => {
        const isCompleted = todo.userCompleted || todo.status === 'done';
        const checkbox = isCompleted ? '- [x]' : '- [ ]';
        return `${checkbox} ${todo.text}`;
      }).join('\n');

      await fetch('/api/todos/update-export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: markdownContent }),
      });
    } catch (error) {
      console.error('Failed to update exported todo list:', error);
    }
  };

  const pollTaskStatus = async (todoId: string, taskId: string) => {
    const poll = async () => {
      try {
        const response = await fetch(`/api/todos/status/${taskId}`);
        if (response.ok) {
          const data = await response.json();
          setTodos(prev => prev.map(todo => 
            todo.id === todoId ? { ...todo, status: data.status as TodoStatus } : todo
          ));
          
          // Continue polling if not finished
          if (data.status === 'scheduled' || data.status === 'in_progress') {
            setTimeout(poll, 1000); // Poll every second
          }
        }
      } catch (error) {
        console.error('Error polling task status:', error);
      }
    };
    
    // Start polling after a short delay
    setTimeout(poll, 500);
  };

  const viewTaskLogs = async (taskId: string) => {
    try {
      const response = await fetch(`/api/todos/logs/${taskId}`);
      if (response.ok) {
        const data = await response.json();
        setTaskLogs(data.logs);
        setSelectedLogTask(taskId);
      } else {
        setStatusMessage('Failed to fetch task logs.');
      }
    } catch (error) {
      setStatusMessage('Error fetching task logs.');
    }
  };

  const closeLogModal = () => {
    setSelectedLogTask(null);
    setTaskLogs(null);
  };

  const generateImplementationGuide = async (todoText: string) => {
    setIsLoadingGuide(true);
    setSelectedGuideTask(todoText);
    setGuideData(null);
    
    try {
      const response = await fetch('/api/todos/generate-guide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ todo_text: todoText }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate implementation guide');
      }
      
      const data = await response.json();
      setGuideData(data);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : 'Failed to generate implementation guide');
      setSelectedGuideTask(null);
    } finally {
      setIsLoadingGuide(false);
    }
  };

  const closeGuideModal = () => {
    setSelectedGuideTask(null);
    setGuideData(null);
    setIsLoadingGuide(false);
  };

  const runCustomTodo = async () => {
    if (!customTodoInput.trim()) {
      setStatusMessage('Please enter a custom TODO item.');
      return;
    }

    setIsRunningCustomTodo(true);
    
    // Create a new custom todo item
    const customTodo: TodoItem = {
      id: `custom-${Date.now()}`,
      text: customTodoInput.trim(),
      status: 'pending',
      userCompleted: false
    };

    // Add to todos list
    setTodos(prev => [customTodo, ...prev]);
    
    try {
      // Execute the custom task directly (don't generate more TODOs)
      setStatusMessage(`Executing custom task: "${customTodo.text}"`);
      await executeSingleTodo(customTodo.id, customTodo.text);
      
      // Clear the input
      setCustomTodoInput('');
      setStatusMessage(`Custom task "${customTodo.text}" has been queued for execution.`);
      
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : 'Failed to run custom TODO');
      // Remove the todo if it failed to start
      setTodos(prev => prev.filter(t => t.id !== customTodo.id));
    } finally {
      setIsRunningCustomTodo(false);
    }
  };

  const handleCustomTodoKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isRunningCustomTodo) {
      runCustomTodo();
    }
  };

  const removeTodoItem = (todoId: string) => {
    const todoToRemove = todos.find(t => t.id === todoId);
    if (!todoToRemove) return;

    // Confirm removal, especially for running tasks
    if (todoToRemove.status === 'in_progress' || todoToRemove.status === 'scheduled') {
      const confirmed = window.confirm(
        `Are you sure you want to remove this ${todoToRemove.status} task?\n\n"${todoToRemove.text}"\n\nThis will not stop the Claude instance if it's already running.`
      );
      if (!confirmed) return;
    }

    // Remove from the list
    setTodos(prev => prev.filter(todo => todo.id !== todoId));
    setStatusMessage(`Removed task: "${todoToRemove.text}"`);
  };

  const getStatusIcon = (status: TodoStatus) => {
    switch (status) {
      case 'pending':
        return '⏸️';
      case 'scheduled':
        return '📅';
      case 'in_progress':
        return '⚡';
      case 'done':
        return '✅';
      case 'error':
        return '❌';
      default:
        return '⏸️';
    }
  };

  const getStatusText = (status: TodoStatus) => {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'scheduled':
        return 'Scheduled';
      case 'in_progress':
        return 'In Progress';
      case 'done':
        return 'Done';
      case 'error':
        return 'Error';
      default:
        return 'Pending';
    }
  };

  const pendingCount = todos.filter(t => t.status === 'pending' && !t.userCompleted).length;
  const inProgressCount = todos.filter(t => t.status === 'in_progress').length;

  return (
    <div className="todo-view-container">
      <div className="custom-todo-section">
        <h3>Custom TODO Runner</h3>
        <div className="custom-todo-input-row">
          <input
            type="text"
            value={customTodoInput}
            onChange={(e) => setCustomTodoInput(e.target.value)}
            onKeyPress={handleCustomTodoKeyPress}
            placeholder="Enter a custom task to run (e.g., 'Update the README file', 'Fix the login bug', 'Add dark mode toggle')"
            className="custom-todo-input"
            disabled={isRunningCustomTodo}
          />
          <button
            onClick={runCustomTodo}
            disabled={!customTodoInput.trim() || isRunningCustomTodo}
            className="custom-todo-run-button"
          >
            {isRunningCustomTodo ? 'Running...' : 'Run'}
          </button>
        </div>
        <div className="custom-todo-help">
          This will: Execute the custom task directly → Track status → Provide execution logs
        </div>
      </div>

      <div className="todo-toolbar">
        <span className="status-message">{statusMessage}</span>
        <div className="toolbar-buttons">
          <button 
            onClick={executeAllTodos} 
            disabled={pendingCount === 0 || inProgressCount > 0}
            className="execute-button"
          >
            Execute All ({pendingCount})
          </button>
          <button onClick={handleGenerateTodos} disabled={isLoading}>
            {isLoading ? 'Generating...' : 'Generate To-Do List'}
          </button>
        </div>
      </div>

      {filesUsed.length > 0 && (
        <div className="files-used-section">
          <div className="files-used-header" onClick={() => setShowFilesUsed(!showFilesUsed)}>
            <h3>Files Used for Generation ({filesUsed.length} files, {totalTokens.toLocaleString()} tokens)</h3>
            <span className="toggle-arrow">{showFilesUsed ? '▼' : '▶'}</span>
          </div>
          {showFilesUsed && (
            <div className="files-used-list">
              {filesUsed.map((file, index) => (
                <div key={index} className="file-used-item">
                  <span className="file-path">{file.file_path}</span>
                  <span className="file-tokens">{file.token_count.toLocaleString()} tokens</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="todo-list-container">
        {isLoading && todos.length === 0 ? (
          <div className="loading-spinner"></div>
        ) : todos.length > 0 ? (
          <ul className="todo-list">
            {todos.map((todo) => (
              <li key={todo.id} className={`todo-item status-${todo.status} ${todo.userCompleted ? 'user-completed' : ''}`}>
                <input
                  type="checkbox"
                  id={`user-complete-${todo.id}`}
                  checked={todo.userCompleted}
                  onChange={() => handleUserCompletionToggle(todo.id)}
                  className="user-completion-checkbox"
                  title="Mark as already completed by you"
                />
                <div className="todo-status">
                  <span className="status-icon">{getStatusIcon(todo.status)}</span>
                  <span className="status-text">{getStatusText(todo.status)}</span>
                </div>
                <div className="todo-text">{todo.text}</div>
                {todo.status === 'pending' && !todo.userCompleted && (
                  <button 
                    className="execute-single-button"
                    onClick={() => executeSingleTodo(todo.id, todo.text)}
                    disabled={inProgressCount > 0}
                  >
                    Execute
                  </button>
                )}
                {todo.userCompleted && (
                  <span className="user-completed-badge">User Completed</span>
                )}
                <div className="todo-actions">
                  <button 
                    className="guide-button"
                    onClick={() => generateImplementationGuide(todo.text)}
                    disabled={isLoadingGuide}
                  >
                    {isLoadingGuide && selectedGuideTask === todo.text ? 'Generating...' : 'Guide'}
                  </button>
                  {todo.taskId && (todo.status === 'done' || todo.status === 'error') && (
                    <button 
                      className="log-button"
                      onClick={() => viewTaskLogs(todo.taskId!)}
                    >
                      View Logs
                    </button>
                  )}
                  <button 
                    className="remove-button"
                    onClick={() => removeTodoItem(todo.id)}
                    title="Remove this TODO item"
                  >
                    ✕
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="placeholder-message">
            <p>Click "Generate To-Do List" to find actionable items from your knowledge base.</p>
          </div>
        )}
      </div>

      {selectedLogTask && taskLogs && (
        <div className="log-modal" onClick={closeLogModal}>
          <div className="log-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="log-modal-header">
              <h3>Task Execution Logs</h3>
              <button className="log-close-button" onClick={closeLogModal}>
                Close
              </button>
            </div>
            
            <div className="log-section">
              <h4>Standard Output:</h4>
              <div className="log-content">
                {taskLogs.stdout || 'No output'}
              </div>
            </div>
            
            <div className="log-section">
              <h4>Standard Error:</h4>
              <div className="log-content">
                {taskLogs.stderr || 'No errors'}
              </div>
            </div>
            
            <div className="log-section">
              <h4>Return Code:</h4>
              <div className="log-content">
                {taskLogs.return_code}
              </div>
            </div>
          </div>
        </div>
      )}

      {selectedGuideTask && (
        <div className="guide-modal" onClick={closeGuideModal}>
          <div className="guide-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="guide-modal-header">
              <h3>Implementation Guide</h3>
              <button className="guide-close-button" onClick={closeGuideModal}>
                Close
              </button>
            </div>
            
            <div className="guide-task-title">
              <strong>Task:</strong> {selectedGuideTask}
            </div>

            {isLoadingGuide ? (
              <div className="guide-loading">
                <div className="loading-spinner"></div>
                <p>Generating comprehensive implementation guide from your knowledge base...</p>
              </div>
            ) : guideData ? (
              <div className="guide-content">
                <div className="guide-files-used">
                  <h4>Knowledge Sources ({guideData.file_token_info?.length || 0} files, {(guideData.total_tokens || 0).toLocaleString()} tokens):</h4>
                  <div className="guide-files-list">
                    {guideData.file_token_info?.map((file: FileTokenInfo, index: number) => (
                      <span key={index} className="guide-file-tag">
                        {file.file_path.split('/').pop()} ({file.token_count.toLocaleString()})
                      </span>
                    ))}
                  </div>
                </div>
                
                <div className="guide-text">
                  <div dangerouslySetInnerHTML={{ 
                    __html: guideData.guide
                      .replace(/\n\n/g, '<br><br>')
                      .replace(/\n/g, '<br>')
                      .replace(/## (.*?)(<br>|$)/g, '<h3 class="guide-section-header">$1</h3>')
                      .replace(/### (.*?)(<br>|$)/g, '<h4 class="guide-subsection-header">$1</h4>')
                      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                      .replace(/`([^`]+)`/g, '<code>$1</code>')
                      .replace(/- (.*?)(<br>|$)/g, '<li>$1</li>')
                      .replace(/(\d+)\. (.*?)(<br>|$)/g, '<div class="guide-step"><span class="step-number">$1</span>$2</div>')
                  }} />
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};

export default TodoView;