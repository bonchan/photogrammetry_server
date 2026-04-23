export interface RunConfig {
  engine?: string;
  template?: string;
  profile?: string;
  clear_downstream?: boolean;
}

// Ensure your Job interface includes progress
export interface Job {
  id: number;
  dataset_name: string;
  status: string;
  step: string;
  progress?: number;
  created_at?: string;
  updated_at?: string;
}

export interface Dataset {
  name: string;
  count: number;
  latestJob?: Job;
  isProcessing: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  isStalled: boolean;
}