import { apiRequest } from './api';

export type NotificationMessageStatus =
  | 'PENDING'
  | 'SENT'
  | 'FAILED'
  | 'DELIVERED'
  | 'CANCELED'
  | string;

export interface BackendNotificationMessage {
  id: string;
  recipient_user_id?: string;
  channel?: string;
  notification_type?: string;
  message_type?: string;
  title?: string;
  recipient_masked?: string;
  recipient?: string;
  recipient_email?: string;
  recipient_phone?: string;
  subject?: string;
  template_code?: string;
  status?: NotificationMessageStatus;
  priority?: string;
  is_read?: boolean;
  read_at?: string | null;
  provider?: string;
  provider_message_id?: string;
  error_code?: string;
  error_message?: string;
  retry_count?: number;
  last_attempt_at?: string | null;
  sent_at?: string | null;
  created_at?: string;
  updated_at?: string;
  message?: string;
  body?: string;
  text?: string;
  content?: string;
  rendered_message?: string;
  template_context?: string | Record<string, unknown>;
  metadata?: string | Record<string, unknown>;
  data?: string | Record<string, unknown>;
}

export type BackendNotification = BackendNotificationMessage;

interface PaginatedResponse<T> {
  count?: number;
  next?: string | null;
  previous?: string | null;
  results?: T[];
  data?: T[];
}

interface UnreadCountResponse {
  count?: number;
  unread_count?: number;
  unread?: number;
  pending_count?: number;
}

export interface NotificationMessagesParams {
  search?: string;
  status?: string;
  channel?: string;
  limit?: number;
}

export interface NotificationMutationPayload {
  title?: string;
  subject?: string;
  message?: string;
  body?: string;
  text?: string;
  content?: string;
  channel?: string;
  notification_type?: string;
  message_type?: string;
  recipient?: string;
  recipient_user_id?: string;
  recipient_email?: string;
  recipient_phone?: string;
  priority?: string;
  template_code?: string;
  template_context?: string | Record<string, unknown>;
  metadata?: string | Record<string, unknown>;
  data?: string | Record<string, unknown>;
}

export interface NotificationTestPayload {
  email?: string;
  recipient_email?: string;
  recipient?: string;
  phone?: string;
  phone_number?: string;
  recipient_phone?: string;
  subject?: string;
  title?: string;
  message?: string;
  body?: string;
  text?: string;
  content?: string;
  template_code?: string;
  metadata?: string | Record<string, unknown>;
  data?: string | Record<string, unknown>;
}

function unwrapList<T>(data: T[] | PaginatedResponse<T>) {
  if (Array.isArray(data)) return data;
  return data.results || data.data || [];
}

function getLimit(params: NotificationMessagesParams = {}) {
  return Math.min(Math.max(params.limit || 100, 1), 100);
}

function toJsonString(value: unknown) {
  if (!value) return '';

  if (typeof value === 'string') {
    return value;
  }

  try {
    return JSON.stringify(value);
  } catch {
    return '';
  }
}

function getSearchHaystack(item: BackendNotificationMessage) {
  return [
    item.id,
    item.channel,
    item.notification_type,
    item.message_type,
    item.title,
    item.subject,
    item.recipient_masked,
    item.recipient,
    item.recipient_email,
    item.recipient_phone,
    item.template_code,
    item.status,
    item.message,
    item.body,
    item.text,
    item.content,
    item.rendered_message,
    toJsonString(item.template_context),
    toJsonString(item.metadata),
    toJsonString(item.data),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function filterClientSide(
  items: BackendNotificationMessage[],
  params: NotificationMessagesParams = {},
) {
  const search = params.search?.trim().toLowerCase();

  return items.filter((item) => {
    if (params.status && params.status !== 'all') {
      if ((item.status || '').toLowerCase() !== params.status.toLowerCase()) {
        return false;
      }
    }

    if (params.channel && params.channel !== 'all') {
      if ((item.channel || '').toLowerCase() !== params.channel.toLowerCase()) {
        return false;
      }
    }

    if (search && !getSearchHaystack(item).includes(search)) {
      return false;
    }

    return true;
  });
}

function getDateScore(item: BackendNotificationMessage) {
  return new Date(item.sent_at || item.last_attempt_at || item.created_at || 0).getTime();
}

function buildMessageKey(item: BackendNotificationMessage) {
  return [
    item.id,
    item.channel,
    item.notification_type,
    item.message_type,
    item.title,
    item.subject,
    item.recipient,
    item.recipient_email,
    item.recipient_phone,
    item.recipient_masked,
    item.template_code,
    item.created_at,
    item.sent_at,
    item.message,
    item.body,
    item.text,
    item.content,
    item.rendered_message,
  ]
    .filter(Boolean)
    .join('|');
}

function mergeNotificationItems(items: BackendNotificationMessage[]) {
  const seen = new Map<string, BackendNotificationMessage>();

  for (const item of items) {
    const key = buildMessageKey(item);
    const existing = seen.get(key);

    if (!existing) {
      seen.set(key, item);
      continue;
    }

    seen.set(key, {
      ...existing,
      ...item,
      template_context: item.template_context || existing.template_context,
      metadata: item.metadata || existing.metadata,
      data: item.data || existing.data,
      message: item.message || existing.message,
      body: item.body || existing.body,
      text: item.text || existing.text,
      content: item.content || existing.content,
      rendered_message: item.rendered_message || existing.rendered_message,
      recipient_masked: item.recipient_masked || existing.recipient_masked,
      recipient: item.recipient || existing.recipient,
      recipient_email: item.recipient_email || existing.recipient_email,
      recipient_phone: item.recipient_phone || existing.recipient_phone,
      subject: item.subject || existing.subject,
      status: item.status || existing.status,
      sent_at: item.sent_at || existing.sent_at,
      created_at: item.created_at || existing.created_at,
    });
  }

  return Array.from(seen.values()).sort((left, right) => getDateScore(right) - getDateScore(left));
}

async function fetchNotificationsFromPath(path: string) {
  return apiRequest<BackendNotificationMessage[] | PaginatedResponse<BackendNotificationMessage>>(path);
}

function normalizeNotificationList(
  data: BackendNotificationMessage[] | PaginatedResponse<BackendNotificationMessage>,
  params: NotificationMessagesParams = {},
) {
  return filterClientSide(mergeNotificationItems(unwrapList(data)), params).slice(0, getLimit(params));
}

function sanitizePayloadValue(value: unknown) {
  if (value === undefined || value === null) {
    return undefined;
  }

  if (typeof value !== 'string') {
    return value;
  }

  const trimmed = value.trim();

  if (!trimmed) {
    return undefined;
  }

  if (
    (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
    (trimmed.startsWith('[') && trimmed.endsWith(']'))
  ) {
    try {
      return JSON.parse(trimmed) as unknown;
    } catch {
      return value;
    }
  }

  return value;
}

function sanitizePayload(payload: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(payload)
      .map(([key, value]) => [key, sanitizePayloadValue(value)])
      .filter(([, value]) => value !== undefined),
  );
}

export async function getNotifications(
  params: NotificationMessagesParams = {},
) {
  const limit = getLimit(params);
  const response = await fetchNotificationsFromPath(`/notifications/?limit=${limit}`);
  return normalizeNotificationList(response, params);
}

export async function getNotificationMessages(
  params: NotificationMessagesParams = {},
) {
  const limit = getLimit(params);
  const endpoints = [
    `/notifications/messages/?limit=${limit}`,
    `/notifications/?limit=${limit}`,
  ];

  const settled = await Promise.allSettled(endpoints.map((path) => fetchNotificationsFromPath(path)));
  const successfulResults = settled
    .filter((result): result is PromiseFulfilledResult<BackendNotificationMessage[] | PaginatedResponse<BackendNotificationMessage>> => result.status === 'fulfilled')
    .flatMap((result) => unwrapList(result.value));

  if (!successfulResults.length) {
    const rejected = settled.find((result): result is PromiseRejectedResult => result.status === 'rejected');
    throw rejected?.reason ?? new Error('Unable to load notifications');
  }

  return filterClientSide(mergeNotificationItems(successfulResults), params).slice(0, limit);
}

export async function getNotificationDetail(notificationId: string) {
  return apiRequest<BackendNotification>(`/notifications/${String(notificationId).trim()}/`);
}

export async function createNotification(payload: NotificationMutationPayload) {
  return apiRequest<BackendNotification>('/notifications/', {
    method: 'POST',
    body: JSON.stringify(sanitizePayload(payload as Record<string, unknown>)),
  });
}

export async function updateNotification(
  notificationId: string,
  payload: NotificationMutationPayload,
) {
  return apiRequest<BackendNotification>(`/notifications/${String(notificationId).trim()}/`, {
    method: 'PATCH',
    body: JSON.stringify(sanitizePayload(payload as Record<string, unknown>)),
  });
}

export async function deleteNotification(notificationId: string) {
  return apiRequest<void>(`/notifications/${String(notificationId).trim()}/`, {
    method: 'DELETE',
  });
}

export async function markNotificationMessageAsRead(notificationId: string) {
  const normalizedId = String(notificationId || '').trim();

  if (!normalizedId) {
    throw new Error('Notification id is required');
  }

  const attempts = [
    {
      path: `/notifications/${normalizedId}/read/`,
      options: {
        method: 'POST',
      },
    },
    {
      path: `/notifications/${normalizedId}/`,
      options: {
        method: 'PATCH',
        body: JSON.stringify({ is_read: true }),
      },
    },
  ] as const;

  let lastError: unknown;

  for (const attempt of attempts) {
    try {
      return await apiRequest(attempt.path, attempt.options);
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError ?? new Error('Unable to mark notification as read');
}

export async function markAllNotificationsAsRead() {
  return apiRequest('/notifications/read-all/', {
    method: 'POST',
  });
}

export async function sendNotificationEmailTest(payload: NotificationTestPayload) {
  return apiRequest('/notifications/email/test/', {
    method: 'POST',
    body: JSON.stringify(sanitizePayload(payload as Record<string, unknown>)),
  });
}

export async function sendNotificationSmsTest(payload: NotificationTestPayload) {
  return apiRequest('/notifications/sms/test/', {
    method: 'POST',
    body: JSON.stringify(sanitizePayload(payload as Record<string, unknown>)),
  });
}

export async function getPendingNotificationCount() {
  try {
    const unread = await apiRequest<UnreadCountResponse>('/notifications/unread-count/');
    const count = Number(unread.unread_count ?? unread.count ?? unread.unread ?? unread.pending_count);

    if (Number.isFinite(count) && count >= 0) {
      return count;
    }
  } catch (error) {
    console.warn('Unread notification count endpoint unavailable, falling back to messages list.', error);
  }

  try {
    const messages = await getNotificationMessages({ limit: 100 });
    return messages.filter((item) => item.is_read !== true && !item.read_at).length;
  } catch (error) {
    console.warn('Failed to fetch notification count', error);
    return 0;
  }
}
