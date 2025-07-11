import React, { useState, useEffect } from 'react';
import './IndexEditor.css';

const IndexEditor: React.FC = () => {
    const [content, setContent] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [status, setStatus] = useState('');

    useEffect(() => {
        fetch('/api/index')
            .then(res => res.json())
            .then(data => {
                setContent(data.content);
                setIsLoading(false);
            })
            .catch(err => {
                console.error(err);
                setStatus('Failed to load index.');
                setIsLoading(false);
            });
    }, []);

    const handleSave = async () => {
        setStatus('Saving...');
        try {
            const response = await fetch('/api/index', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
            if (!response.ok) throw new Error('Failed to save');
            const data = await response.json();
            setStatus(data.message || 'Saved successfully!');
            setTimeout(() => setStatus(''), 3000);
        } catch (err) {
            setStatus('Error saving index.');
        }
    };

    if (isLoading) {
        return <div className="index-editor-container"><p>Loading Index...</p></div>;
    }

    return (
        <div className="index-editor-container">
            <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Enter your index content here..."
            />
            <div className="editor-actions">
                <span className="status-message">{status}</span>
                <button onClick={handleSave} disabled={status === 'Saving...'}>
                    {status === 'Saving...' ? 'Saving...' : 'Save Index'}
                </button>
            </div>
        </div>
    );
};

export default IndexEditor; 