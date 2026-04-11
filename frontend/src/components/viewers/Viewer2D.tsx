// src/components/viewer/Viewer.tsx
import { useData } from '@/context/DataContext';
import './Viewer2D.css';

const Viewer2D = () => {
  const { datasets, selectedFolder } = useData();
  const currentDataset = datasets.find(d => d.name === selectedFolder);

  if (!currentDataset) return null;

  return (
    <div className="viewer-wrapper">
      {!currentDataset.isCompleted ? (
        <div className="viewer-empty">
          No orthophoto available yet. Complete the pipeline first.
        </div>
      ) : (
        <div className="viewer-canvas">
          <img
            src={`/api/outputs/${currentDataset.name}_out/orthophoto_preview.jpg`}
            alt="Orthophoto"
            className="viewer-image"
            draggable={false}
          />
        </div>
      )}
    </div>
  );
};

export default Viewer2D;