import { apiRequest } from './api';

export interface CurrentUser {
  id: string;
  phone_number?: string;
  phone?: string;
  username?: string;
  display_name?: string | null;
  art_name?: string | null;
  first_name?: string;
  last_name?: string;
}

export async function getCurrentUser() {
  return apiRequest<CurrentUser>('/users/me/');
}
