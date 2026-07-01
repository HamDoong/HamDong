import { identityApiRequest, isApiError } from './api';

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

export interface ArtNameAvailabilityResult {
  available: boolean | null;
  unsupported?: boolean;
  message?: string;
}

export interface UserSearchResult {
  user_id: string;
  art_name: string;
  avatar_url?: string | null;
}

interface UserSearchResponse {
  items: UserSearchResult[];
  count: number;
  query: string;
}

function buildArtNameAvailabilityPaths(artName: string) {
  const encodedValue = encodeURIComponent(artName);
  const configuredPath = import.meta.env.VITE_ART_NAME_AVAILABILITY_PATH?.trim();

  const candidates = [
    configuredPath
      ? configuredPath.includes('{value}')
        ? configuredPath.replace('{value}', encodedValue)
        : `${configuredPath}${configuredPath.includes('?') ? '&' : '?'}art_name=${encodedValue}`
      : '',
    `/users/art-name-availability/?art_name=${encodedValue}`,
    `/users/art-name/check/?art_name=${encodedValue}`,
    `/users/check-art-name/?art_name=${encodedValue}`,
    `/users/check-username/?username=${encodedValue}`,
    `/users/username-availability/?username=${encodedValue}`,
    `/auth/check-art-name/?art_name=${encodedValue}`,
  ];

  return Array.from(new Set(candidates.filter(Boolean)));
}

function readBooleanField(source: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    if (typeof source[key] === 'boolean') {
      return source[key] as boolean;
    }
  }

  return null;
}

function parseArtNameAvailabilityResponse(payload: unknown): ArtNameAvailabilityResult {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return { available: null, unsupported: true };
  }

  const body = payload as Record<string, unknown>;
  const nested = body.data && typeof body.data === 'object' && !Array.isArray(body.data)
    ? (body.data as Record<string, unknown>)
    : null;

  const available =
    readBooleanField(body, ['available', 'is_available', 'isAvailable']) ??
    readBooleanField(nested || {}, ['available', 'is_available', 'isAvailable']);

  if (available !== null) {
    return {
      available,
      message: typeof body.message === 'string' ? body.message : typeof nested?.message === 'string' ? nested.message : undefined,
    };
  }

  const exists =
    readBooleanField(body, ['exists', 'is_taken', 'isTaken', 'taken']) ??
    readBooleanField(nested || {}, ['exists', 'is_taken', 'isTaken', 'taken']);

  if (exists !== null) {
    return {
      available: !exists,
      message: typeof body.message === 'string' ? body.message : typeof nested?.message === 'string' ? nested.message : undefined,
    };
  }

  return { available: null, unsupported: true };
}

export function getCurrentUser() {
  return identityApiRequest<CurrentUser>('/users/me/');
}

export async function searchUsersByArtName(artName: string, limit = 10) {
  const query = artName.trim();

  if (query.length < 2) return [];

  const response = await identityApiRequest<UserSearchResponse>(
    `/users/search/?art_name=${encodeURIComponent(query)}&limit=${Math.min(Math.max(limit, 1), 20)}&exclude_me=true`,
  );

  return Array.isArray(response.items) ? response.items : [];
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

export async function checkArtNameAvailability(
  artName: string,
  options: {
    currentArtName?: string;
    signal?: AbortSignal;
  } = {},
) {
  const normalizedArtName = artName.trim();
  const normalizedCurrentArtName = options.currentArtName?.trim();

  if (!normalizedArtName) {
    return {
      available: false,
      message: 'نام کاربری نمی‌تواند خالی باشد.',
    } satisfies ArtNameAvailabilityResult;
  }

  if (
    normalizedCurrentArtName &&
    normalizedArtName.localeCompare(normalizedCurrentArtName, 'fa', { sensitivity: 'base' }) === 0
  ) {
    return {
      available: true,
      message: 'این نام کاربری روی حساب شما ثبت شده است.',
    } satisfies ArtNameAvailabilityResult;
  }

  const paths = buildArtNameAvailabilityPaths(normalizedArtName);

  for (const path of paths) {
    try {
      const response = await identityApiRequest<unknown>(path, {
        signal: options.signal,
      });

      const parsed = parseArtNameAvailabilityResponse(response);

      if (!parsed.unsupported) {
        return parsed;
      }
    } catch (error) {
      if (options.signal?.aborted) {
        throw error;
      }

      if (!isApiError(error)) {
        throw error;
      }

      const body = error.body as { error?: { code?: string } } | undefined;
      const code = String(body?.error?.code || '').toUpperCase();

      if (code === 'ART_NAME_ALREADY_EXISTS') {
        return {
          available: false,
          message: 'این نام کاربری قبلاً ثبت شده است.',
        };
      }

      if (code === 'INVALID_ART_NAME') {
        return {
          available: false,
          message: 'نام کاربری معتبر نیست.',
        };
      }

      if ([404, 405, 501].includes(error.status)) {
        continue;
      }

      throw error;
    }
  }

  return {
    available: null,
    unsupported: true,
  } satisfies ArtNameAvailabilityResult;
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
