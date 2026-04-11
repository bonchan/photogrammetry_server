import React, { useEffect, useRef } from 'react';
import { useData } from '@/context/DataContext';

const Viewer3D = () => {
  const { selectedFolder } = useData();
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    // When the folder changes, tell the Vanilla Iframe to load the new model
    if (iframeRef.current && selectedFolder) {
      iframeRef.current.contentWindow?.postMessage({
        type: 'LOAD_DATASET',
        name: selectedFolder
      }, '*');
    }
  }, [selectedFolder]);

  if (!selectedFolder) return <div style={{padding: '20px', color: '#888'}}>Select a dataset...</div>;

  return (
    <iframe
      ref={iframeRef}
      src="/viewer.html"
      style={{
        width: '100%',
        height: '100%',
        border: 'none',
        background: '#1a1a1a'
      }}
      title="3D Viewer"
    />
  );
};

export default Viewer3D;