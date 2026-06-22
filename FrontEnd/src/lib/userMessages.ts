import { isApiError } from './api';

interface FriendlyErrorOptions {
  defaultMessage?: string;
  invalidMessage?: string;
  authMessage?: string;
  forbiddenMessage?: string;
  notFoundMessage?: string;
  unavailableMessage?: string;
  codeMap?: Record<string, string>;
}

function normalizeText(value: string) {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

function looksTechnical(value: string) {
  return /api|backend|service|console|network|endpoint|token|response|status|field|provider|clipboard|gateway|localhost|debug|otp_rate|otp_cooldown|message_id|amount_minor|identity/i.test(value);
}

export function humanizeMachineLabel(value?: string | null, fallback = 'نامشخص') {
  const input = normalizeText(String(value || ''));
  if (!input) return fallback;

  const upper = input.toUpperCase();

  const dictionary: Record<string, string> = {
    ACTIVE: 'فعال',
    ARCHIVED: 'آرشیو شده',
    VALID: 'معتبر',
    EXPIRED: 'منقضی شده',
    REVOKED: 'لغو شده',
    PENDING: 'در انتظار',
    SENT: 'ارسال شده',
    DELIVERED: 'تحویل شده',
    FAILED: 'ناموفق',
    CANCELED: 'لغو شده',
    CANCELLED: 'لغو شده',
    CLOSED: 'بسته شده',
    REPORTED: 'ثبت شده',
    CONFIRMED: 'تأیید شده',
    REJECTED: 'رد شده',
    PENDING_CONFIRMATION: 'در انتظار تأیید',
    COMPLETED: 'تکمیل شده',
    SENDING: 'در حال ارسال',
    EQUAL: 'مساوی',
    CUSTOM: 'سفارشی',
    SMS: 'پیامک',
    EMAIL: 'ایمیل',
    PUSH: 'اعلان',
    OTP: 'کد تایید',
    INVITE: 'دعوت',
    REMINDER: 'یادآوری',
    SETTLEMENT: 'تسویه',
    PAYMENT: 'پرداخت',
    GROUP: 'گروه',
    OWNER: 'مالک',
    ADMIN: 'مدیر',
    MEMBER: 'عضو',
    GENERAL: 'عمومی',
    TRIP: 'سفر',
    FOOD: 'غذا و رستوران',
    HOME: 'خانه و زندگی',
    OTHER: 'سایر',
  };

  if (dictionary[upper]) {
    return dictionary[upper];
  }

  if (/^[A-Z0-9_ -]+$/.test(String(value || ''))) {
    return fallback;
  }

  if (looksTechnical(input)) {
    return fallback;
  }

  return input;
}

function getApiBody(error: unknown) {
  if (!isApiError(error) || typeof error.body !== 'object' || !error.body) {
    return {};
  }

  return error.body as {
    code?: unknown;
    detail?: unknown;
    message?: unknown;
    error?: {
      code?: unknown;
      message?: unknown;
      details?: Record<string, unknown>;
    };
  };
}

function readSanitizedText(values: unknown[], fallback = '') {
  for (const value of values) {
    if (typeof value !== 'string') continue;
    const text = normalizeText(value);
    if (!text) continue;
    if (looksTechnical(text)) continue;
    if (/^[A-Z0-9_ -]+$/.test(text)) continue;
    if (text.length > 180) continue;
    return text;
  }

  return fallback;
}

export function getFriendlyApiErrorMessage(
  error: unknown,
  {
    defaultMessage = 'عملیات انجام نشد. لطفاً دوباره تلاش کنید.',
    invalidMessage = 'اطلاعات واردشده کامل یا درست نیست.',
    authMessage = 'برای ادامه دوباره وارد حساب خود شوید.',
    forbiddenMessage = 'اجازه انجام این کار را ندارید.',
    notFoundMessage = 'اطلاعات موردنظر پیدا نشد.',
    unavailableMessage = 'فعلاً انجام این کار ممکن نیست. کمی بعد دوباره تلاش کنید.',
    codeMap = {},
  }: FriendlyErrorOptions = {},
) {
  if (!isApiError(error)) {
    return defaultMessage;
  }

  const body = getApiBody(error);
  const code = String(body.error?.code || body.code || '').toUpperCase();

  if (code && codeMap[code]) {
    return codeMap[code];
  }

  if (error.status === 400) return invalidMessage;
  if (error.status === 401) return authMessage;
  if (error.status === 403) return forbiddenMessage;
  if (error.status === 404) return notFoundMessage;
  if (error.status >= 500) return unavailableMessage;

  return readSanitizedText([
    body.error?.message,
    body.detail,
    body.message,
    error.message,
  ], defaultMessage);
}

function stringifyValue(value: unknown) {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return String(value);

  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const preferredKeys = ['message', 'body', 'text', 'content', 'template', 'otp', 'code', 'verification_code'];

    for (const key of preferredKeys) {
      const nestedValue = record[key];
      if (typeof nestedValue === 'string' || typeof nestedValue === 'number') {
        if (key === 'otp' || key === 'code' || key === 'verification_code') {
          return `کد تایید: ${nestedValue}`;
        }

        return String(nestedValue);
      }
    }
  }

  return '';
}

export function getFriendlyNotificationTitle(item: {
  title?: string | null;
  channel?: string | null;
  notification_type?: string | null;
  message_type?: string | null;
  template_code?: string | null;
}) {
  const title = humanizeMachineLabel(item.title, '');
  if (title) return title;

  const type =
    humanizeMachineLabel(item.notification_type, '') ||
    humanizeMachineLabel(item.message_type, '') ||
    humanizeMachineLabel(item.template_code, '');

  if (type) return `پیام ${type}`;

  const channel = humanizeMachineLabel(item.channel, '');
  if (channel) return `پیام ${channel}`;

  return 'پیام سیستمی';
}

export function getFriendlyNotificationBody(item: {
  message?: unknown;
  body?: unknown;
  text?: unknown;
  content?: unknown;
  rendered_message?: unknown;
  template_context?: unknown;
  metadata?: unknown;
  data?: unknown;
  error_message?: unknown;
  error_code?: string | null;
  message_type?: string | null;
}) {
  const text = readSanitizedText([
    stringifyValue(item.message),
    stringifyValue(item.body),
    stringifyValue(item.text),
    stringifyValue(item.content),
    stringifyValue(item.rendered_message),
    stringifyValue(item.template_context),
    stringifyValue(item.metadata),
    stringifyValue(item.data),
    stringifyValue(item.error_message),
  ]);

  if (text) return text;

  const type = humanizeMachineLabel(item.message_type, '');
  if (type) return `پیام مربوط به ${type}.`;

  return 'جزئیات پیام در دسترس نیست.';
}
