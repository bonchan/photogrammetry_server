import { useState, useEffect, useRef } from 'react';

interface Job {
  id: number;
  dataset_name: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  step: string;
  progress: number;
}

interface FolderInfo {
  name: string;
  count: number;
}

function App() {
  const [availableFolders, setAvailableFolders] = useState<FolderInfo[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);

  // Visor State
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });

  const fetchAvailable = async () => {
    try {
      const response = await fetch('/api/available-datasets');
      const data = await response.json();
      setAvailableFolders(data);
    } catch (error) {
      console.error("Error fetching folders:", error);
    }
  };

  const fetchJobs = async () => {
    try {
      const response = await fetch('/api/jobs');
      if (!response.ok) throw new Error("Network response was not ok");
      const data = await response.json();
      setJobs(data);
    } catch (error) {
      console.error("Error fetching jobs:", error);
    }
  };

  const startJob = async (folderName: string) => {
    try {
      const response = await fetch(`/api/run/${encodeURIComponent(folderName)}`, {
        method: 'POST',
      });
      if (response.ok) fetchJobs();
    } catch (error) {
      console.error("Error starting job:", error);
    }
  };

  useEffect(() => {
    fetchJobs();
    fetchAvailable();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  // --- MERGE & SORT LOGIC ---
  const rows = availableFolders.map(folder => {
    const latestJob = jobs.find(j => j.dataset_name === folder.name);
    return { ...folder, latestJob };
  });

  rows.sort((a, b) => {
    // 1. Define the priority weights (Higher number = closer to the top)
    const getStatusWeight = (status?: string) => {
      if (status === 'COMPLETED') return 4;
      if (status === 'FAILED') return 3;     // <-- Failed now sits right under Completed
      if (status === 'PROCESSING') return 2;
      // PENDING or undefined (Ready) drop to the bottom
      return 1;
    };

    const weightA = getStatusWeight(a.latestJob?.status);
    const weightB = getStatusWeight(b.latestJob?.status);

    // 2. Sort by weight first
    if (weightA !== weightB) {
      return weightB - weightA;
    }

    // 3. Alphabetical fallback if they have the same status
    return a.name.localeCompare(b.name);
  });

  // --- VISOR PAN/ZOOM HANDLERS ---
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setScale(prev => Math.min(Math.max(0.1, prev * zoomFactor), 10));
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    setIsDragging(true);
    dragStart.current = { x: e.clientX - position.x, y: e.clientY - position.y };
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStart.current.x,
      y: e.clientY - dragStart.current.y
    });
  };

  const handlePointerUp = () => setIsDragging(false);

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', fontFamily: 'system-ui, sans-serif' }}>

      {/* LEFT PANEL: The List */}
      <div style={{ width: '40%', minWidth: '400px', borderRight: '1px solid #ccc', display: 'flex', flexDirection: 'column', backgroundColor: '#fafafa' }}>
        <div style={{ padding: '20px', borderBottom: '1px solid #ddd', backgroundColor: '#fff' }}>
          <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Datasets</h1>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
          {rows.map(row => {
            const isProcessing = row.latestJob?.status === 'PROCESSING' || row.latestJob?.status === 'PENDING';
            const isCompleted = row.latestJob?.status === 'COMPLETED';
            const isSelected = selectedFolder === row.name;

            return (
              <div
                key={row.name}
                onClick={() => isCompleted && setSelectedFolder(row.name)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 15px',
                  marginBottom: '8px',
                  backgroundColor: isSelected ? '#e3f2fd' : '#fff',
                  border: `1px solid ${isSelected ? '#90caf9' : '#eee'}`,
                  borderRadius: '6px',
                  cursor: isCompleted ? 'pointer' : 'default',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                }}
              >
                {/* Info Column */}
                <div style={{ flex: 1, marginRight: '15px' }}>
                  <div style={{ fontWeight: 'bold', fontSize: '1rem', color: '#333' }}>{row.name}</div>

                  {isProcessing ? (
                    <div style={{ marginTop: '5px' }}>
                      <div style={{ fontSize: '0.8rem', color: '#eb95dc', fontWeight: 'bold' }}>{row.latestJob?.step || 'Initializing...'}</div>
                      <div style={{ width: '100%', height: '4px', backgroundColor: '#eee', marginTop: '4px', borderRadius: '2px' }}>
                        <div style={{ width: `${row.latestJob?.progress || 0}%`, height: '100%', backgroundColor: '#4caf50' }} />
                      </div>
                    </div>
                  ) : (
                    <div style={{ fontSize: '0.8rem', color: '#888', marginTop: '2px' }}>
                      📷 {row.count} images {isCompleted && '• ✅ Processed'} {row.latestJob?.status === 'FAILED' && '• ❌ Failed'}
                    </div>
                  )}
                </div>

                {/* Action Column */}
                <div>
                  <button
                    disabled={isProcessing || row.count === 0}
                    onClick={(e) => {
                      e.stopPropagation(); // Prevent row click when clicking button
                      startJob(row.name);
                    }}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: isProcessing || row.count === 0 ? '#e0e0e0' : (isCompleted ? '#fff' : '#000'),
                      color: isProcessing || row.count === 0 ? '#999' : (isCompleted ? '#000' : '#fff'),
                      border: isCompleted ? '1px solid #ccc' : 'none',
                      borderRadius: '4px', cursor: isProcessing || row.count === 0 ? 'not-allowed' : 'pointer',
                      fontSize: '0.85rem', fontWeight: 'bold'
                    }}
                  >
                    {isProcessing ? `${Math.round(row.latestJob?.progress || 0)}%` : isCompleted ? 'Re-run' : 'Process'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* RIGHT PANEL: The Visor */}
      <div style={{ flex: 1, backgroundColor: '#1e1e1e', position: 'relative', overflow: 'hidden' }}>
        {!selectedFolder ? (
          <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: '#666' }}>
            Select a completed dataset to view the orthophoto
          </div>
        ) : (
          <div
            style={{ width: '100%', height: '100%', cursor: isDragging ? 'grabbing' : 'grab' }}
            onWheel={handleWheel}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
          >
            <img
              // THIS IS A PLACEHOLDER PATH - See notes below!
              src={`/api/outputs/${selectedFolder}_out/orthophoto_preview.jpg`}
              alt="Orthophoto"
              draggable={false}
              style={{
                transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                transformOrigin: '0 0',
                transition: isDragging ? 'none' : 'transform 0.1s ease',
                maxWidth: '100%', // Prevent it from initially blowing up
                maxHeight: '100%',
                objectFit: 'contain'
              }}
            />
            {/* Visor Controls Overlay */}
            <div style={{ position: 'absolute', bottom: '20px', right: '20px', backgroundColor: 'rgba(0,0,0,0.6)', padding: '10px', borderRadius: '8px', color: 'white', fontSize: '0.85rem' }}>
              <div>Zoom: {Math.round(scale * 100)}%</div>
              <button onClick={() => { setScale(1); setPosition({ x: 0, y: 0 }); }} style={{ marginTop: '5px', background: '#333', color: 'white', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>Reset View</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;