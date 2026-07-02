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

type NotificationLike = {
  title?: string | null;
  channel?: string | null;
  notification_type?: string | null;
  message_type?: string | null;
  template_code?: string | null;
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
  status?: string | null;
};

function normalizeText(value: string) {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

function looksTechnical(value: string) {
  return /api|backend|service|console|network|endpoint|token|response|status|field|provider|clipboard|gateway|localhost|debug|otp_rate|otp_cooldown|message_id|amount_minor|identity|traceback|exception|stack|serializer|payload/i.test(
    value,
  );
}

function isLikelyJsonText(value: string) {
  const text = value.trim();
  return (
    (text.startsWith('{') && text.endsWith('}')) ||
    (text.startsWith('[') && text.endsWith(']'))
  );
}

function parseJsonSafely(value: string) {
  if (!isLikelyJsonText(value)) return undefined;

  try {
    return JSON.parse(value) as unknown;
  } catch {
    return undefined;
  }
}

function getRecord(value: unknown): Record<string, unknown> | undefined {
  if (!value) return undefined;

  if (typeof value === 'string') {
    const parsed = parseJsonSafely(value);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }

    return undefined;
  }

  if (typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }

  return undefined;
}

function pickRecordValue(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' || typeof value === 'number') {
      return String(value);
    }
  }

  return '';
}

function toEnglishDigits(value: string) {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)));
}

function stringifyValue(value: unknown) {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return String(value);

  const record = getRecord(value);

  if (record) {
    const preferredKeys = [
      'message',
      'body',
      'text',
      'content',
      'subject',
      'title',
      'template',
      'otp',
      'code',
      'verification_code',
      'verificationCode',
    ];

    for (const key of preferredKeys) {
      const nestedValue = record[key];
      if (typeof nestedValue === 'string' || typeof nestedValue === 'number') {
        if (
          key === 'otp' ||
          key === 'code' ||
          key === 'verification_code' ||
          key === 'verificationCode'
        ) {
          return `کد تایید: ${nestedValue}`;
        }

        return String(nestedValue);
      }
    }

    try {
      return JSON.stringify(record);
    } catch {
      return '';
    }
  }

  return '';
}

function readSanitizedText(values: unknown[], fallback = '') {
  for (const value of values) {
    if (typeof value !== 'string') continue;

    const text = normalizeText(value);
    if (!text) continue;
    if (looksTechnical(text)) continue;
    if (/^[A-Z0-9_ -]+$/.test(text)) continue;
    if (text.length > 220) continue;

    return text;
  }

  return fallback;
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
    IN_APP: 'اعلان داخل برنامه',
    OTP: 'کد تایید',
    INVITE: 'دعوت',
    REMINDER: 'یادآوری',
    SETTLEMENT: 'تسویه',
    PAYMENT: 'پرداخت',
    EXPENSE: 'هزینه',
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

export function getFriendlyApiErrorMessage(
  error: unknown,
  {
    defaultMessage = 'عملیات انجام نشد. لطفاً دوباره تلاش کنید.',
    invalidMessage = 'اطلاعات واردشده کامل یا درست نیست.',
    authMessage = 'برای ادامه دوباره وارد حساب خود شوید.',
    forbiddenMessage = 'اجازه انجام این کار را ندارید.',
    notFoundMessage = 'برای این ایمیل حساب کاربری ساخته نشده، ثبت نام کنید.',
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

  return readSanitizedText([body.error?.message, body.detail, body.message, error.message], defaultMessage);
}

function normalizeOtpCandidate(value: unknown) {
  if (value === null || value === undefined) return '';
  const text = String(value).trim();
  return /^\d{4,8}$/.test(text) ? text : '';
}

function getOtpValue(context: Record<string, unknown>) {
  const keys = ['otp', 'code', 'verification_code', 'verificationCode'];

  for (const key of keys) {
    const value = normalizeOtpCandidate(context[key]);
    if (value) return value;
  }

  return '';
}

function extractOtpCodeFromText(value: string) {
  const text = value.trim();
  if (!text) return '';

  const patterns = [
    /\b(?:otp|one\s*time\s*code|verification\s*code|login\s*verification\s*code)\b[^\d]{0,30}(\d{4,8})\b/i,
    /(?:کد\s*تایید|رمز\s*یکبار\s*مصرف)[^\d]{0,30}(\d{4,8})\b/i,
    /\b(\d{4,8})\b/,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    const code = normalizeOtpCandidate(match?.[1]);
    if (code) return code;
  }

  return '';
}

function getOtpCode(item: NotificationLike, context: Record<string, unknown>) {
  const directCode = getOtpValue(context);
  if (directCode) return directCode;

  const rawValues = [
    stringifyValue(item.message),
    stringifyValue(item.body),
    stringifyValue(item.text),
    stringifyValue(item.content),
    stringifyValue(item.rendered_message),
  ];

  for (const value of rawValues) {
    const code = extractOtpCodeFromText(value);
    if (code) return code;
  }

  return '';
}

function formatMoney(value: string) {
  const normalized = toEnglishDigits(value).replace(/[^0-9.-]/g, '');
  const amount = Number(normalized);

  if (!Number.isFinite(amount)) {
    return '';
  }

  return `${amount.toLocaleString('fa-IR')} تومان`;
}

function readContext(...sources: unknown[]) {
  const merged: Record<string, unknown> = {};

  for (const source of sources) {
    const record = getRecord(source);
    if (!record) continue;

    for (const [key, value] of Object.entries(record)) {
      if (value !== undefined && value !== null && value !== '') {
        merged[key] = value;
      }
    }
  }

  return merged;
}


function getAmountValue(context: Record<string, unknown>) {
  return (
    pickRecordValue(context, [
      'amount',
      'total_amount',
      'payable_amount',
      'receivable_amount',
      'amount_due',
      'due_amount',
      'share_amount',
      'settlement_amount',
      'outstanding_amount',
      'amount_minor',
    ]) || ''
  );
}

function getGroupName(context: Record<string, unknown>) {
  return pickRecordValue(context, [
    'group_name',
    'group_title',
    'group_display_name',
    'group',
    'team_name',
    'team',
  ]);
}

function getExpenseName(context: Record<string, unknown>) {
  return pickRecordValue(context, ['expense_title', 'expense_name', 'title', 'subject']);
}

function getCounterpartyName(context: Record<string, unknown>) {
  return pickRecordValue(context, [
    'payer_name',
    'receiver_name',
    'payee_name',
    'debtor_name',
    'creditor_name',
    'from_name',
    'to_name',
    'member_name',
    'user_name',
  ]);
}

function inferFriendlyTitle(item: NotificationLike, context: Record<string, unknown>) {
  const combinedType = [
    item.title,
    item.notification_type,
    item.message_type,
    item.template_code,
    pickRecordValue(context, ['template', 'type', 'notification_type']),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  if (/otp|verify|verification|login|signin|signup/.test(combinedType) || getOtpCode(item, context)) {
    return 'کد تایید';
  }

  if (/settlement|receiv|credit/.test(combinedType)) {
    return 'دریافتی جدید';
  }

  if (/payment|payable|debt|reminder/.test(combinedType)) {
    return 'یادآوری پرداخت';
  }

  if (/expense/.test(combinedType)) {
    return 'هزینه جدید';
  }

  if (/invite|join/.test(combinedType)) {
    return 'دعوت به گروه';
  }

  const title = humanizeMachineLabel(item.title, '');
  if (title) return title;

  const type =
    humanizeMachineLabel(item.notification_type, '') ||
    humanizeMachineLabel(item.message_type, '') ||
    humanizeMachineLabel(item.template_code, '');

  if (type) return `پیام ${type}`;

  const channel = humanizeMachineLabel(item.channel, '');
  if (channel) return `پیام ${channel}`;

  return 'پیام جدید';
}

function inferFriendlyBody(item: NotificationLike, context: Record<string, unknown>) {
  const combinedType = [
    item.notification_type,
    item.message_type,
    item.template_code,
    pickRecordValue(context, ['template', 'type', 'notification_type']),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  const otp = getOtpCode(item, context);
  if (otp || /otp|verify|verification|login|signin|signup/.test(combinedType)) {
    return otp ? `کد تایید ورود: ${otp}` : 'کد تایید ورود برای شما ارسال شده است.';
  }

  const amount = formatMoney(getAmountValue(context));
  const groupName = getGroupName(context);
  const expenseName = getExpenseName(context);
  const counterparty = getCounterpartyName(context);

  if (/settlement|receiv|credit/.test(combinedType) && (amount || groupName)) {
    const amountPart = amount ? `${amount}` : 'مبلغی';
    const target = counterparty ? ` از ${counterparty}` : '';
    const groupPart = groupName ? ` در گروه «${groupName}»` : '';
    return `قرار است ${amountPart}${target}${groupPart} دریافت کنی.`;
  }

  if (/payment|payable|debt|reminder/.test(combinedType) && (amount || groupName)) {
    const amountPart = amount ? `${amount}` : 'مبلغی';
    const target = counterparty ? ` به ${counterparty}` : '';
    const groupPart = groupName ? ` برای گروه «${groupName}»` : '';
    return `لازم است ${amountPart}${target}${groupPart} پرداخت کنی.`;
  }

  if (/expense/.test(combinedType)) {
    const title = expenseName ? `«${expenseName}»` : 'یک هزینه جدید';
    const amountPart = amount ? ` به مبلغ ${amount}` : '';
    const groupPart = groupName ? ` در گروه «${groupName}»` : '';
    return `${title}${amountPart}${groupPart} ثبت شده است.`;
  }

  if (/invite|join/.test(combinedType)) {
    return groupName
      ? `برای پیوستن به گروه «${groupName}» دعوت شده‌ای.`
      : 'برای پیوستن به یک گروه جدید دعوت شده‌ای.';
  }

  const rawText = readSanitizedText([
    stringifyValue(item.message),
    stringifyValue(item.body),
    stringifyValue(item.text),
    stringifyValue(item.content),
    stringifyValue(item.rendered_message),
  ]);

  if (rawText) {
    return rawText;
  }

  const contextText = readSanitizedText([
    stringifyValue(item.template_context),
    stringifyValue(item.metadata),
    stringifyValue(item.data),
  ]);

  if (contextText) {
    return contextText;
  }

  if ((item.status || '').toUpperCase() === 'FAILED') {
    return 'این پیام هنوز به مقصد نرسیده است. کمی بعد دوباره بررسی کن.';
  }

  return 'جزئیات پیام در دسترس نیست.';
}

export function getFriendlyNotificationTitle(item: NotificationLike) {
  const context = readContext(item.template_context, item.metadata, item.data);
  return inferFriendlyTitle(item, context);
}

export function getFriendlyNotificationBody(item: NotificationLike) {
  const context = readContext(item.template_context, item.metadata, item.data);
  return inferFriendlyBody(item, context);
}

export function getFriendlyNotificationCode(item: NotificationLike) {
  const context = readContext(item.template_context, item.metadata, item.data);
  return getOtpCode(item, context);
}
