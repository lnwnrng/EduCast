export interface User {
  id: string;
  display_id: number | null;
  username: string;
  email: string | null;
  role: 'admin' | 'user';
  is_active: boolean;
  last_login: string | null;
  created_at: string;
}

export interface UserAdmin extends User {
  updated_at: string | null;
  project_count: number;
}

export interface UserWithToken {
  user: User;
  access_token: string;
  token_type: string;
}