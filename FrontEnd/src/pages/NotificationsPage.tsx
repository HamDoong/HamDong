import { useEffect, useMemo, useState } from 'react';
import {
  Bell,
  CheckCircle2,
  Clock3,
  MessageCircle,
  RefreshCw,
  Search,
  Send,
  Smartphone,
  XCircle,
} from 'lucide-react';
import {
  getNotificationMessages,
  sendTestSms,
  type BackendNotificationMessage,
} from '../lib/notificationApi';
import { useFeedback } from '../components/feedback/FeedbackProvider';

interface NotificationsPageProps {
  onUnreadCountChange?: (count: number) => void;
}

type StatusFilter = 'all' | 'PENDING' | 'SENT' | 'FAILED' | 'DELIVERED';

const statusTabs: Array<{ value: StatusFilter; label: string }> = [
  { value: 'all', label: 'همه' },
  { value: 'PENDING', label: 'در انتظار' },
  { value: 'SENT', label: 'ارسال شده' },
  { value: 'DELIVERED', label: 'تحویل شده' },
  { value: 'FAILED', label: 'ناموفق' },
];

function formatDate(value?: string | null) {
  if (!value) return 'زمان نامشخص';

  try {
    return new Intl.DateTimeFormat('fa-IR', {
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function getStatusLabel(status?: string) {
  const value = (status || '').toUpperCase();

  if (value === 'PENDING') return 'در انتظار';
  if (value === 'SENT') return 'ارسال شده';
  if (value === 'DELIVERED') return 'تحویل شده';
  if (value === 'FAILED') return 'ناموفق';
  if (value === 'CANCELED') return 'لغو شده';

  return status || 'نامشخص';
}

function getStatusStyle(status?: string) {
  const value = (status || '').toUpperCase();

  if (value === 'FAILED') {
    return {
      icon: <XCircle className="h-4.5 w-4.5" />,
      badge: 'bg-rose-50 text-rose-600 ring-rose-100',
      iconBox: 'bg-rose-50 text-rose-600',
    };
  }

  if (value === 'PENDING') {
    return {
      icon: <Clock3 className="h-4.5 w-4.5" />,
      badge: 'bg-amber-50 text-amber-700 ring-amber-100',
      iconBox: 'bg-amber-50 text-amber-600',
    };
  }

  if (value === 'SENT' || value === 'DELIVERED') {
    return {
      icon: <CheckCircle2 className="h-4.5 w-4.5" />,
      badge: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
      iconBox: 'bg-emerald-50 text-emerald-600',
    };
  }

  return {
    icon: <Bell className="h-4.5 w-4.5" />,
    badge: 'bg-slate-50 text-slate-600 ring-slate-100',
    iconBox: 'bg-slate-50 text-slate-500',
  };
}

function getMessageTitle(item: BackendNotificationMessage) {
  if (item.title) return item.title;
  if (item.template_code) return item.template_code;
  if (item.notification_type) return item.notification_type;
  if (item.message_type) return item.message_type;
  if (item.channel) return `پیام ${item.channel}`;
  return 'پیام نوتیفیکیشن';
}

function stringifyMessageValue(value: unknown): string {
  if (!value) return '';

  if (typeof value === 'string') {
    return value;
  }

  if (typeof value === 'number') {
    return String(value);
  }

  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;

    const preferredKeys = [
      'message',
      'body',
      'text',
      'content',
      'otp',
      'code',
      'verification_code',
      'template',
    ];

    for (const key of preferredKeys) {
      const nestedValue = record[key];

      if (typeof nestedValue === 'string' || typeof nestedValue === 'number') {
        if (key === 'otp' || key === 'code' || key === 'verification_code') {
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

function getMessageBody(item: BackendNotificationMessage) {
  const candidates = [
    item.message,
    item.body,
    item.text,
    item.content,
    item.rendered_message,
    item.template_context,
    item.metadata,
    item.error_message,
  ];

  for (const candidate of candidates) {
    const value = stringifyMessageValue(candidate);

    if (value.trim()) {
      return value;
    }
  }

  if (item.error_code) return `خطا: ${item.error_code}`;
  if (item.message_type) return `نوع پیام: ${item.message_type}`;

  return 'متن پیام در پاسخ بک‌اند خالی است.';
}

function getSearchText(item: BackendNotificationMessage) {
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
    stringifyMessageValue(item.template_context),
    stringifyMessageValue(item.metadata),
    stringifyMessageValue(item.data),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function getPendingOrFailedCount(items: BackendNotificationMessage[]) {
  return items.filter((item) => {
    const status = (item.status || '').toUpperCase();
    return status === 'PENDING' || status === 'FAILED';
  }).length;
}

function NotificationItem({ item }: { item: BackendNotificationMessage }) {
  const status = item.status || 'UNKNOWN';
  const style = getStatusStyle(status);
  const body = getMessageBody(item);

  return (
    <article className="rounded-3xl border border-border bg-white px-4 py-4 shadow-soft transition hover:-translate-y-0.5 hover:shadow-[0_18px_50px_rgba(15,23,42,0.08)] sm:px-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-4 text-right">
          <div
            className={[
              'flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl',
              style.iconBox,
            ].join(' ')}
          >
            {(item.channel || '').toLowerCase() === 'sms' ? (
              <Smartphone className="h-5 w-5" />
            ) : (
              <MessageCircle className="h-5 w-5" />
            )}
          </div>

          <div className="min-w-0">
            <h3 className="text-base font-extrabold text-text">
              {getMessageTitle(item)}
            </h3>

            <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-7 text-slate-600">
              {body}
            </p>

            <div className="mt-3 flex flex-wrap items-center justify-start gap-x-4 gap-y-1 text-xs text-slate-500 sm:justify-end">
              <span>{item.recipient_masked || item.recipient || 'گیرنده نامشخص'}</span>
              <span>{item.provider || 'Provider نامشخص'}</span>
              <span>{formatDate(item.sent_at || item.last_attempt_at || item.created_at)}</span>
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:flex-col sm:items-end">
          <span
            className={[
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ring-1',
              style.badge,
            ].join(' ')}
          >
            {style.icon}
            {getStatusLabel(status)}
          </span>

          {item.retry_count ? (
            <span className="rounded-2xl bg-slate-50 px-3 py-2 text-xs font-bold text-slate-500">
              تلاش: {item.retry_count.toLocaleString('fa-IR')}
            </span>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function SummaryPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-border bg-slate-50 px-4 py-3 text-right">
      <div className="text-xs font-semibold text-muted">{label}</div>
      <div className="mt-1 text-xl font-extrabold text-text">{value.toLocaleString('fa-IR')}</div>
    </div>
  );
}

export function NotificationsPage({ onUnreadCountChange }: NotificationsPageProps) {
  const { notify } = useFeedback();

  const [messages, setMessages] = useState<BackendNotificationMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [search, setSearch] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [testMessage, setTestMessage] = useState('سلام از همدنگ');
  const [sending, setSending] = useState(false);

  const counts = useMemo(() => {
    const pending = messages.filter((item) => (item.status || '').toUpperCase() === 'PENDING').length;
    const failed = messages.filter((item) => (item.status || '').toUpperCase() === 'FAILED').length;
    const sent = messages.filter((item) => ['SENT', 'DELIVERED'].includes((item.status || '').toUpperCase())).length;

    return { pending, failed, sent };
  }, [messages]);

  const filteredMessages = useMemo(() => {
    const query = search.trim().toLowerCase();

    return messages.filter((item) => {
      if (statusFilter !== 'all' && (item.status || '').toUpperCase() !== statusFilter) {
        return false;
      }

      if (!query) return true;
      return getSearchText(item).includes(query);
    });
  }, [messages, search, statusFilter]);

  async function loadMessages() {
    try {
      setLoading(true);
      setError(null);

      const data = await getNotificationMessages();
      setMessages(data);
      onUnreadCountChange?.(getPendingOrFailedCount(data));
    } catch (err) {
      console.error(err);
      setError('پیام‌ها دریافت نشدند. اتصال notification-service را بررسی کن.');
      setMessages([]);
      onUnreadCountChange?.(0);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSendTestSms() {
    if (!phoneNumber.trim() || !testMessage.trim()) {
      notify({
        type: 'error',
        title: 'شماره و متن پیام را وارد کن',
      });
      return;
    }

    try {
      setSending(true);

      const result = await sendTestSms({
        phone_number: phoneNumber,
        message: testMessage,
      });

      notify({
        type: 'success',
        title: 'درخواست پیامک ارسال شد',
        description: result.message_id ? `شناسه پیام: ${result.message_id}` : result.status,
      });

      setPhoneNumber('');
      await loadMessages();
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'ارسال پیامک ناموفق بود',
      });
    } finally {
      setSending(false);
    }
  }

  return (
    <main className="px-4 py-6 sm:px-6 xl:px-8">
      <div className="mx-auto max-w-[1180px] space-y-6">
        <section className="rounded-3xl border border-border bg-white p-6 shadow-soft">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="text-right">
              <h1 className="text-[32px] font-extrabold tracking-[-0.03em] text-text">
                اعلان‌ها
              </h1>
              <p className="mt-2 text-sm leading-7 text-muted">
                آخرین پیامک‌ها و وضعیت ارسال پیام‌های سیستم را اینجا ببین.
              </p>
            </div>

            <button
              type="button"
              onClick={loadMessages}
              disabled={loading}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border bg-white px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className="h-4 w-4" />
              {loading ? 'در حال بروزرسانی...' : 'بروزرسانی'}
            </button>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
          <div className="space-y-5">
            <div className="rounded-3xl border border-border bg-white p-5 shadow-soft">
              <div className="grid gap-3 sm:grid-cols-3">
                <SummaryPill label="همه پیام‌ها" value={messages.length} />
                <SummaryPill label="ارسال‌شده" value={counts.sent} />
                <SummaryPill label="نیازمند بررسی" value={counts.pending + counts.failed} />
              </div>

              <div className="mt-5 flex flex-col gap-3 lg:flex-row lg:items-center">
                <div className="relative min-w-0 flex-1">
                  <Search className="pointer-events-none absolute right-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" />
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="جستجو در پیام‌ها، شماره یا خطا..."
                    className="h-12 w-full rounded-2xl border border-border bg-white pr-11 pl-4 text-right text-sm outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {statusTabs.map((tab) => (
                    <button
                      key={tab.value}
                      type="button"
                      onClick={() => setStatusFilter(tab.value)}
                      className={[
                        'h-10 rounded-2xl px-4 text-sm font-bold transition',
                        statusFilter === tab.value
                          ? 'bg-emerald-600 text-white shadow-[0_10px_22px_rgba(16,185,129,0.20)]'
                          : 'border border-border bg-white text-slate-600 hover:bg-slate-50',
                      ].join(' ')}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {error ? (
              <div className="rounded-3xl border border-rose-100 bg-rose-50 p-5 text-center text-sm font-bold text-rose-600">
                {error}
              </div>
            ) : null}

            {loading ? (
              <div className="rounded-3xl border border-border bg-white p-8 text-center text-sm text-muted shadow-soft">
                در حال دریافت پیام‌ها...
              </div>
            ) : null}

            {!loading && filteredMessages.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-emerald-200 bg-emerald-50/40 p-10 text-center shadow-soft">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-white text-emerald-600 shadow-sm">
                  <Bell className="h-7 w-7" />
                </div>
                <h2 className="text-xl font-extrabold text-text">اعلانی برای نمایش نیست</h2>
                <p className="mt-2 text-sm leading-7 text-muted">
                  بعد از ارسال OTP، یادآوری یا پیامک تست، پیام‌ها اینجا نمایش داده می‌شوند.
                </p>
              </div>
            ) : null}

            <div className="space-y-3">
              {filteredMessages.map((item) => (
                <NotificationItem key={item.id} item={item} />
              ))}
            </div>
          </div>

          <aside className="rounded-3xl border border-border bg-white p-6 shadow-soft xl:sticky xl:top-[118px] xl:h-fit">
            <div className="mb-5 flex items-center justify-between">
              <div className="text-right">
                <h2 className="text-xl font-extrabold text-text">ارسال پیام تست</h2>
                <p className="mt-1 text-sm leading-7 text-muted">
                  یک SMS ساده برای بررسی سرویس بفرست.
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                <Send className="h-5 w-5" />
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-bold text-text">شماره موبایل</label>
                <input
                  dir="ltr"
                  value={phoneNumber}
                  onChange={(event) => setPhoneNumber(event.target.value)}
                  placeholder="09123456789"
                  className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-left text-sm outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-bold text-text">متن پیام</label>
                <textarea
                  value={testMessage}
                  onChange={(event) => setTestMessage(event.target.value)}
                  className="min-h-[96px] w-full resize-none rounded-2xl border border-border bg-white px-4 py-3 text-right text-sm leading-7 outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                />
              </div>

              <button
                type="button"
                onClick={handleSendTestSms}
                disabled={sending}
                className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-5 text-sm font-bold text-white shadow-[0_12px_28px_rgba(0,168,107,0.18)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Send className="h-4.5 w-4.5" />
                {sending ? 'در حال ارسال...' : 'ارسال پیام'}
              </button>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
