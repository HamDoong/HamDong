const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export class ApiError extends Error {
  status: number;
  body: unknown;
  bodyText: string;

  constructor(message: string, status: number, body: unknown, bodyText: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
    this.bodyText = bodyText;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

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

function parseJsonSafely(text: string) {
  if (!text) return undefined;

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function readResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();

  if (!text) {
    return undefined as T;
  }

  return parseJsonSafely(text) as T;
}

async function throwApiError(path: string, response: Response): Promise<never> {
  const text = await response.text();
  const body = parseJsonSafely(text);
  const message =
    typeof body === 'object' && body && 'detail' in body
      ? String((body as { detail?: unknown }).detail)
      : text || `Request failed with status ${response.status}`;

  console.error('API Error:', {
    path,
    status: response.status,
    body,
  });

  throw new ApiError(message, response.status, body, text);
}

async function refreshAccessToken() {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    throw new Error('No refresh token found');
  }

  async function tryRefresh(body: Record<string, string>) {
    return fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
  }

  let response = await tryRefresh({ refresh_token: refreshToken });

  if (!response.ok) {
    response = await tryRefresh({ refresh: refreshToken });
  }

  if (!response.ok) {
    clearTokens();
    throw new Error('Refresh token failed');
  }

  const data = await readResponse<Record<string, string>>(response);

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
  const { auth = true, skipAuthRefresh = false, ...fetchOptions } = options;

  const token = getAccessToken();
  const headers = new Headers(fetchOptions.headers);

  if (!headers.has('Content-Type') && fetchOptions.body) {
    headers.set('Content-Type', 'application/json');
  }

  if (auth && token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (response.status === 401 && auth && !skipAuthRefresh) {
    const newAccessToken = await refreshAccessToken();

    headers.set('Authorization', `Bearer ${newAccessToken}`);

    const retryResponse = await fetch(`${API_BASE_URL}${path}`, {
      ...fetchOptions,
      headers,
    });

    if (!retryResponse.ok) {
      return throwApiError(path, retryResponse);
    }

    return readResponse<T>(retryResponse);
  }

  if (!response.ok) {
    return throwApiError(path, response);
  }

  return readResponse<T>(response);
}
