// src/components/Workspace.tsx
import { useData } from '@/context/DataContext';
import './Workspace.css';

const Workspace = () => {
  const { datasets, selectedFolder, setSelectedFolder } = useData();

  // Helper to determine status color dynamically
  const getStatusColor = (dataset: any) => {
    if (dataset.isProcessing) return '#2196f3';
    if (dataset.isFailed || dataset.isStalled) return '#f44336';
    if (dataset.isCompleted) return '#4caf50';
    return '#e0e0e0';
  };

  return (
    <div className="workspace-container">
      <div className="workspace-header">
        <h2>Workspace</h2>
      </div>

      <div className="workspace-list">
        {datasets.map(dataset => {
          const isSelected = selectedFolder === dataset.name;
          return (
            <div 
              key={dataset.name} 
              onClick={() => setSelectedFolder(dataset.name)}
              className={`dataset-item ${isSelected ? 'selected' : ''}`}
            >
              <div className="dataset-name">{dataset.name}</div>
              <div 
                className="status-dot" 
                style={{ backgroundColor: getStatusColor(dataset) }} 
                title={dataset.latestJob?.status || 'Ready'} 
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Workspace;