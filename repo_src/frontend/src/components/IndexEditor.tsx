import React, { useState, useEffect, useCallback } from 'react';
import './IndexEditor.css';

interface IndexEntry {
    id: number;
    file_path: string;
    description: string;
    tags: string;
}

const IndexEditor: React.FC = () => {
    const [entries, setEntries] = useState<IndexEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState('');

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/index');
            if (!response.ok) throw new Error('Failed to fetch index data');
            const data: IndexEntry[] = await response.json();
            setEntries(data);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleInputChange = (id: number, field: 'description' | 'tags', value: string) => {
        setEntries(prevEntries =>
            prevEntries.map(entry =>
                entry.id === id ? { ...entry, [field]: value } : entry
            )
        );
    };

    const handleSave = async (id: number) => {
        const entryToSave = entries.find(e => e.id === id);
        if (!entryToSave) return;

        try {
            setStatus(`Saving ${entryToSave.file_path}...`);
            const response = await fetch(`/api/index/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    description: entryToSave.description,
                    tags: entryToSave.tags
                })
            });
            if (!response.ok) throw new Error('Failed to save');
            setStatus('Saved successfully!');
        } catch (err) {
            setStatus('Error saving.');
        } finally {
            setTimeout(() => setStatus(''), 3000);
        }
    };

    const handleScan = async () => {
        try {
            setStatus('Scanning for new files...');
            const response = await fetch('/api/index/scan', { method: 'POST' });
            const data = await response.json();
            setStatus(data.message);
            await fetchData(); // Refresh data after scan
        } catch (err) {
            setStatus('Error during scan.');
        } finally {
            setTimeout(() => setStatus(''), 5000);
        }
    };

    if (loading) return <div className="index-editor-container"><p>Loading index...</p></div>;
    if (error) return <div className="index-editor-container"><p>Error: {error}</p></div>;

    return (
        <div className="index-editor-container">
            <div className="editor-toolbar">
                <span className="toolbar-status">{status}</span>
                <button onClick={handleScan}>Scan for new files</button>
            </div>
            <div className="table-container">
                {entries.length === 0 ? (
                    <div className="no-entries-message">No index entries found. Try 'Scan for new files'.</div>
                ) : (
                    <table className="index-table">
                        <thead>
                            <tr>
                                <th className="col-file">File Path</th>
                                <th className="col-desc">Description</th>
                                <th className="col-tags">Tags (comma-separated)</th>
                                <th className="col-actions">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {entries.map(entry => (
                                <tr key={entry.id}>
                                    <td>{entry.file_path}</td>
                                    <td><input type="text" value={entry.description} onChange={e => handleInputChange(entry.id, 'description', e.target.value)} /></td>
                                    <td><input type="text" value={entry.tags} onChange={e => handleInputChange(entry.id, 'tags', e.target.value)} /></td>
                                    <td><button className="action-button save" onClick={() => handleSave(entry.id)}>Save</button></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};

export default IndexEditor; 