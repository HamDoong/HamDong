const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken?: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);

  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function refreshAccessToken() {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    throw new Error('No refresh token found');
  }

  const tryRefresh = async (body: Record<string, string>) => {
    return fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
  };

  let response = await tryRefresh({ refresh_token: refreshToken });

  if (!response.ok) {
    response = await tryRefresh({ refresh: refreshToken });
  }

  if (!response.ok) {
    clearTokens();
    throw new Error('Refresh token failed');
  }

  const data = await response.json();

  const newAccessToken = data.access_token || data.access;
  const newRefreshToken = data.refresh_token || data.refresh;

  if (!newAccessToken) {
    clearTokens();
    throw new Error('Refresh response does not include access token');
  }

  setTokens(newAccessToken, newRefreshToken);

  return newAccessToken;
}

interface ApiRequestOptions extends RequestInit {
  auth?: boolean;
  skipAuthRefresh?: boolean;
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const token = getAccessToken();

  const headers = new Headers(options.headers);

  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  if (options.auth !== false && token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && options.auth !== false && !options.skipAuthRefresh) {
    const newAccessToken = await refreshAccessToken();

    headers.set('Authorization', `Bearer ${newAccessToken}`);

    const retryResponse = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      skipAuthRefresh: true,
    } as RequestInit);

    if (!retryResponse.ok) {
      const errorText = await retryResponse.text();
      throw new Error(errorText || `Request failed with status ${retryResponse.status}`);
    }

    if (retryResponse.status === 204) {
      return undefined as T;
    }

    return retryResponse.json() as Promise<T>;
  }

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}