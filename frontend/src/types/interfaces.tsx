export interface Job {
  id: number;
  dataset_name: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  step: string;
  progress: number;
  created_at: string;
  updated_at: string;
}

export interface FolderInfo {
  name: string;
  count: number;
}

// This is our "Single Source of Truth" row object
export interface Dataset extends FolderInfo {
  latestJob?: Job;
  isProcessing: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  isStalled: boolean;
}
