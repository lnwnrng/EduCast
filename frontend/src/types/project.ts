export interface Project {
  id: string;
  title: string;
  subject: string;
  grade: string;
  description: string | null;
  template: string;
  status: string;
  created_at: string;
  updated_at: string | null;
}

export interface ProjectCreate {
  title: string;
  subject?: string;
  grade?: string;
  description?: string;
  template?: string;
}

export interface ProjectUpdate {
  title?: string;
  subject?: string;
  grade?: string;
  description?: string;
  template?: string;
  status?: string;
}
