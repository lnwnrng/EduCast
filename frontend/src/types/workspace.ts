import type { CostEstimate } from './cost';

export interface VideoVersion {
  version: number;
  ir_version: number | null;
  resource_id: string;
  subtitle_vtt_id: string | null;
  archive_id: string | null;
  created_at: string | null;
}

export interface LatestTask {
  id: string;
  status: string;
  progress: number;
  step_detail?: string | null;
  error_message: string | null;
}

export interface WorkspaceData {
  project_id: string;
  title: string;
  status: string;
  subject: string;
  grade: string;
  has_ir: boolean;
  latest_ir_version: number | null;
  videos: VideoVersion[];
  is_stale: boolean;
  cost_estimate: CostEstimate | null;
  latest_task: LatestTask | null;
}
