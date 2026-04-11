// src/context/DataContext.tsx
import React, { createContext, useState, useEffect, useContext, useMemo, type ReactNode } from 'react';
import type { Job, FolderInfo, Dataset } from '@/types/interfaces';

interface DataContextType {
  datasets: Dataset[];
  selectedFolder: string | null;
  setSelectedFolder: (folder: string | null) => void;
  startJob: (folderName: string) => Promise<void>;
  refreshData: () => void;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export const DataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [folders, setFolders] = useState<FolderInfo[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);

  const fetchFolders = async () => {
    try {
      const res = await fetch('/api/available-datasets');
      if (res.ok) setFolders(await res.json());
    } catch (e) {
      console.error("Failed to fetch folders", e);
    }
  };

  const fetchJobs = async () => {
    try {
      const res = await fetch('/api/jobs');
      if (res.ok) setJobs(await res.json());
    } catch (e) {
      console.error("Failed to fetch jobs", e);
    }
  };

  const refreshData = () => {
    fetchFolders();
    fetchJobs();
  };

  const startJob = async (folderName: string) => {
    try {
      const response = await fetch(`/api/run/${encodeURIComponent(folderName)}`, { method: 'POST' });
      if (response.ok) refreshData();
    } catch (error) {
      console.error("Error starting job:", error);
    }
  };

  useEffect(() => {
    refreshData();
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, []);

  const datasets = useMemo(() => {
    const merged: Dataset[] = folders.map(folder => {
      const latestJob = jobs.find(j => j.dataset_name === folder.name);

      let isProcessing = latestJob?.status === 'PROCESSING' || latestJob?.status === 'PENDING';
      const isCompleted = latestJob?.status === 'COMPLETED';
      const isFailed = latestJob?.status === 'FAILED';
      let isStalled = false;

      if (isProcessing && latestJob?.updated_at) {
        const safeDateStr = latestJob.updated_at.replace(' ', 'T') + 'Z';
        const diffMinutes = (Date.now() - new Date(safeDateStr).getTime()) / (1000 * 60);
        if (diffMinutes > 5) {
          isStalled = true;
          isProcessing = false;
        }
      }

      return {
        ...folder,
        latestJob,
        isProcessing,
        isCompleted,
        isFailed,
        isStalled
      };
    });

    return merged.sort((a, b) => {
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
  }, [folders, jobs]);

  useEffect(() => {
    if (selectedFolder && !folders.some(f => f.name === selectedFolder)) {
      setSelectedFolder(null);
    }
  }, [folders, selectedFolder]);

  return (
    <DataContext.Provider value={{ datasets, selectedFolder, setSelectedFolder, startJob, refreshData }}>
      {children}
    </DataContext.Provider>
  );
};

export const useData = () => {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error("useData must be used within a DataProvider");
  }
  return context;
};