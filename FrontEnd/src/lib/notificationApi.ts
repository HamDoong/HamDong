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
  channel?: string;
  message_type?: string;
  recipient_masked?: string;
  recipient?: string;
  template_code?: string;
  status?: NotificationMessageStatus;
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
}

function unwrapList<T>(data: T[] | PaginatedResponse<T>) {
  if (Array.isArray(data)) return data;
  return data.results || data.data || [];
}

function getSearchHaystack(item: BackendNotificationMessage) {
  return [
    item.id,
    item.channel,
    item.message_type,
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
  const data = await apiRequest<
    BackendNotificationMessage[] | PaginatedResponse<BackendNotificationMessage>
  >('/notifications/messages/');

  return filterClientSide(unwrapList(data), params);
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
