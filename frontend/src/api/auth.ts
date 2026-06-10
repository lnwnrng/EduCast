import apiClient from './client';
import type { UserWithToken, User } from '../types/user';

export const register = (
  username: string,
  password: string,
  email: string,
  code: string
) => apiClient.post<UserWithToken>('/auth/register', { username, password, email, code });

export const sendVerificationCode = (email: string) =>
  apiClient.post<{ message: string; cooldown_seconds: number }>('/auth/send-code', { email });

export const login = (username: string, password: string) =>
  apiClient.post<UserWithToken>('/auth/login', { username, password });

export const refreshToken = () =>
  apiClient.post<{ message: string }>('/auth/refresh');

export const logout = () =>
  apiClient.post<{ message: string }>('/auth/logout');

export const getMe = () =>
  apiClient.get<User>('/auth/me');