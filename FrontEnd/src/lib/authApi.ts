import {
  clearTokens,
  getRefreshToken,
  identityApiRequest,
  setTokens,
} from './api';
import { getCurrentUser } from './userApi';
import type { CurrentUser } from './userApi';

export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
  expires_in?: number;
  user?: CurrentUser;
}

type RawAuthResponse = Partial<AuthResponse> & {
  access?: string;
  refresh?: string;
  tokens?: {
    access_token?: string;
    refresh_token?: string;
    access?: string;
    refresh?: string;
  };
};

export interface OtpRequestResponse {
  message: string;
  expires_in: number;
  resend_after?: number;
  debug_otp?: string;
}

export interface MessageResponse {
  message: string;
}


export class IncompleteSignupError extends Error {
  constructor(message = 'برای این ایمیل هنوز ثبت‌نام کامل نشده است.') {
    super(message);
    this.name = 'IncompleteSignupError';
  }
}

export function isIncompleteSignupError(error: unknown): error is IncompleteSignupError {
  return error instanceof IncompleteSignupError;
}

function hasCompletedSignup(user?: CurrentUser | null) {
  const artName = String(user?.art_name || '').trim();
  const username = String(user?.username || '').trim();
  return Boolean(artName || username);
}

function persistAuthTokens(response: RawAuthResponse): AuthResponse {
  const accessToken =
    response.access_token ||
    response.access ||
    response.tokens?.access_token ||
    response.tokens?.access;
  const refreshToken =
    response.refresh_token ||
    response.refresh ||
    response.tokens?.refresh_token ||
    response.tokens?.refresh;

  if (!accessToken) {
    throw new Error('Login response does not include an access token.');
  }

  setTokens(accessToken, refreshToken);

  return {
    ...response,
    access_token: accessToken,
    refresh_token: refreshToken,
  };
}

export async function loginWithPassword(payload: { art_name: string; password: string }) {
  const response = await identityApiRequest<RawAuthResponse>('/auth/password/login/', {
    method: 'POST',
    auth: false,
    skipAuthRefresh: true,
    body: JSON.stringify(payload),
  });

  return persistAuthTokens(response);
}

export async function requestLoginOtp(email: string) {
  return identityApiRequest<OtpRequestResponse>('/auth/otp/request/', {
    method: 'POST',
    auth: false,
    skipAuthRefresh: true,
    body: JSON.stringify({ email }),
  });
}

export async function verifyLoginOtp(payload: { email: string; code: string }) {
  const response = await identityApiRequest<RawAuthResponse>('/auth/otp/verify/', {
    method: 'POST',
    auth: false,
    skipAuthRefresh: true,
    body: JSON.stringify(payload),
  });

  return persistAuthTokens(response);
}

export async function verifyLoginOtpForExistingAccount(payload: { email: string; code: string }) {
  await verifyLoginOtp(payload);

  const currentUser = await getCurrentUser();

  if (!hasCompletedSignup(currentUser)) {
    clearTokens();
    throw new IncompleteSignupError();
  }

  return currentUser;
}

export async function updateSignupProfile(payload: {
  display_name?: string;
  art_name: string;
  first_name?: string;
  last_name?: string;
}) {
  return identityApiRequest<CurrentUser>('/users/me/', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function setInitialPassword(payload: {
  new_password: string;
  new_password_confirm: string;
}) {
  return identityApiRequest<MessageResponse>('/auth/password/set/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function logoutCurrentUser() {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    clearTokens();
    return;
  }

  try {
    await identityApiRequest<MessageResponse>('/auth/logout/', {
      method: 'POST',
      auth: false,
      skipAuthRefresh: true,
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch (error) {
    console.warn('Logout request failed. Clearing local auth state.', error);
  } finally {
    clearTokens();
  }
}
