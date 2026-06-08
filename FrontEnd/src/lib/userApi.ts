import { apiRequest } from './api';

export interface CurrentUser {
  id: number | string;
  phone_number?: string;
  phone?: string;
  username?: string;
  first_name?: string;
  last_name?: string;
}

export async function getCurrentUser() {
  return apiRequest<CurrentUser>('/users/me/');
}