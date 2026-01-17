import React, { useState, useCallback, useEffect } from 'react';
import './BatchProcessing.css';
import api from '../services/api';

interface BatchItem {
  id: string;
  type: 'file' | 'folder';
  path: string;
  name: string;
}

interface BatchJob {
  id: string;
  status: string;
  progress: number;
  current: number;
  total: number;
  message: string;
  errors: string[];
}

const BatchProcessing: React.FC = () => {
  const [items, setItems] = useState<BatchItem[]>([]);
  const [inkThreshold, setInkThreshold] = useState(80);
  const [maxSide, setMaxSide] = useState(1024);
  const [outputFormat, setOutputFormat] = useState<'folder' | 'zip'>('folder');
  const [currentJob, setCurrentJob] = useState<BatchJob | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [results, setResults] = useState<any>(null);

  // Initialize API service
  useEffect(() => {
    api.initialize();
  }, []);

  // Poll for status updates
  useEffect(() => {
    if (!currentJob || currentJob.status === 'completed' || currentJob.status === 'failed') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const status = await api.getBatchStatus(currentJob.id);
        setCurrentJob(status);

        if (status.status === 'completed') {
          const results = await api.getBatchResults(currentJob.id);
          setResults(results);
        }
      } catch (error) {
        console.error('Failed to get batch status:', error);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [currentJob]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const newItems: BatchItem[] = files.map((file) => ({
      id: Math.random().toString(36),
      type: 'file',
      path: file.path || file.name,
      name: file.name,
    }));

    setItems((prev) => [...prev, ...newItems]);
  }, []);

  const handleFileSelect = async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = 'image/*';
    
    input.onchange = (e) => {
      const files = Array.from((e.target as HTMLInputElement).files || []);
      const newItems: BatchItem[] = files.map((file) => ({
        id: Math.random().toString(36),
        type: 'file',
        path: file.path || file.name,
        name: file.name,
      }));
      
      setItems((prev) => [...prev, ...newItems]);
    };
    
    input.click();
  };

  const handleFolderSelect = async () => {
    const input = document.createElement('input');
    input.type = 'file';
    // @ts-ignore - webkitdirectory is not in TypeScript types
    input.webkitdirectory = true;
    
    input.onchange = (e) => {
      const files = Array.from((e.target as HTMLInputElement).files || []);
      if (files.length > 0) {
        const folderPath = files[0].path?.split('/').slice(0, -1).join('/') || 'folder';
        const folderName = folderPath.split('/').pop() || 'Folder';
        
        const newItem: BatchItem = {
          id: Math.random().toString(36),
          type: 'folder',
          path: folderPath,
          name: `${folderName} (${files.length} files)`,
        };
        
        setItems((prev) => [...prev, newItem]);
      }
    };
    
    input.click();
  };

  const removeItem = (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const startBatch = async () => {
    if (items.length === 0) {
      alert('Please add files or folders to process');
      return;
    }

    try {
      const response = await api.createBatch({
        items: items.map((item) => ({ type: item.type, path: item.path })),
        ink_threshold: inkThreshold,
        max_side: maxSide,
        output_format: outputFormat,
      });

      const batchId = response.batch_id;
      
      setCurrentJob({
        id: batchId,
        status: 'created',
        progress: 0,
        current: 0,
        total: response.total_images,
        message: 'Starting batch...',
        errors: [],
      });

      await api.startBatch(batchId);
    } catch (error: any) {
      console.error('Failed to start batch:', error);
      alert(`Failed to start batch: ${error.message}`);
    }
  };

  const cancelBatch = async () => {
    if (!currentJob) return;

    try {
      await api.cancelBatch(currentJob.id);
      setCurrentJob({ ...currentJob, status: 'cancelled' });
    } catch (error: any) {
      console.error('Failed to cancel batch:', error);
      alert(`Failed to cancel batch: ${error.message}`);
    }
  };

  const resetBatch = () => {
    setCurrentJob(null);
    setResults(null);
    setItems([]);
  };

  return (
    <div className="batch-processing">
      {!currentJob ? (
        <>
          <div className="batch-header">
            <h2>📦 Batch Processing</h2>
            <p>Process multiple manga pages at once</p>
          </div>

          <div
            className={`drop-zone ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="drop-zone-content">
              <div className="drop-zone-icon">📁</div>
              <h3>Drag & Drop Files or Folders</h3>
              <p>or</p>
              <div className="drop-zone-buttons">
                <button onClick={handleFileSelect} className="btn-primary">
                  Choose Files
                </button>
                <button onClick={handleFolderSelect} className="btn-secondary">
                  Choose Folder
                </button>
              </div>
              <p className="drop-zone-hint">
                Supports: JPG, PNG, WEBP, BMP
              </p>
            </div>
          </div>

          {items.length > 0 && (
            <div className="items-list">
              <div className="items-list-header">
                <h3>Selected Items ({items.length})</h3>
                <button onClick={() => setItems([])} className="btn-clear">
                  Clear All
                </button>
              </div>
              <ul>
                {items.map((item) => (
                  <li key={item.id} className="item">
                    <span className="item-icon">
                      {item.type === 'folder' ? '📁' : '🖼️'}
                    </span>
                    <span className="item-name">{item.name}</span>
                    <button
                      onClick={() => removeItem(item.id)}
                      className="btn-remove"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="settings">
            <h3>Settings</h3>
            <div className="setting-group">
              <label>
                Ink Threshold: {inkThreshold}
                <input
                  type="range"
                  min="40"
                  max="120"
                  value={inkThreshold}
                  onChange={(e) => setInkThreshold(Number(e.target.value))}
                />
              </label>
            </div>

            <div className="setting-group">
              <label>
                Max Resolution: {maxSide}px
                <input
                  type="range"
                  min="512"
                  max="1536"
                  step="256"
                  value={maxSide}
                  onChange={(e) => setMaxSide(Number(e.target.value))}
                />
              </label>
            </div>

            <div className="setting-group">
              <label>
                Output Format:
                <select
                  value={outputFormat}
                  onChange={(e) =>
                    setOutputFormat(e.target.value as 'folder' | 'zip')
                  }
                >
                  <option value="folder">Folder</option>
                  <option value="zip">ZIP Archive</option>
                </select>
              </label>
            </div>
          </div>

          <button
            onClick={startBatch}
            disabled={items.length === 0}
            className="btn-start"
          >
            🚀 Start Batch Processing
          </button>
        </>
      ) : (
        <div className="batch-progress">
          <div className="progress-header">
            <h2>
              {currentJob.status === 'completed'
                ? '✅ Batch Complete'
                : currentJob.status === 'failed'
                ? '❌ Batch Failed'
                : currentJob.status === 'cancelled'
                ? '🛑 Batch Cancelled'
                : '⏳ Processing...'}
            </h2>
            <p>{currentJob.message}</p>
          </div>

          <div className="progress-bar-container">
            <div
              className="progress-bar"
              style={{ width: `${currentJob.progress}%` }}
            >
              <span className="progress-text">{currentJob.progress}%</span>
            </div>
          </div>

          <div className="progress-stats">
            <div className="stat">
              <span className="stat-label">Current:</span>
              <span className="stat-value">{currentJob.current}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Total:</span>
              <span className="stat-value">{currentJob.total}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Status:</span>
              <span className="stat-value">{currentJob.status}</span>
            </div>
          </div>

          {currentJob.errors.length > 0 && (
            <div className="errors">
              <h3>⚠️ Errors ({currentJob.errors.length})</h3>
              <ul>
                {currentJob.errors.map((error, idx) => (
                  <li key={idx}>{error}</li>
                ))}
              </ul>
            </div>
          )}

          {results && (
            <div className="results">
              <h3>📊 Results</h3>
              <div className="results-stats">
                <div className="result-stat success">
                  <span className="result-label">Successful:</span>
                  <span className="result-value">{results.successful}</span>
                </div>
                <div className="result-stat failed">
                  <span className="result-label">Failed:</span>
                  <span className="result-value">{results.failed}</span>
                </div>
              </div>
            </div>
          )}

          <div className="progress-actions">
            {currentJob.status === 'processing' && (
              <button onClick={cancelBatch} className="btn-cancel">
                🛑 Cancel
              </button>
            )}
            {(currentJob.status === 'completed' ||
              currentJob.status === 'failed' ||
              currentJob.status === 'cancelled') && (
              <button onClick={resetBatch} className="btn-primary">
                🔄 New Batch
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default BatchProcessing;
