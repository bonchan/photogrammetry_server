import React, { createContext, useState, useEffect, useContext, useMemo, type ReactNode } from 'react';
import type { Job, Dataset, RunConfig } from '@/types/interfaces';

interface DataContextType {
  datasets: Dataset[];
  selectedFolder: string | null;
  setSelectedFolder: (folder: string | null) => void;
  startJob: (folderName: string, config?: RunConfig) => Promise<void>;
  refreshData: () => void;
  completedSteps: string[];
  engineList: any;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export const DataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // We now store a single source of truth directly from the workspace endpoint
  const [rawDatasets, setRawDatasets] = useState<any[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [engineList, setEngineList] = useState<any>({});

  const [completedSteps, setCompletedSteps] = useState<string[]>([]);

  // --- 1. INITIAL LOAD & MANUAL REFRESH ---
  const fetchWorkspace = async () => {
    try {
      const res = await fetch('/api/workspace');
      if (res.ok) {
        setRawDatasets(await res.json());
      }
    } catch (e) {
      console.error("Failed to fetch workspace", e);
    }
  };

  const fetchEngines = async () => {
    try {
      const res = await fetch('/api/engines');
      if (res.ok) {
        const data = await res.json();
        console.log('engines', data)
        setEngineList(data);
      }
    } catch (e) {
      console.error("Failed to fetch pipelines", e);
    }
  };

  const refreshData = () => {
    fetchWorkspace();
  };

  // --- 2. WEBSOCKET FOR REAL-TIME UPDATES ---
  useEffect(() => {
    // Initial fetch
    fetchWorkspace();
    fetchEngines();

    // Connect to WebSocket (adjust port if your backend runs elsewhere)
    // If you are using Vite proxy, you might need to use standard WS url formatting
    const wsUrl = `ws://127.0.0.1:8000/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => console.log("🟢 Connected to Metashape live feed");

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        // payload = { job_id, status, step, progress }

        // Update the specific dataset that owns this job_id
        setRawDatasets(prev => prev.map(dataset => {
          if (dataset.latest_job?.id === payload.job_id || dataset.latestJob?.id === payload.job_id) {
            return {
              ...dataset,
              latest_job: {
                ...dataset.latest_job,
                status: payload.status,
                step: payload.step,
                progress: payload.progress,
                updated_at: new Date().toISOString() // Touch the timestamp
              }
            };
          }
          return dataset;
        }));
      } catch (e) {
        console.error("WebSocket parsing error:", e);
      }
    };

    ws.onclose = () => console.log("🔴 Disconnected from Metashape feed");

    return () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    // If no folder is selected, clear the state and do nothing
    if (!selectedFolder) {
      setCompletedSteps([]);
      return;
    }

    setCompletedSteps([]);

    // 1. Open the WebSocket connection
    // Note: Change localhost:8001 to your actual server address if different
    const wsUrl = `ws://localhost:8000/api/ws/state/${encodeURIComponent(selectedFolder)}`;
    const ws = new WebSocket(wsUrl);

    // 2. Listen for messages from the server
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Whenever the server sends new data, update the UI
        if (data.completed_tasks) {
          setCompletedSteps(data.completed_tasks);
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };

    // 3. Handle connection errors
    ws.onerror = (error) => {
      console.error("WebSocket error on state connection:", error);
      setCompletedSteps([]); // Fallback to empty if it fails
    };

    // 4. Cleanup: Close the socket when the user selects a different folder or leaves the page
    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [selectedFolder]); // Re-run this whenever the selected folder changes

  // --- 3. MODULAR RUN LAUNCHER ---
  // Now accepts a config object so you can say startJob("FM-PP-10", { start_step: "build_depth_maps" })
  const startJob = async (folderName: string, config: RunConfig = {}) => {
    try {
      console.log('startJob', config)
      const response = await fetch(`/api/run/${encodeURIComponent(folderName)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config) // Pass the pipeline boundaries!
      });
      if (response.ok) {
        // We trigger a hard refresh just to ensure DB syncs, 
        // but WS will take over immediately after.
        refreshData();
      }
    } catch (error) {
      console.error("Error starting job:", error);
    }
  };

  // --- 4. COMPUTED STATE ---
  const datasets = useMemo(() => {
    const processed: Dataset[] = rawDatasets.map(item => {
      // Handle the snake_case from python to camelCase in React
      const job = item.latest_job;

      let isProcessing = job?.status === 'PROCESSING' || job?.status === 'PENDING';
      const isCompleted = job?.status === 'COMPLETED';
      const isFailed = job?.status === 'FAILED';
      let isStalled = false;

      // Stall detection (if WS disconnects and API hasn't heard from it in 5 mins)
      if (isProcessing && job?.updated_at) {
        const safeDateStr = job.updated_at.replace(' ', 'T') + 'Z';
        const diffMinutes = (Date.now() - new Date(safeDateStr).getTime()) / (1000 * 60);
        if (diffMinutes > 5) {
          isStalled = true;
          isProcessing = false;
        }
      }

      return {
        name: item.dataset_name,
        count: item.image_count,
        latestJob: job,
        isProcessing,
        isCompleted,
        isFailed,
        isStalled
      };
    });

    return processed.sort((a, b) => {
      const getStatusWeight = (d: Dataset) => {
        if (d.isCompleted) return 4;
        if (d.isFailed) return 3;
        if (d.isProcessing) return 2;
        return 1;
      };

      const weightA = getStatusWeight(a);
      const weightB = getStatusWeight(b);

      if (weightA !== weightB) return weightB - weightA;
      return a.name.localeCompare(b.name);
    });
  }, [rawDatasets]);

  // Keep selected folder valid
  useEffect(() => {
    if (selectedFolder && !datasets.some(f => f.name === selectedFolder)) {
      setSelectedFolder(null);
    }
  }, [datasets, selectedFolder]);

  return (
    <DataContext.Provider value={{ datasets, selectedFolder, setSelectedFolder, startJob, refreshData, completedSteps, engineList }}>
      {children}
    </DataContext.Provider>
  );
};

export const useData = () => {
  const context = useContext(DataContext);
  if (context === undefined) throw new Error("useData must be used within a DataProvider");
  return context;
};