import React, { useState, useEffect } from 'react';
import { useData } from '@/context/DataContext';
import './Dashboard.css';

const Dashboard = () => {
  const { datasets, selectedFolder, startJob, completedSteps, engineList } = useData();
  const [selectedEngineId, setSelectedEngineId] = useState('');

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

  useEffect(() => {
    if (selectedEngineId == '') {
      if (engineList.length > 0) {
        setSelectedEngineId(engineList[0].id);
      }
    }

  }, [engineList]);

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

  const handlePipelineAction = (pipeline: any, isDone: boolean) => {
    if (isDone) {
      alert(`Opening viewer for ${pipeline.id}... (Visualization module coming soon)`);
      // Later: navigate(`/viewer/${selectedFolder}/${profileId}`)
    } else {
      // Trigger the pipeline profile
      console.log('handlePipelineAction', pipeline, selectedEngineId)
      startJob(currentDataset.name, { engine: selectedEngineId, profile: pipeline.id  });
    }
  };

  const isGlobalProcessing = currentDataset.isProcessing || currentDataset.isStalled;

  const selectedEngine = engineList.find((e: any) => e.id === selectedEngineId);
  const currentPipelines = selectedEngine ? selectedEngine.pipelines : [];

  return (
    <div className="dashboard-container">
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        minHeight: '90px',
        borderBottom: '1px solid #eaeaea',
        paddingBottom: '10px',
        marginBottom: '20px'
      }}>

        {/* --- LEFT SIDE: Title & Meta --- */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '15px' }}>
          <h1 className="dashboard-title" style={{ margin: 0 }}>
            {currentDataset.name}
          </h1>
          <p className="dashboard-meta" style={{ margin: 0, color: '#666', fontSize: '0.9rem' }}>
            📷 {currentDataset.count} images detected
          </p>
        </div>

        {/* --- RIGHT SIDE: Compact Processing Block --- */}
        {/* We wrap this in a fixed-width div so text changes (like duration) don't cause horizontal jitter */}
        <div style={{ width: '520px' }}>
          {(currentDataset.isProcessing || currentDataset.isStalled) && (
            <div className="processing-block" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>

              {/* Top text row of the processing block */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', fontSize: '0.85rem', gap: '2px' }}>
                <div className="status-text" >
                  <span style={{ color: currentDataset.isStalled ? '#f44336' : '#2196f3', fontWeight: 'bold' }}>
                    {currentDataset.isStalled ? '⚠️ Stalled     ' : '⚙️ Processing: '}

                  </span>
                  <span>{currentDataset.latestJob?.step || 'Initializing...'}</span>
                </div>
                <div className="percentage-text" style={{ color: '#555', fontWeight: '500' }}>
                  {formatDuration()} | {Math.round(currentDataset.latestJob?.progress || 0)}%
                </div>
              </div>

              {/* The tiny progress bar */}
              <div className="progress-track" style={{ height: '6px', backgroundColor: '#e0e0e0', borderRadius: '3px', overflow: 'hidden', marginBottom: '4px' }}>
                <div
                  className="progress-fill"
                  style={{
                    height: '100%',
                    width: `${currentDataset.latestJob?.progress || 0}%`,
                    backgroundColor: currentDataset.isStalled ? '#f44336' : '#2196f3',
                    transition: 'width 0.3s ease',

                  }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* --- pipeline PROFILES (The Actions) --- */}
      <div className="pipeline-section" style={{ marginTop: '20px' }}>

        {/* --- ENGINE SELECTION COMBO BOX --- */}
        <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'center' }}>
          <label htmlFor="engine-select" style={{ fontWeight: 'bold', marginRight: '15px' }}>
            Processing Engine:
          </label>
          <select
            id="engine-select"
            value={selectedEngineId}
            onChange={(e) => setSelectedEngineId(e.target.value)}
            disabled={isGlobalProcessing} // Lock dropdown while a job is running
            style={{
              padding: '10px',
              borderRadius: '5px',
              border: '1px solid #ccc',
              fontSize: '1rem',
              minWidth: '250px'
            }}
          >
            {engineList.map((engine: any) => (
              <option key={engine.id} value={engine.id}>
                {engine.name}
              </option>
            ))}
          </select>
        </div>

        <h3 style={{ marginBottom: '15px' }}>Available Pipelines</h3>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '15px' }}>
          {/* Map over the currently selected engine's pipelines array */}
          {currentPipelines.map((pipeline: any) => {
            // Access the id directly from the pipeline object now
            const id = pipeline.id;
            const isDone = completedSteps.includes(pipeline.required_asset);

            return (
              <div key={id} className="pipeline-card" style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px 15px', // slightly padded for better look
                border: '1px solid #e0e0e0',
                borderRadius: '10px',
                backgroundColor: isDone ? '#f8fff9' : '#fff'
              }}>
                {/* Left Side: Text Details */}
                <div style={{ flex: 1, paddingRight: '15px' }}>
                  <h4 style={{ margin: 0, fontSize: '1rem' }}>{pipeline.name}</h4>
                  <p style={{ margin: '5px 0', fontSize: '0.85rem', color: '#666' }}>
                    {pipeline.description}
                  </p>
                  <p style={{ margin: '5px 0 0', fontSize: '0.8rem', color: '#666' }}>
                    Target: {pipeline.required_asset.toUpperCase()}
                  </p>
                </div>

                {/* Right Side: Action Buttons */}
                <div style={{
                  display: 'flex',
                  gap: '10px',
                  width: '510px',
                  justifyContent: 'flex-end'
                }}>
                  {isDone &&
                    <button
                      disabled={isGlobalProcessing && !isDone}
                      onClick={() => handlePipelineAction(pipeline, isDone)}
                      className={isDone ? 'btn-secondary' : 'btn-primary'}
                      style={{ width: '250px' }}
                    >
                      {`View ${id}`}
                    </button>
                  }
                  <button
                    disabled={isGlobalProcessing}
                    // NOTE: Ensure your handlePipelineAction sends both the pipeline id AND selectedEngineId to the backend!
                    onClick={() => handlePipelineAction(pipeline, false)}
                    className={isDone ? 'btn-alert' : 'btn-primary'}
                    style={{ width: '250px' }}
                  >
                    {isGlobalProcessing ? 'Wait' : isDone ? `Reprocess ${id}` : `Process ${id}`}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* --- COMPLETED ASSETS (Read Only Status) --- */}
      <div className="status-section" style={{ marginTop: '10px', padding: '10px', backgroundColor: '#f9f9f9', borderRadius: '10px' }}>
        <h4 style={{ marginBottom: '15px', color: '#555' }}>Dataset Technical Status</h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          {['add_photos', 'align_photos', 'depth_maps', 'model', 'uv', 'texture', 'tiled_model', 'point_cloud', 'dem', 'ortho'].map(step => {
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
      <div className="status-section" style={{ marginTop: '10px', padding: '10px', backgroundColor: '#f9f9f9', borderRadius: '10px' }}>
        <h4 style={{ marginBottom: '15px', color: '#555' }}>Dataset Export Status</h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          {['export_map_center', 'export_map_tiles', 'export_ortho', 'export_dem', 'export_model', 'export_point_cloud', 'export_report'].map(step => {
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