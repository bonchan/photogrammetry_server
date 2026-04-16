// src/components/layout/DetailPanel.tsx
import { useState } from 'react';
import { useData } from '@/context/DataContext';
import Dashboard from '@/components/dashboard/Dashboard';
import Viewer2D from '@/components/viewers/Viewer2D';
import Viewer3D from '@/components/viewers/Viewer3D';
import MapViewer from '@/components/viewers/MapViewer';
import OrthoSwipe from '@/components/viewers/OrthoSwipe';

const DetailPanel = () => {
  const { datasets, selectedFolder } = useData();
  const [activeTab, setActiveTab] = useState<'dashboard' | '2Dviewer' | 'OrthoSwipe' | '3Dviewer' | 'mapviewer' | 'outputs'>('dashboard');

  const currentDataset = datasets.find(d => d.name === selectedFolder);

  // If no folder is clicked, show the empty state
  if (!currentDataset) {
    return (
      <div className="main-panel">
        <div className="empty-state">Select a dataset from the workspace to begin</div>
      </div>
    );
  }

  // Otherwise, show the tabs and content
  return (
    <div className="main-panel">
      {/* Tabs Navigation */}
      <div className="tab-bar">
        {(['dashboard', 'OrthoSwipe', '2Dviewer', '3Dviewer', 'mapviewer', 'outputs'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`tab-button ${activeTab === tab ? 'active' : ''}`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content Router */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        {activeTab === 'dashboard' && <Dashboard />}

        {activeTab === 'OrthoSwipe' && <OrthoSwipe />}
        {activeTab === '2Dviewer' && <Viewer2D />}
        {activeTab === '3Dviewer' && <Viewer3D />}
        {activeTab === 'mapviewer' && <MapViewer />}

        {activeTab === 'outputs' && (
          <div style={{ padding: '40px' }}>
            <h2>Generated Files</h2>
            {currentDataset.isCompleted ? (
              <ul style={{ lineHeight: '2' }}>
                <li><a
                  href={`/api/outputs/${currentDataset.name}_out/orthomosaic.tif`}
                  download={`${currentDataset.name}_Orthomosaic.tif`}
                  target="_blank"
                  rel="noreferrer">
                  Download High-Res Orthophoto (TIFF)
                </a></li>
                <li><a
                  href={`/api/outputs/${currentDataset.name}_out/report.pdf`}
                  download={`${currentDataset.name}_Quality_Report.pdf`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download Quality Report (PDF)
                </a></li>
              </ul>
            ) : (
              <p style={{ color: '#888' }}>No outputs generated yet.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DetailPanel;