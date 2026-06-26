import { type ReactNode, useEffect, useMemo, useState } from 'react';
import {
  Bell,
  Check,
  CheckCheck,
  Mail,
  RefreshCw,
  Search,
  Send,
} from 'lucide-react';
import {
  getNotificationMessages,
  getNotifications,
  markAllNotificationsAsRead,
  markNotificationMessageAsRead,
  sendNotificationEmailTest,
  type BackendNotificationMessage,
} from '../lib/notificationApi';
import { useFeedback } from '../components/feedback/FeedbackProvider';
import {
  getFriendlyApiErrorMessage,
  getFriendlyNotificationBody,
  getFriendlyNotificationCode,
  getFriendlyNotificationTitle,
} from '../lib/userMessages';

interface NotificationsPageProps {
  onUnreadCountChange?: (count: number) => void;
}

type ViewFilter = 'all' | 'unread' | 'read';
type DataSource = 'notifications' | 'messages';

const viewTabs: Array<{ value: ViewFilter; label: string }> = [
  { value: 'all', label: 'همه' },
  { value: 'unread', label: 'خوانده‌نشده' },
  { value: 'read', label: 'خوانده‌شده' },
];

const sourceTabs: Array<{ value: DataSource; label: string; description: string }> = [
  {
    value: 'notifications',
    label: 'اعلان‌های من',
    description: 'اعلان‌هایی که برای حساب تو ثبت شده‌اند.',
  },
  {
    value: 'messages',
    label: 'پیام‌های اخیر',
    description: 'پیام‌هایی که آماده نمایش به کاربر هستند.',
  },
];

const READ_STORAGE_KEY = 'hamdong.read-notification-ids';

interface EmailTestFormState {
  email: string;
  subject: string;
  message: string;
}

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
    return 'زمان نامشخص';
  }
}

function loadPersistedReadIds() {
  if (typeof window === 'undefined') return new Set<string>();

  try {
    const raw = window.localStorage.getItem(READ_STORAGE_KEY);
    if (!raw) return new Set<string>();

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set<string>();

    return new Set(parsed.filter((value): value is string => typeof value === 'string'));
  } catch {
    return new Set<string>();
  }
}

function persistReadIds(ids: Set<string>) {
  if (typeof window === 'undefined') return;

  try {
    window.localStorage.setItem(READ_STORAGE_KEY, JSON.stringify(Array.from(ids)));
  } catch {
    // ignore local storage failures
  }
}

function isMessageRead(item: BackendNotificationMessage, localReadIds: Set<string>) {
  return Boolean(item.is_read || item.read_at || localReadIds.has(item.id));
}

function getUnreadCount(items: BackendNotificationMessage[], localReadIds: Set<string>) {
  return items.filter((item) => !isMessageRead(item, localReadIds)).length;
}

function getChannelLabel(channel?: string | null) {
  const value = (channel || '').toLowerCase();

  if (value === 'email') return 'ایمیل';
  if (value === 'sms') return 'پیامک';
  if (value === 'in_app' || value === 'push') return 'اعلان داخل برنامه';

  return 'اعلان';
}

function getChannelIcon(channel?: string | null) {
  const value = (channel || '').toLowerCase();

  if (value === 'email') {
    return <Mail className="h-5 w-5" />;
  }

  return <Bell className="h-5 w-5" />;
}

function getStatusLabel(status?: string | null) {
  const value = (status || '').toUpperCase();

  if (!value) return '';
  if (value === 'DELIVERED') return 'تحویل شده';
  if (value === 'SENT') return 'ارسال شده';
  if (value === 'FAILED') return 'ارسال نشد';
  if (value === 'PENDING') return 'در انتظار';
  if (value === 'CANCELED' || value === 'CANCELLED') return 'لغو شده';

  return '';
}

function getStatusClass(status?: string | null) {
  const value = (status || '').toUpperCase();

  if (value === 'DELIVERED' || value === 'SENT') {
    return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300';
  }

  if (value === 'FAILED') {
    return 'bg-rose-500/10 text-rose-700 dark:text-rose-300';
  }

  if (value === 'PENDING') {
    return 'bg-amber-500/10 text-amber-700 dark:text-amber-300';
  }

  return 'bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-300';
}

function toPrettyText(value: unknown) {
  if (typeof value === 'string') return value.trim();
  if (typeof value === 'number') return String(value);
  return '';
}

function toEnglishDigits(value: string) {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)));
}

function parseRecord(value: unknown): Record<string, unknown> | undefined {
  if (!value) return undefined;

  if (typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }

  if (typeof value !== 'string') {
    return undefined;
  }

  const text = value.trim();
  if (!text) return undefined;
  if (!(text.startsWith('{') && text.endsWith('}'))) return undefined;

  try {
    const parsed = JSON.parse(text) as unknown;
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    return undefined;
  }

  return undefined;
}

function readContext(item: BackendNotificationMessage) {
  return [
    parseRecord(item.template_context),
    parseRecord(item.metadata),
    parseRecord(item.data),
  ].reduce<Record<string, unknown>>((merged, record) => {
    if (!record) return merged;

    for (const [key, value] of Object.entries(record)) {
      if (value !== undefined && value !== null && value !== '') {
        merged[key] = value;
      }
    }

    return merged;
  }, {});
}

function pickString(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    const text = toPrettyText(value);

    if (text) {
      return text;
    }
  }

  return '';
}

function getGroupName(item: BackendNotificationMessage) {
  const context = readContext(item);

  return (
    pickString(context, [
      'group_name',
      'group_title',
      'group_display_name',
      'team_name',
      'group',
      'team',
    ]) || ''
  );
}

function getAmountText(item: BackendNotificationMessage) {
  const context = readContext(item);
  const rawAmount = pickString(context, [
    'amount',
    'total_amount',
    'payable_amount',
    'amount_due',
    'due_amount',
    'share_amount',
    'settlement_amount',
    'outstanding_amount',
    'receivable_amount',
    'amount_minor',
  ]);

  if (!rawAmount) {
    return '';
  }

  const normalized = toEnglishDigits(rawAmount).replace(/[^0-9.-]/g, '');
  const amount = Number(normalized);

  if (!Number.isFinite(amount)) {
    return '';
  }

  return `${amount.toLocaleString('fa-IR')} تومان`;
}

function isPaymentReminder(item: BackendNotificationMessage) {
  const haystack = [
    item.notification_type,
    item.message_type,
    item.template_code,
    item.title,
    getFriendlyNotificationTitle(item),
    getFriendlyNotificationBody(item),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  return /payment|payable|debt|settlement|reminder|expense|پرداخت|تسویه|هزینه/.test(haystack);
}

function getNotificationBodyText(item: BackendNotificationMessage) {
  const friendlyBody = getFriendlyNotificationBody(item);
  return friendlyBody || 'جزئیات این اعلان در دسترس نیست.';
}

function getNotificationSearchText(item: BackendNotificationMessage) {
  return [
    getFriendlyNotificationTitle(item),
    getNotificationBodyText(item),
    getChannelLabel(item.channel),
    getGroupName(item),
    getAmountText(item),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function getActionErrorMessage(error: unknown, fallback: string) {
  return getFriendlyApiErrorMessage(error, {
    defaultMessage: fallback,
    invalidMessage: 'اطلاعات واردشده کامل یا درست نیست.',
    unavailableMessage: 'فعلاً ارتباط با بخش اعلان‌ها برقرار نمی‌شود. کمی بعد دوباره تلاش کن.',
    notFoundMessage: 'اطلاعات اعلان پیدا نشد.',
    codeMap: {
      NOTIFICATION_NOT_FOUND: 'این اعلان پیدا نشد.',
      ALREADY_READ: 'این اعلان قبلاً خوانده شده است.',
      EMAIL_SEND_FAILED: 'ارسال ایمیل انجام نشد. کمی بعد دوباره تلاش کن.',
      INVALID_EMAIL: 'ایمیل واردشده درست نیست.',
    },
  });
}

function SummaryCard({
  title,
  value,
  tone = 'default',
}: {
  title: string;
  value: string;
  tone?: 'default' | 'success' | 'info' | 'warning';
}) {
  const toneClass =
    tone === 'success'
      ? 'border-emerald-500/15 bg-emerald-500/5 dark:bg-emerald-500/10'
      : tone === 'info'
        ? 'border-sky-500/15 bg-sky-500/5 dark:bg-sky-500/10'
        : tone === 'warning'
          ? 'border-amber-500/15 bg-amber-500/5 dark:bg-amber-500/10'
          : 'border-border bg-white dark:bg-white/[0.03]';

  return (
    <div className={`rounded-3xl border px-5 py-4 text-right ${toneClass}`}>
      <div className="text-xs font-semibold text-muted">{title}</div>
      <div className="mt-2 text-3xl font-extrabold text-text">{value}</div>
    </div>
  );
}

function ChannelSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="h-11 w-full rounded-2xl border border-border bg-white px-4 text-right text-sm text-slate-700 outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 dark:bg-white/[0.03] dark:text-slate-200"
    >
      <option value="">همه کانال‌ها</option>
      <option value="in_app">اعلان داخل برنامه</option>
      <option value="push">اعلان</option>
      <option value="email">ایمیل</option>
    </select>
  );
}

function FieldLabel({ children }: { children: string }) {
  return <label className="mb-2 block text-right text-xs font-bold text-muted">{children}</label>;
}

function SectionCard({
  title,
  description,
  icon,
  children,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[28px] border border-border bg-white p-5 shadow-soft dark:bg-white/[0.03]">
      <div className="flex items-start gap-3">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-300">
          {icon}
        </div>
        <div className="min-w-0 text-right">
          <h2 className="text-lg font-extrabold text-text">{title}</h2>
          <p className="mt-1 text-sm leading-7 text-muted">{description}</p>
        </div>
      </div>

      <div className="mt-5">{children}</div>
    </section>
  );
}

interface NotificationItemProps {
  item: BackendNotificationMessage;
  read: boolean;
  marking: boolean;
  onMarkAsRead: (item: BackendNotificationMessage) => void;
}

function NotificationItem({
  item,
  read,
  marking,
  onMarkAsRead,
}: NotificationItemProps) {
  const code = getFriendlyNotificationCode(item);
  const body = getNotificationBodyText(item);
  const statusLabel = getStatusLabel(item.status);
  const amountText = getAmountText(item);
  const groupName = getGroupName(item);

  return (
    <article
      className={[
        'overflow-hidden rounded-[28px] border p-5 shadow-soft transition sm:p-6',
        read
          ? 'border-border bg-white dark:bg-white/[0.03]'
          : 'border-emerald-500/20 bg-[linear-gradient(180deg,rgba(16,185,129,0.08),rgba(255,255,255,0))] dark:bg-[linear-gradient(180deg,rgba(16,185,129,0.08),rgba(255,255,255,0.03))]',
      ].join(' ')}
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 flex-1 items-start gap-4 text-right">
          <div
            className={[
              'flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl',
              read
                ? 'bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-300'
                : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-300',
            ].join(' ')}
          >
            {getChannelIcon(item.channel)}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center justify-start gap-2 sm:justify-end">
              <h3 className="text-lg font-extrabold text-text">
                {getFriendlyNotificationTitle(item)}
              </h3>

              <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-bold text-slate-600 dark:bg-white/5 dark:text-slate-300">
                {getChannelLabel(item.channel)}
              </span>

              {statusLabel ? (
                <span
                  className={[
                    'inline-flex items-center rounded-full px-3 py-1 text-[11px] font-bold',
                    getStatusClass(item.status),
                  ].join(' ')}
                >
                  {statusLabel}
                </span>
              ) : null}

              <span
                className={[
                  'inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-bold',
                  read
                    ? 'bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-300'
                    : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
                ].join(' ')}
              >
                {read ? (
                  <CheckCheck className="h-3.5 w-3.5" />
                ) : (
                  <Bell className="h-3.5 w-3.5" />
                )}
                {read ? 'خوانده شد' : 'جدید'}
              </span>
            </div>

            <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-8 text-slate-600 dark:text-slate-300">
              {body}
            </p>

            {amountText || groupName ? (
              <div className="mt-4 flex flex-wrap items-center justify-start gap-2 sm:justify-end">
                {groupName ? (
                  <span className="rounded-full bg-sky-500/10 px-3 py-1 text-xs font-bold text-sky-700 dark:text-sky-300">
                    گروه: {groupName}
                  </span>
                ) : null}

                {amountText ? (
                  <span className="rounded-full bg-amber-500/10 px-3 py-1 text-xs font-bold text-amber-700 dark:text-amber-300">
                    مبلغ: {amountText}
                  </span>
                ) : null}
              </div>
            ) : null}

            <div className="mt-4 flex flex-wrap items-center justify-start gap-2 text-xs font-medium text-slate-500 dark:text-slate-400 sm:justify-end">
              <span>{formatDate(item.sent_at || item.last_attempt_at || item.created_at)}</span>
            </div>

            {code ? (
              <div className="mt-4 inline-flex min-h-12 items-center gap-3 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 text-right dark:bg-emerald-500/10">
                <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">
                  کد تایید
                </span>
                <span className="font-mono text-base font-extrabold tracking-[0.35em] text-emerald-700 dark:text-emerald-200">
                  {code}
                </span>
              </div>
            ) : null}
          </div>
        </div>

        {!read ? (
          <button
            type="button"
            onClick={() => onMarkAsRead(item)}
            disabled={marking}
            className="inline-flex h-11 shrink-0 items-center justify-center gap-2 self-end rounded-2xl bg-emerald-600 px-4 text-sm font-bold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Check className="h-4 w-4" />
            {marking ? 'در حال ثبت...' : 'خواندم'}
          </button>
        ) : null}
      </div>
    </article>
  );
}

function EmptyState({
  source,
  filter,
}: {
  source: DataSource;
  filter: ViewFilter;
}) {
  const title =
    filter === 'unread'
      ? 'اعلان خوانده‌نشده‌ای نداری'
      : filter === 'read'
        ? 'اعلان خوانده‌شده‌ای برای نمایش نیست'
        : source === 'messages'
          ? 'پیامی برای نمایش پیدا نشد'
          : 'اعلانی برای نمایش پیدا نشد';

  const description =
    filter === 'all'
      ? 'هر اعلان جدیدی که ثبت شود همین‌جا نمایش داده می‌شود.'
      : 'فیلتر را تغییر بده یا دوباره صفحه را بروزرسانی کن.';

  return (
    <div className="rounded-[28px] border border-dashed border-border bg-white px-5 py-12 text-center shadow-soft dark:bg-white/[0.03]">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500 dark:bg-white/5 dark:text-slate-300">
        <Bell className="h-6 w-6" />
      </div>
      <h3 className="mt-4 text-lg font-extrabold text-text">{title}</h3>
      <p className="mt-2 text-sm leading-7 text-muted">{description}</p>
    </div>
  );
}

export function NotificationsPage({ onUnreadCountChange }: NotificationsPageProps) {
  const { notify } = useFeedback();
  const [notifications, setNotifications] = useState<BackendNotificationMessage[]>([]);
  const [messages, setMessages] = useState<BackendNotificationMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<DataSource>('notifications');
  const [viewFilter, setViewFilter] = useState<ViewFilter>('all');
  const [search, setSearch] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [markingIds, setMarkingIds] = useState<string[]>([]);
  const [localReadIds, setLocalReadIds] = useState<Set<string>>(() => loadPersistedReadIds());
  const [emailTestForm, setEmailTestForm] = useState<EmailTestFormState>({
    email: '',
    subject: '',
    message: '',
  });

  const activeItems = useMemo(
    () => (dataSource === 'notifications' ? notifications : messages),
    [dataSource, messages, notifications],
  );

  const totalNotificationsCount = notifications.length;
  const totalMessagesCount = messages.length;

  const unreadCount = useMemo(
    () => getUnreadCount(activeItems, localReadIds),
    [activeItems, localReadIds],
  );

  const readCount = useMemo(
    () => activeItems.filter((item) => isMessageRead(item, localReadIds)).length,
    [activeItems, localReadIds],
  );

  const paymentReminders = useMemo(
    () =>
      activeItems.filter((item) => !isMessageRead(item, localReadIds) && isPaymentReminder(item)),
    [activeItems, localReadIds],
  );

  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase();

    return activeItems.filter((item) => {
      const read = isMessageRead(item, localReadIds);
      const channel = (item.channel || '').toLowerCase();

      if (viewFilter === 'read' && !read) return false;
      if (viewFilter === 'unread' && read) return false;
      if (channelFilter && channel !== channelFilter.toLowerCase()) return false;
      if (!query) return true;

      return getNotificationSearchText(item).includes(query);
    });
  }, [activeItems, channelFilter, localReadIds, search, viewFilter]);

  useEffect(() => {
    persistReadIds(localReadIds);
    onUnreadCountChange?.(getUnreadCount(notifications, localReadIds));
  }, [localReadIds, notifications, onUnreadCountChange]);

  async function loadNotificationsPage() {
    try {
      setLoading(true);
      setError(null);

      const [notificationResult, messagesResult] = await Promise.allSettled([
        getNotifications({ limit: 100 }),
        getNotificationMessages({ limit: 100 }),
      ]);

      if (notificationResult.status === 'rejected' && messagesResult.status === 'rejected') {
        throw notificationResult.reason || messagesResult.reason;
      }

      const notificationList = notificationResult.status === 'fulfilled' ? notificationResult.value : [];
      const recentMessages = messagesResult.status === 'fulfilled' ? messagesResult.value : [];

      if (notificationResult.status === 'rejected' || messagesResult.status === 'rejected') {
        console.warn('One notification source failed, rendering the available source.', {
          notificationError: notificationResult.status === 'rejected' ? notificationResult.reason : undefined,
          messagesError: messagesResult.status === 'rejected' ? messagesResult.reason : undefined,
        });
      }

      setNotifications(
        notificationList.map((item) =>
          localReadIds.has(item.id)
            ? {
                ...item,
                is_read: true,
                read_at: item.read_at || new Date().toISOString(),
              }
            : item,
        ),
      );

      setMessages(
        recentMessages.map((item) =>
          localReadIds.has(item.id)
            ? {
                ...item,
                is_read: true,
                read_at: item.read_at || new Date().toISOString(),
              }
            : item,
        ),
      );
    } catch (loadError) {
      const message = getActionErrorMessage(
        loadError,
        'فعلاً اعلان‌ها در دسترس نیستند. کمی بعد دوباره تلاش کن.',
      );
      setError(message);
      setNotifications([]);
      setMessages([]);
      onUnreadCountChange?.(0);

      notify({
        type: 'error',
        title: 'اعلان‌ها بارگذاری نشدند',
        description: message,
      });
    } finally {
      setLoading(false);
    }
  }

  function updateLocalReadState(notificationId: string) {
    setLocalReadIds((current) => {
      const next = new Set(current);
      next.add(notificationId);
      return next;
    });

    const readAt = new Date().toISOString();

    setNotifications((current) =>
      current.map((item) =>
        item.id === notificationId
          ? {
              ...item,
              is_read: true,
              read_at: item.read_at || readAt,
            }
          : item,
      ),
    );

    setMessages((current) =>
      current.map((item) =>
        item.id === notificationId
          ? {
              ...item,
              is_read: true,
              read_at: item.read_at || readAt,
            }
          : item,
      ),
    );
  }

  async function handleMarkAsRead(item: BackendNotificationMessage) {
    if (isMessageRead(item, localReadIds)) {
      return;
    }

    setMarkingIds((current) => [...current, item.id]);
    updateLocalReadState(item.id);

    try {
      await markNotificationMessageAsRead(item.id);
    } catch (markError) {
      notify({
        type: 'info',
        title: 'اعلان برای این دستگاه خوانده شد',
        description:
          'وضعیت خواندن روی این دستگاه ثبت شد. اگر کمی بعد دوباره همگام نشد، صفحه را بروزرسانی کن.',
      });
      console.warn(markError);
    } finally {
      setMarkingIds((current) => current.filter((id) => id !== item.id));
    }
  }

  async function handleMarkAllRead() {
    try {
      setActionLoading('read-all');
      await markAllNotificationsAsRead();

      const now = new Date().toISOString();
      const ids = [...notifications.map((item) => item.id), ...messages.map((item) => item.id)];

      setLocalReadIds((current) => {
        const next = new Set(current);

        for (const id of ids) {
          next.add(id);
        }

        return next;
      });

      setNotifications((current) =>
        current.map((item) => ({ ...item, is_read: true, read_at: item.read_at || now })),
      );
      setMessages((current) =>
        current.map((item) => ({ ...item, is_read: true, read_at: item.read_at || now })),
      );

      notify({
        type: 'success',
        title: 'همه اعلان‌ها خوانده شدند',
        description: 'دیگر اعلان خوانده‌نشده‌ای در این صفحه باقی نماند.',
      });
    } catch (markAllError) {
      notify({
        type: 'error',
        title: 'ثبت وضعیت اعلان‌ها انجام نشد',
        description: getActionErrorMessage(
          markAllError,
          'فعلاً امکان ثبت خوانده شدن همه اعلان‌ها وجود ندارد.',
        ),
      });
    } finally {
      setActionLoading(null);
    }
  }

  async function handleSendEmailTest() {
    if (!emailTestForm.email.trim()) {
      notify({
        type: 'error',
        title: 'ایمیل وارد نشده',
        description: 'برای ارسال تست، ایمیل گیرنده را وارد کن.',
      });
      return;
    }

    if (!emailTestForm.message.trim()) {
      notify({
        type: 'error',
        title: 'متن ایمیل خالی است',
        description: 'متن کوتاهی برای ایمیل تستی بنویس.',
      });
      return;
    }

    try {
      setActionLoading('email-test');
      await sendNotificationEmailTest({
        email: emailTestForm.email.trim(),
        recipient_email: emailTestForm.email.trim(),
        subject: emailTestForm.subject.trim() || 'تست اعلان ایمیلی',
        title: emailTestForm.subject.trim() || 'تست اعلان ایمیلی',
        message: emailTestForm.message.trim(),
        body: emailTestForm.message.trim(),
        content: emailTestForm.message.trim(),
      });

      setEmailTestForm({
        email: '',
        subject: '',
        message: '',
      });

      notify({
        type: 'success',
        title: 'ایمیل تستی ارسال شد',
        description: 'اگر سرویس ایمیل فعال باشد، پیام تست برای این آدرس ارسال می‌شود.',
      });
    } catch (emailError) {
      notify({
        type: 'error',
        title: 'ارسال ایمیل انجام نشد',
        description: getActionErrorMessage(
          emailError,
          'ارسال ایمیل تستی انجام نشد. کمی بعد دوباره تلاش کن.',
        ),
      });
    } finally {
      setActionLoading(null);
    }
  }

  useEffect(() => {
    void loadNotificationsPage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="px-4 py-6 sm:px-6 xl:px-8">
      <div className="mx-auto max-w-[1320px] space-y-6">
        <section className="overflow-hidden rounded-[32px] border border-border bg-[linear-gradient(135deg,rgba(15,23,42,0.02),rgba(16,185,129,0.08))] p-6 shadow-soft dark:bg-[linear-gradient(135deg,rgba(255,255,255,0.03),rgba(16,185,129,0.08))]">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
            <div className="text-right">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-300">
                <Bell className="h-6 w-6" />
              </div>

              <h1 className="mt-4 text-[32px] font-extrabold tracking-[-0.03em] text-text">
                اعلان‌ها
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-7 text-muted">
                اینجا می‌توانی اعلان‌های جدیدت را ببینی، آن‌ها را به‌عنوان خوانده‌شده ثبت کنی و
                یادآوری‌های پرداخت را با مبلغ و نام گروه راحت‌تر دنبال کنی.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <SummaryCard
                title="همه اعلان‌ها"
                value={totalNotificationsCount.toLocaleString('fa-IR')}
                tone="success"
              />
              <SummaryCard
                title="پیام‌های اخیر"
                value={totalMessagesCount.toLocaleString('fa-IR')}
                tone="info"
              />
              <SummaryCard
                title="خوانده‌نشده"
                value={unreadCount.toLocaleString('fa-IR')}
                tone="warning"
              />
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1.65fr)_minmax(320px,0.95fr)]">
          <div className="space-y-6">
            <div className="rounded-[28px] border border-border bg-white p-5 shadow-soft dark:bg-white/[0.03]">
              <div className="flex flex-col gap-4">
                <div className="flex flex-wrap items-center gap-2">
                  {sourceTabs.map((tab) => (
                    <button
                      key={tab.value}
                      type="button"
                      onClick={() => setDataSource(tab.value)}
                      className={[
                        'inline-flex h-11 items-center justify-center rounded-2xl px-4 text-sm font-bold transition',
                        dataSource === tab.value
                          ? 'bg-emerald-600 text-white shadow-[0_10px_22px_rgba(16,185,129,0.20)]'
                          : 'border border-border bg-white text-slate-600 hover:bg-slate-50 dark:bg-white/[0.03] dark:text-slate-300 dark:hover:bg-white/[0.05]',
                      ].join(' ')}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <p className="text-right text-sm leading-7 text-muted">
                  {sourceTabs.find((tab) => tab.value === dataSource)?.description}
                </p>

                <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_220px_220px]">
                  <div className="relative min-w-0">
                    <Search className="pointer-events-none absolute right-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" />
                    <input
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      placeholder="جستجو در عنوان، متن، گروه یا مبلغ..."
                      className="h-12 w-full rounded-2xl border border-border bg-white pr-11 pl-4 text-right text-sm outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 dark:bg-white/[0.03]"
                    />
                  </div>

                  <ChannelSelect value={channelFilter} onChange={setChannelFilter} />

                  <button
                    type="button"
                    onClick={() => void loadNotificationsPage()}
                    disabled={loading}
                    className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-border bg-white px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white/[0.03] dark:text-slate-200 dark:hover:bg-white/[0.05]"
                  >
                    <RefreshCw className="h-4 w-4" />
                    {loading ? 'در حال بروزرسانی...' : 'بروزرسانی'}
                  </button>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    {viewTabs.map((tab) => {
                      const count =
                        tab.value === 'all'
                          ? activeItems.length
                          : tab.value === 'read'
                            ? readCount
                            : unreadCount;

                      return (
                        <button
                          key={tab.value}
                          type="button"
                          onClick={() => setViewFilter(tab.value)}
                          className={[
                            'inline-flex h-11 items-center justify-center gap-2 rounded-2xl px-4 text-sm font-bold transition',
                            viewFilter === tab.value
                              ? 'bg-emerald-600 text-white shadow-[0_10px_22px_rgba(16,185,129,0.20)]'
                              : 'border border-border bg-white text-slate-600 hover:bg-slate-50 dark:bg-white/[0.03] dark:text-slate-300 dark:hover:bg-white/[0.05]',
                          ].join(' ')}
                        >
                          <span>{tab.label}</span>
                          <span
                            className={[
                              'inline-flex min-w-7 items-center justify-center rounded-full px-2 py-0.5 text-[11px]',
                              viewFilter === tab.value
                                ? 'bg-white/20'
                                : 'bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-300',
                            ].join(' ')}
                          >
                            {count.toLocaleString('fa-IR')}
                          </span>
                        </button>
                      );
                    })}
                  </div>

                  <button
                    type="button"
                    onClick={handleMarkAllRead}
                    disabled={actionLoading === 'read-all' || activeItems.length === 0}
                    className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-emerald-600 px-4 text-sm font-bold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <CheckCheck className="h-4 w-4" />
                    {actionLoading === 'read-all' ? 'در حال ثبت...' : 'خواندن همه'}
                  </button>
                </div>
              </div>
            </div>

            {error ? (
              <div className="rounded-[28px] border border-rose-100 bg-rose-50 p-5 text-center text-sm font-bold leading-7 text-rose-600 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300">
                {error}
              </div>
            ) : null}

            {loading ? (
              <div className="rounded-[28px] border border-border bg-white p-8 text-center text-sm text-muted shadow-soft dark:bg-white/[0.03]">
                در حال دریافت اعلان‌ها...
              </div>
            ) : null}

            {!loading && filteredItems.length === 0 ? (
              <EmptyState source={dataSource} filter={viewFilter} />
            ) : null}

            <div className="space-y-4">
              {filteredItems.map((item) => (
                <NotificationItem
                  key={`${dataSource}-${item.id}`}
                  item={item}
                  read={isMessageRead(item, localReadIds)}
                  marking={markingIds.includes(item.id)}
                  onMarkAsRead={handleMarkAsRead}
                />
              ))}
            </div>
          </div>

          <div className="space-y-6">
            <SectionCard
              title="یادآوری‌های پرداخت"
              description="اگر اعلان پرداختی داشته باشی، مبلغ و نام گروه اینجا واضح‌تر نمایش داده می‌شود."
              icon={<Bell className="h-5 w-5" />}
            >
              {paymentReminders.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-border px-5 py-8 text-center text-sm leading-7 text-muted">
                  فعلاً یادآوری پرداخت خوانده‌نشده‌ای نداری.
                </div>
              ) : (
                <div className="space-y-3">
                  {paymentReminders.slice(0, 6).map((item) => (
                    <div
                      key={`payment-${item.id}`}
                      className="rounded-3xl border border-border bg-slate-50 px-4 py-4 text-right dark:bg-white/[0.04]"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <h3 className="text-sm font-extrabold text-text">
                          {getFriendlyNotificationTitle(item)}
                        </h3>
                        <span className="text-xs font-medium text-muted">
                          {formatDate(item.sent_at || item.last_attempt_at || item.created_at)}
                        </span>
                      </div>

                      <p className="mt-2 text-sm leading-7 text-slate-600 dark:text-slate-300">
                        {getNotificationBodyText(item)}
                      </p>

                      <div className="mt-3 flex flex-wrap items-center justify-start gap-2 sm:justify-end">
                        <span className="rounded-full bg-sky-500/10 px-3 py-1 text-xs font-bold text-sky-700 dark:text-sky-300">
                          گروه: {getGroupName(item) || 'نامشخص'}
                        </span>
                        <span className="rounded-full bg-amber-500/10 px-3 py-1 text-xs font-bold text-amber-700 dark:text-amber-300">
                          مبلغ: {getAmountText(item) || 'نامشخص'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>

            <SectionCard
              title="ارسال تست ایمیل"
              description="برای بررسی سرویس ایمیل، یک پیام تستی برای آدرس دلخواهت بفرست."
              icon={<Mail className="h-5 w-5" />}
            >
              <div className="space-y-4">
                <div>
                  <FieldLabel>ایمیل گیرنده</FieldLabel>
                  <input
                    type="email"
                    value={emailTestForm.email}
                    onChange={(event) =>
                      setEmailTestForm((current) => ({
                        ...current,
                        email: event.target.value,
                      }))
                    }
                    className="h-11 w-full rounded-2xl border border-border bg-white px-4 text-left text-sm outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 dark:bg-white/[0.03]"
                    dir="ltr"
                    placeholder="user@example.com"
                  />
                </div>

                <div>
                  <FieldLabel>موضوع</FieldLabel>
                  <input
                    value={emailTestForm.subject}
                    onChange={(event) =>
                      setEmailTestForm((current) => ({
                        ...current,
                        subject: event.target.value,
                      }))
                    }
                    className="h-11 w-full rounded-2xl border border-border bg-white px-4 text-right text-sm outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 dark:bg-white/[0.03]"
                    placeholder="مثلاً یادآوری پرداخت"
                  />
                </div>

                <div>
                  <FieldLabel>متن ایمیل</FieldLabel>
                  <textarea
                    value={emailTestForm.message}
                    onChange={(event) =>
                      setEmailTestForm((current) => ({
                        ...current,
                        message: event.target.value,
                      }))
                    }
                    rows={4}
                    className="w-full rounded-2xl border border-border bg-white px-4 py-3 text-right text-sm leading-7 outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 dark:bg-white/[0.03]"
                    placeholder="متن ایمیل تستی را اینجا بنویس..."
                  />
                </div>

                <button
                  type="button"
                  onClick={handleSendEmailTest}
                  disabled={actionLoading === 'email-test'}
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-sky-600 px-4 text-sm font-bold text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Send className="h-4 w-4" />
                  {actionLoading === 'email-test' ? 'در حال ارسال...' : 'ارسال ایمیل تستی'}
                </button>
              </div>
            </SectionCard>
          </div>
        </section>
      </div>
    </main>
  );
}
