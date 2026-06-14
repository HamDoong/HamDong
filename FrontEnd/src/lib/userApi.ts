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
  avatar_url?: string | null;
  is_phone_verified?: boolean;
  role?: string;
}

export async function getCurrentUser() {
  return apiRequest<CurrentUser>('/users/me/');
}

export async function updateCurrentUserProfile(payload: {
  display_name?: string;
  art_name?: string;
  first_name?: string;
  last_name?: string;
}) {
  return apiRequest<CurrentUser>('/users/me/', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}
