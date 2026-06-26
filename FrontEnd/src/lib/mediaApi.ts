import { API_BASE_URL, apiRequest, getAccessToken, isApiError } from './api';

export type MediaFileType = 'RECEIPT' | 'AVATAR' | 'OTHER' | string;
export type MediaStatus = 'ACTIVE' | 'DELETED' | string;
export type MediaVisibility = 'GROUP_MEMBERS' | 'OWNER_ONLY' | 'PRIVATE' | string;

export interface MediaMetadata {
  id: string;
  group_id: string;
  related_expense_id?: string | null;
  file_type: MediaFileType;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: MediaStatus;
  visibility: MediaVisibility;
  created_at: string;
}

export interface MediaListItem {
  id: string;
  group_id?: string;
  related_expense_id?: string | null;
  file_type: MediaFileType;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status?: MediaStatus;
  visibility?: MediaVisibility;
  created_at: string;
}

export interface MediaListResponse {
  count: number;
  results: MediaListItem[];
}

type MediaListPayload =
  | MediaListItem[]
  | {
      count?: number;
      results?: MediaListItem[];
      data?: MediaListItem[];
      items?: MediaListItem[];
      files?: MediaListItem[];
    };

export interface UploadReceiptInput {
  groupId: string;
  file: File;
  relatedExpenseId?: string | null;
  visibility?: MediaVisibility;
}

export interface ListGroupMediaFilters {
  file_type?: MediaFileType;
  page?: number;
  page_size?: number;
}

export interface DownloadedMediaFile {
  blob: Blob;
  fileName: string;
  contentType: string;
}

function buildApiUrl(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL.replace(/\/+$/, '')}${normalizedPath}`;
}

function buildQuery(filters: ListGroupMediaFilters = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value));
    }
  });

  const query = params.toString();
  return query ? `?${query}` : '';
}

function getFileNameFromContentDisposition(value: string | null) {
  if (!value) return '';

  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i);

  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1].replace(/["']/g, ''));
    } catch {
      return utf8Match[1].replace(/["']/g, '');
    }
  }

  const normalMatch = value.match(/filename="?([^";]+)"?/i);
  return normalMatch?.[1] || '';
}

function getSafeFileName(fileName: string, fallback = 'receipt') {
  const cleaned = fileName.trim().replace(/[\\/]/g, '-');
  return cleaned || fallback;
}

function buildReceiptFormData(input: UploadReceiptInput, includeVisibility = true) {
  const formData = new FormData();

  formData.append('group_id', input.groupId);
  formData.append('file', input.file);

  if (input.relatedExpenseId) {
    formData.append('related_expense_id', input.relatedExpenseId);
  }

  if (includeVisibility) {
    formData.append('visibility', input.visibility || 'GROUP_MEMBERS');
  }

  return formData;
}

function shouldRetryUploadWithoutVisibility(error: unknown) {
  if (!isApiError(error) || error.status !== 400) return false;

  const text = `${error.message} ${error.bodyText}`.toLowerCase();
  return text.includes('visibility') || text.includes('unknown') || text.includes('unexpected');
}

export async function uploadReceipt(input: UploadReceiptInput) {
  try {
    return await apiRequest<MediaMetadata>('/media/receipts/', {
      method: 'POST',
      body: buildReceiptFormData(input),
    });
  } catch (error) {
    if (!shouldRetryUploadWithoutVisibility(error)) {
      throw error;
    }

    console.warn(
      'Receipt upload with visibility failed; retrying without the visibility field.',
      error,
    );

    return apiRequest<MediaMetadata>('/media/receipts/', {
      method: 'POST',
      body: buildReceiptFormData(input, false),
    });
  }
}

export async function getMediaDetail(fileId: string) {
  return apiRequest<MediaMetadata>(`/media/files/${fileId}/`);
}

export async function deleteMediaFile(fileId: string) {
  return apiRequest<{ message?: string }>(`/media/files/${fileId}/`, {
    method: 'DELETE',
  });
}

function shouldRetryAlternateMediaEndpoint(error: unknown) {
  return isApiError(error) && [400, 404, 405, 500, 502, 503, 504].includes(error.status);
}

function normalizeMediaList(data: MediaListPayload): MediaListResponse {
  if (Array.isArray(data)) {
    return { count: data.length, results: data };
  }

  const results = data.results || data.data || data.items || data.files || [];
  return {
    count: typeof data.count === 'number' ? data.count : results.length,
    results,
  };
}

async function requestGroupMedia(path: string) {
  const data = await apiRequest<MediaListPayload>(path);
  return normalizeMediaList(data);
}

export async function listGroupMedia(
  groupId: string,
  filters: ListGroupMediaFilters = {},
) {
  const query = buildQuery(filters);
  const primaryPath = `/groups/${groupId}/media/${query}`;
  const aliasPath = `/media/groups/${groupId}/media/${query}`;

  try {
    return await requestGroupMedia(primaryPath);
  } catch (error) {
    if (!shouldRetryAlternateMediaEndpoint(error)) {
      throw error;
    }

    console.warn('Could not list media via /groups/{id}/media/. Retrying media alias.', error);

    try {
      return await requestGroupMedia(aliasPath);
    } catch (aliasError) {
      const hasQuery = query.length > 0;

      if (!hasQuery || !shouldRetryAlternateMediaEndpoint(aliasError)) {
        throw aliasError;
      }

      console.warn(
        'Media list endpoint rejected filters. Retrying without filters so members can still see group files.',
        aliasError,
      );

      try {
        return await requestGroupMedia(`/groups/${groupId}/media/`);
      } catch (plainError) {
        if (!shouldRetryAlternateMediaEndpoint(plainError)) {
          throw plainError;
        }

        return requestGroupMedia(`/media/groups/${groupId}/media/`);
      }
    }
  }
}

export async function downloadMediaFile(
  fileId: string,
): Promise<DownloadedMediaFile> {
  let token = getAccessToken();

  async function requestDownload() {
    return fetch(buildApiUrl(`/media/files/${fileId}/download/`), {
      method: 'GET',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
  }

  let response = await requestDownload();

  if (response.status === 401) {
    await getMediaDetail(fileId);
    token = getAccessToken();
    response = await requestDownload();
  }

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(text || 'دانلود فایل رسید ناموفق بود.');
  }

  const blob = await response.blob();
  const contentType =
    response.headers.get('content-type') ||
    blob.type ||
    'application/octet-stream';

  const fileName = getSafeFileName(
    getFileNameFromContentDisposition(response.headers.get('content-disposition')),
    `receipt-${fileId}`,
  );

  return { blob, fileName, contentType };
}

export async function openMediaFile(fileId: string) {
  const downloaded = await downloadMediaFile(fileId);
  const objectUrl = window.URL.createObjectURL(downloaded.blob);
  const openedWindow = window.open(objectUrl, '_blank', 'noopener,noreferrer');

  if (!openedWindow) {
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = downloaded.fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  }

  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 60_000);
}
