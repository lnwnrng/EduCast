export interface CostEstimate {
  total: number;
  chargeable: number;
  breakdown: Record<string, number>;
  currency: string;
}

export interface CostSummary {
  project_id: string;
  task_count: number;
  status_counts: Record<string, number>;
  estimated_total: number;
  actual_total: number;
  storage_bytes: number;
}

export interface DashboardRecentTask {
  id: string;
  project_id: string;
  status: string;
  progress: number;
  step_detail?: string | null;
  estimated_cost: number;
  actual_cost: number;
  created_at: string | null;
}

export interface DashboardStats {
  task_count: number;
  status_counts: Record<string, number>;
  estimated_total: number;
  actual_total: number;
  storage_bytes: number;
  recent_tasks: DashboardRecentTask[];
  admin_stats?: {
    user_count: number;
    today_registrations: number;
    project_count: number;
    storage_bytes: number;
  };
}
