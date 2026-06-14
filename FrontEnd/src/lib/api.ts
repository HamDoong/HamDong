const DEFAULT_API_BASE_URL = '/api/v1';
const DEFAULT_LOCAL_IDENTITY_API_BASE_URL = 'http://localhost:8001/api/v1';

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

/**
 * Keeps API configuration forgiving during local development.
 *
 * Examples:
 * - /api               -> /api/v1
 * - http://localhost:8080/api -> http://localhost:8080/api/v1
 * - /api/v1/           -> /api/v1
 */
export function normalizeApiBaseUrl(value?: string) {
  let normalized = (value || DEFAULT_API_BASE_URL).trim().replace(/\/+$/, '');

  if (!normalized) {
    normalized = DEFAULT_API_BASE_URL;
  }

  if (/\/api$/i.test(normalized)) {
    normalized = `${normalized}/v1`;
  }

  return normalized;
}

export const API_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

function isLocalBrowser() {
  if (typeof window === 'undefined') return false;
  return window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
}

function getIdentityFallbackBaseUrl() {
  const configuredBaseUrl = import.meta.env.VITE_IDENTITY_API_BASE_URL?.trim();

  if (configuredBaseUrl) {
    return normalizeApiBaseUrl(configuredBaseUrl);
  }

  return isLocalBrowser() ? DEFAULT_LOCAL_IDENTITY_API_BASE_URL : undefined;
}

function buildApiUrl(baseUrl: string, path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${normalizeApiBaseUrl(baseUrl)}${normalizedPath}`;
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
  const bodyObject = typeof body === 'object' && body ? body as Record<string, unknown> : undefined;
  const nestedError = bodyObject?.error;
  const nestedMessage =
    typeof nestedError === 'object' && nestedError && 'message' in nestedError
      ? String((nestedError as { message?: unknown }).message || '')
      : '';
  const detail = bodyObject && 'detail' in bodyObject ? String(bodyObject.detail || '') : '';
  const message = detail || nestedMessage || text || `Request failed with status ${response.status}`;

  console.error('API Error:', {
    path,
    status: response.status,
    body,
  });

  throw new ApiError(message, response.status, body, text);
}

async function refreshAccessToken(baseUrl = API_BASE_URL) {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    throw new Error('No refresh token found');
  }

  async function tryRefresh(body: Record<string, string>) {
    return fetch(buildApiUrl(baseUrl, '/auth/token/refresh/'), {
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

export interface ApiRequestOptions extends RequestInit {
  auth?: boolean;
  skipAuthRefresh?: boolean;
  baseUrl?: string;
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    auth = true,
    skipAuthRefresh = false,
    baseUrl = API_BASE_URL,
    ...fetchOptions
  } = options;

  const token = getAccessToken();
  const headers = new Headers(fetchOptions.headers);

  if (
    !headers.has('Content-Type') &&
    fetchOptions.body &&
    !(typeof FormData !== 'undefined' && fetchOptions.body instanceof FormData)
  ) {
    headers.set('Content-Type', 'application/json');
  }

  if (auth && token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const requestUrl = buildApiUrl(baseUrl, path);
  const response = await fetch(requestUrl, {
    ...fetchOptions,
    headers,
  });

  if (response.status === 401 && auth && !skipAuthRefresh) {
    const newAccessToken = await refreshAccessToken(baseUrl);

    headers.set('Authorization', `Bearer ${newAccessToken}`);

    const retryResponse = await fetch(requestUrl, {
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

function shouldRetryIdentityDirectly(error: unknown) {
  if (error instanceof TypeError) return true;
  return isApiError(error) && [404, 502, 503, 504].includes(error.status);
}

/**
 * Identity endpoints normally go through the API gateway. During local
 * development, if the gateway route is stale/missing, retry the same request
 * against identity-service on port 8001. This keeps production traffic on the
 * gateway and fixes the local 404 shown by the login screen.
 */
export async function identityApiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  try {
    return await apiRequest<T>(path, options);
  } catch (error) {
    const fallbackBaseUrl = getIdentityFallbackBaseUrl();

    if (
      !fallbackBaseUrl ||
      normalizeApiBaseUrl(options.baseUrl || API_BASE_URL) === fallbackBaseUrl ||
      !shouldRetryIdentityDirectly(error)
    ) {
      throw error;
    }

    console.warn(
      `Gateway request for ${path} failed; retrying identity-service directly at ${fallbackBaseUrl}.`,
      error,
    );

    return apiRequest<T>(path, {
      ...options,
      baseUrl: fallbackBaseUrl,
    });
  }
}
