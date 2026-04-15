import React, { useState, useEffect } from 'react';
import { useData } from '@/context/DataContext';
import './Dashboard.css';

const Dashboard = () => {
  const { datasets, selectedFolder, startJob, completedSteps, pipelineProfiles } = useData();
  const [now, setNow] = useState(Date.now());

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
    const startTime = parseDate(job.created_at);
    const lastUpdate = job.updated_at ? parseDate(job.updated_at) : now;
    const endTime = currentDataset.isProcessing ? now : lastUpdate;
    const diff = Math.max(0, endTime - startTime);
    const mins = Math.floor(diff / 60000);
    const secs = Math.floor((diff % 60000) / 1000);
    return `${mins}m ${secs}s`;
  };

  const handlePipelineAction = (profileId: string, isDone: boolean) => {
    if (isDone) {
      alert(`Opening viewer for ${profileId}... (Visualization module coming soon)`);
      // Later: navigate(`/viewer/${selectedFolder}/${profileId}`)
    } else {
      // Trigger the pipeline profile
      startJob(currentDataset.name, { profile: profileId });
    }
  };

  const isGlobalProcessing = currentDataset.isProcessing || currentDataset.isStalled;

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">{currentDataset.name}</h1>
      <p className="dashboard-meta">📷 {currentDataset.count} images detected</p>

      {/* --- LIVE PROGRESS BLOCK --- */}
      {(currentDataset.isProcessing || currentDataset.isStalled) && (
        <div className="processing-block">
          <div className="status-text" style={{ color: currentDataset.isStalled ? '#f44336' : '#2196f3' }}>
            {currentDataset.isStalled ? '⚠️ Process Stalled' : '⚙️ Processing pipeline...'}
          </div>
          <div className="step-text">{currentDataset.latestJob?.step || 'Initializing...'}</div>
          <div className="percentage-text">{formatDuration()} | {Math.round(currentDataset.latestJob?.progress || 0)}%</div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${currentDataset.latestJob?.progress || 0}%`, backgroundColor: currentDataset.isStalled ? '#f44336' : '#2196f3' }} />
          </div>
        </div>
      )}

      {/* --- pipeline PROFILES (The Actions) --- */}
      <div className="pipeline-section" style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px' }}>Available Pipelines</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '15px' }}>
          {Object.entries(pipelineProfiles).map(([id, pipeline]: [string, any]) => {
            const isDone = completedSteps.includes(pipeline.required_asset);

            return (
              <div key={id} className="pipeline-card" style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '20px',
                border: '1px solid #e0e0e0',
                borderRadius: '10px',
                backgroundColor: isDone ? '#f8fff9' : '#fff'
              }}>
                <div>
                  <h4 style={{ margin: 0, fontSize: '1.1rem' }}>{pipeline.name}</h4>
                  <p style={{ margin: '5px 0', fontSize: '0.85rem', color: '#666' }}>
                    {pipeline.description}
                  </p>
                  <p style={{ margin: '5px 0 0', fontSize: '0.85rem', color: '#666' }}>
                    Target: {pipeline.required_asset.toUpperCase()}
                  </p>
                </div>
                <button
                  disabled={isGlobalProcessing && !isDone}
                  onClick={() => handlePipelineAction(id, isDone)}
                  className={isDone ? 'btn-secondary' : 'btn-primary'}
                  style={{ minWidth: '160px' }}
                >
                  {isDone ? `View ${id}` : `Process ${id}`}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* --- COMPLETED ASSETS (Read Only Status) --- */}
      <div className="status-section" style={{ marginTop: '40px', padding: '20px', backgroundColor: '#f9f9f9', borderRadius: '10px' }}>
        <h4 style={{ marginBottom: '15px', color: '#555' }}>Dataset Technical Status</h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          {['add_photos', 'align_photos', 'depth_maps', 'model', 'texture', 'tiled_model', 'point_cloud', 'dem', 'ortho'].map(step => {
            const isDone = completedSteps.includes(step);
            return (
              <div key={step} style={{
                padding: '6px 12px',
                borderRadius: '20px',
                fontSize: '0.8rem',
                backgroundColor: isDone ? '#e8f5e9' : '#eeeeee',
                color: isDone ? '#2e7d32' : '#999',
                border: isDone ? '1px solid #c8e6c9' : '1px solid #ddd',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                {isDone ? '✅' : '⚪'} {step.replace('_', ' ')}
              </div>
            );
          })}
        </div>
      </div>

      {/* --- COMPLETED EXPORTS (Read Only Status) --- */}
      <div className="status-section" style={{ marginTop: '40px', padding: '20px', backgroundColor: '#f9f9f9', borderRadius: '10px' }}>
        <h4 style={{ marginBottom: '15px', color: '#555' }}>Dataset Export Status</h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          {['export_map_tiles', 'export_ortho_file', 'export_dem_file', 'export_model_file', 'export_point_cloud_file', 'export_report_file'].map(step => {
            const isDone = completedSteps.includes(step);
            return (
              <div key={step} style={{
                padding: '6px 12px',
                borderRadius: '20px',
                fontSize: '0.8rem',
                backgroundColor: isDone ? '#e8f5e9' : '#eeeeee',
                color: isDone ? '#2e7d32' : '#999',
                border: isDone ? '1px solid #c8e6c9' : '1px solid #ddd',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                {isDone ? '✅' : '⚪'} {step.replace('_', ' ')}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;