import React from 'react';
import './SettingsModal.css';

interface SettingsModalProps {
  onClose: () => void;
  selectionModel: string;
  setSelectionModel: (model: string) => void;
  executionModel: string;
  setExecutionModel: (model: string) => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({
  onClose,
  selectionModel,
  setSelectionModel,
  executionModel,
  setExecutionModel
}) => {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Configure Models</h2>
        <p>Set which OpenRouter models to use for each step.</p>
        
        <div className="form-group">
          <label htmlFor="selection-model">File Selection Model</label>
          <input
            type="text"
            id="selection-model"
            value={selectionModel}
            onChange={(e) => setSelectionModel(e.target.value)}
            placeholder="e.g., anthropic/claude-3-haiku"
          />
          <small>A fast, cheap model is recommended for this step.</small>
        </div>

        <div className="form-group">
          <label htmlFor="execution-model">Execution/Chat Model</label>
          <input
            type="text"
            id="execution-model"
            value={executionModel}
            onChange={(e) => setExecutionModel(e.target.value)}
            placeholder="e.g., anthropic/claude-3.5-sonnet"
          />
          <small>A more powerful model is recommended for generating the final response.</small>
        </div>

        <div className="modal-actions">
          <button onClick={onClose} className="button-primary">
            Save and Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal; 