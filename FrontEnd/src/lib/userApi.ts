import { identityApiRequest } from './api';

export interface CurrentUser {
  id: string;
  phone_number?: string;
  phone?: string;
  display_name?: string | null;
  art_name?: string | null;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  avatar_url?: string | null;
  is_phone_verified?: boolean;
  role?: string;
}

export function getCurrentUser() {
  return identityApiRequest<CurrentUser>('/users/me/');
}

export async function updateCurrentUserProfile(payload: {
  display_name?: string;
  art_name?: string;
  first_name?: string;
  last_name?: string;
}) {
  return identityApiRequest<CurrentUser>('/users/me/', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}
