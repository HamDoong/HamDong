import { apiRequest, isApiError } from './api';

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
  metadata?: Record<string, unknown>;
  data?: Record<string, unknown>;
}

export interface SendTestSmsInput {
  phone_number: string;
  message: string;
}

export interface SendTestSmsResponse {
  status?: string;
  provider?: string;
  message_id?: string;
  message?: string;
}

interface PaginatedResponse<T> {
  count?: number;
  next?: string | null;
  previous?: string | null;
  results?: T[];
  data?: T[];
}

export interface NotificationMessagesParams {
  search?: string;
  status?: string;
  channel?: string;
  limit?: number;
}

function unwrapList<T>(data: T[] | PaginatedResponse<T>) {
  if (Array.isArray(data)) return data;
  return data.results || data.data || [];
}

function getLimit(params: NotificationMessagesParams = {}) {
  return Math.min(Math.max(params.limit || 100, 1), 100);
}

function shouldFallbackToDebugMessages(error: unknown) {
  return isApiError(error) && [404, 405, 502, 503, 504].includes(error.status);
}

function getSearchHaystack(item: BackendNotificationMessage) {
  return [
    item.id,
    item.channel,
    item.notification_type,
    item.message_type,
    item.title,
    item.recipient_masked,
    item.recipient,
    item.template_code,
    item.status,
    item.provider,
    item.provider_message_id,
    item.error_code,
    item.error_message,
    item.message,
    item.body,
    item.text,
    item.content,
    item.rendered_message,
    typeof item.template_context === 'string'
      ? item.template_context
      : JSON.stringify(item.template_context || ''),
    JSON.stringify(item.metadata || ''),
    JSON.stringify(item.data || ''),
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

export async function getNotificationMessages(
  params: NotificationMessagesParams = {},
) {
  const limit = getLimit(params);
  let data: BackendNotificationMessage[] | PaginatedResponse<BackendNotificationMessage>;

  try {
    data = await apiRequest<
      BackendNotificationMessage[] | PaginatedResponse<BackendNotificationMessage>
    >(`/notifications/?limit=${limit}`);
  } catch (error) {
    if (!shouldFallbackToDebugMessages(error)) {
      throw error;
    }

    data = await apiRequest<
      BackendNotificationMessage[] | PaginatedResponse<BackendNotificationMessage>
    >(`/notifications/messages/?limit=${limit}`);
  }

  return filterClientSide(unwrapList(data), params).slice(0, limit);
}

export async function getPendingNotificationCount() {
  try {
    const messages = await getNotificationMessages();
    return messages.filter((item) => {
      const status = (item.status || '').toUpperCase();
      return status === 'PENDING' || status === 'FAILED';
    }).length;
  } catch (error) {
    console.warn('Failed to fetch notification count', error);
    return 0;
  }
}

export async function sendTestSms(input: SendTestSmsInput) {
  return apiRequest<SendTestSmsResponse>('/notifications/sms/test/', {
    method: 'POST',
    body: JSON.stringify({
      phone_number: input.phone_number.trim(),
      message: input.message.trim(),
    }),
  });
}
