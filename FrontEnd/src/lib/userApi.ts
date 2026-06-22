import { identityApiRequest } from './api';

export interface CurrentUser {
  id: string;
  email?: string;
  phone_number?: string;
  phone?: string;
  display_name?: string | null;
  art_name?: string | null;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  date_of_birth?: string | null;
  city?: string | null;
  bio?: string | null;
  avatar_url?: string | null;
  is_email_verified?: boolean;
  is_phone_verified?: boolean;
  role?: string;
  created_at?: string;
  updated_at?: string;
}

export function getCurrentUser() {
  return identityApiRequest<CurrentUser>('/users/me/');
}

export async function updateCurrentUserProfile(payload: {
  display_name?: string;
  art_name?: string;
  first_name?: string;
  last_name?: string;
  phone_number?: string | null;
  date_of_birth?: string | null;
  city?: string | null;
  bio?: string | null;
  avatar_url?: string | null;
}) {
  return identityApiRequest<CurrentUser>('/users/me/', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function setPassword(payload: {
  new_password: string;
  new_password_confirm: string;
}) {
  return identityApiRequest<{ message?: string }>('/auth/password/set/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
}) {
  return identityApiRequest<{ message?: string }>('/auth/password/change/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
