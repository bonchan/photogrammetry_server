import { useState, useEffect } from 'react';

import { useData } from '@/context/DataContext';
import './Dashboard.css';

const Dashboard = () => {
  const { datasets, selectedFolder, startJob } = useData();

  const [now, setNow] = useState(Date.now());

  // Find the currently selected dataset
  const currentDataset = datasets.find(d => d.name === selectedFolder);
  if (!currentDataset) return null;

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (currentDataset.isProcessing) {
      timer = setInterval(() => setNow(Date.now()), 1000);
    }
    return () => clearInterval(timer);
  }, [currentDataset.isProcessing]);

  const parseDate = (dateStr: string) => {
    return new Date(dateStr.endsWith('Z') ? dateStr : dateStr + "Z").getTime();
  };

  const formatDuration = () => {
    const job = currentDataset.latestJob;
    if (!job?.created_at) return "0m 0s";

    // Parse DB timestamps
    const startTime = parseDate(job.created_at);
    const lastUpdate = parseDate(job.updated_at);

    // If processing, diff from "now". If finished, diff between DB timestamps.
    const endTime = currentDataset.isProcessing ? now : lastUpdate;

    const diff = Math.max(0, endTime - startTime);
    const mins = Math.floor(diff / 60000);
    const secs = Math.floor((diff % 60000) / 1000);

    return `${mins}m ${secs}s`;
  };

  // Safety catch: If nothing is selected, don't render anything

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">{currentDataset.name}</h1>
      <p className="dashboard-meta">📷 {currentDataset.count} images detected</p>
      {currentDataset.isCompleted && (
        <p className="dashboard-meta">⏱️ Duration: {formatDuration()}</p>
      )}

      {(currentDataset.isProcessing || currentDataset.isStalled) && (
        <div className="processing-block">
          <div
            className="status-text"
            style={{ color: currentDataset.isStalled ? 'red' : '#007bff' }}
          >
            {currentDataset.isStalled ? '⚠️ Process Stalled' : '⚙️ Processing...'}
          </div>

          <div className="step-text">
            {currentDataset.latestJob?.step || 'Initializing...'}
          </div>

          <div className="percentage-text">
            {formatDuration()} | {Math.round(currentDataset.latestJob?.progress || 0)}%
          </div>

          <div className="progress-track">
            <div
              className="progress-fill"
              style={{
                width: `${currentDataset.latestJob?.progress || 0}%`,
                backgroundColor: currentDataset.isStalled ? '#f44336' : '#4caf50'
              }}
            />
          </div>
        </div>
      )}

      <button
        disabled={currentDataset.isProcessing || currentDataset.count === 0}
        onClick={() => startJob(currentDataset.name)}
        className="btn-primary"
      >
        {currentDataset.isCompleted || currentDataset.isFailed ? 'Re-run Pipeline' : 'Start Pipeline'}
      </button>
    </div>
  );
};

export default Dashboard;