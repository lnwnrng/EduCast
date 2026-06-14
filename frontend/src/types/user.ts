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
  // 注意：认证使用 httpOnly cookie，前端不直接处理 access_token
  // 此字段由后端返回但前端不存储，仅用于兼容旧接口
  access_token?: string;
  token_type?: string;
}