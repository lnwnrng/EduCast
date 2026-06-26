export type ResourceType =
  | 'video'
  | 'audio'
  | 'image'
  | 'subtitle'
  | 'ir_snapshot'
  | 'archive'
  | 'folder';

export interface Resource {
  id: string;
  project_id: string;
  resource_type: ResourceType;
  title: string;
  name: string;
  file_path: string;
  file_size: number;
  mime_type: string | null;
  version: number;
  is_folder: boolean;
  parent_id: string | null;
  watermark_applied: boolean;
  created_at: string;
  updated_at: string | null;
}
