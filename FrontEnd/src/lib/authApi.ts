import { apiRequest, setTokens } from './api';
import type { CurrentUser } from './userApi';

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: CurrentUser;
}

export interface OtpRequestResponse {
  message: string;
  expires_in: number;
  resend_after?: number;
  debug_otp?: string;
}

export interface MessageResponse {
  message: string;
}

function persistAuthTokens(response: AuthResponse) {
  setTokens(response.access_token, response.refresh_token);
  return response;
}

export async function loginWithPassword(payload: { art_name: string; password: string }) {
  const response = await apiRequest<AuthResponse>('/auth/password/login/', {
    method: 'POST',
    auth: false,
    body: JSON.stringify(payload),
  });

  return persistAuthTokens(response);
}

export async function requestLoginOtp(phoneNumber: string) {
  return apiRequest<OtpRequestResponse>('/auth/otp/request/', {
    method: 'POST',
    auth: false,
    body: JSON.stringify({ phone_number: phoneNumber }),
  });
}

export async function verifyLoginOtp(payload: { phone_number: string; code: string }) {
  const response = await apiRequest<AuthResponse>('/auth/otp/verify/', {
    method: 'POST',
    auth: false,
    body: JSON.stringify(payload),
  });

  return persistAuthTokens(response);
}

export async function updateSignupProfile(payload: {
  display_name?: string;
  art_name: string;
  first_name?: string;
  last_name?: string;
}) {
  return apiRequest<CurrentUser>('/users/me/', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function setInitialPassword(payload: {
  new_password: string;
  new_password_confirm: string;
}) {
  return apiRequest<MessageResponse>('/auth/password/set/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
