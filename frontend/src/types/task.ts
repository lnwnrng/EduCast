export type TaskStatus =
  | 'pending'
  | 'parsing'
  | 'scripting'
  | 'reviewing'
  | 'generating'
  | 'composing'
  | 'completed'
  | 'failed';

export interface Task {
  id: string;
  project_id: string;
  task_type: string;
  status: TaskStatus;
  progress: number;
  error_message: string | null;
  estimated_cost: number;
  actual_cost: number;
  created_at: string;
  updated_at: string | null;
}

export interface SubTask {
  id: string;
  task_id: string;
  subtask_type: string;
  scene_id: string | null;
  status: string;
  progress: number;
  provider_name: string | null;
  result_url: string | null;
  cost: number;
  retry_count: number;
  error_message: string | null;
}

export interface TaskCreate {
  task_type?: string;
  config?: Record<string, unknown>;
}
