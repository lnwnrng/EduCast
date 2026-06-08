import apiClient from './client';
import type { UserWithToken, User } from '../types/user';

export const register = (username: string, password: string) =>
  apiClient.post<UserWithToken>('/auth/register', { username, password });

export const login = (username: string, password: string) =>
  apiClient.post<UserWithToken>('/auth/login', { username, password });

export const refreshToken = () =>
  apiClient.post<{ message: string }>('/auth/refresh');

export const logout = () =>
  apiClient.post<{ message: string }>('/auth/logout');

export const getMe = () =>
  apiClient.get<User>('/auth/me');