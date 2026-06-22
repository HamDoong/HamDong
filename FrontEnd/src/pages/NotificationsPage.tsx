import { useEffect, useMemo, useState } from 'react';
import {
  Bell,
  Check,
  CheckCheck,
  Mail,
  RefreshCw,
  Search,
} from 'lucide-react';
import {
  getNotificationMessages,
  markNotificationMessageAsRead,
  type BackendNotificationMessage,
} from '../lib/notificationApi';
import { useFeedback } from '../components/feedback/FeedbackProvider';
import {
  getFriendlyNotificationBody,
  getFriendlyNotificationCode,
  getFriendlyNotificationTitle,
} from '../lib/userMessages';

interface NotificationsPageProps {
  onUnreadCountChange?: (count: number) => void;
}

type ViewFilter = 'all' | 'read';

const viewTabs: Array<{ value: ViewFilter; label: string }> = [
  { value: 'all', label: 'همه' },
  { value: 'read', label: 'خوانده‌شده‌ها' },
];

const READ_STORAGE_KEY = 'hamdong.read-notification-ids';

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
    // local persistence is only a fallback for local UX
  }
}

function isMessageRead(item: BackendNotificationMessage, localReadIds: Set<string>) {
  return Boolean(item.is_read || item.read_at || localReadIds.has(item.id));
}

function getUnreadCount(
  items: BackendNotificationMessage[],
  localReadIds: Set<string>,
) {
  return items.filter((item) => !isMessageRead(item, localReadIds)).length;
}

function getChannelLabel(channel?: string | null) {
  const value = (channel || '').toLowerCase();

  if (value === 'email') return 'ایمیل';
  if (value === 'in_app' || value === 'push') return 'اعلان';
  return 'پیام';
}

function getChannelIcon(channel?: string | null) {
  const value = (channel || '').toLowerCase();
  return value === 'email' ? <Mail className="h-5 w-5" /> : <Bell className="h-5 w-5" />;
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
  const body = getFriendlyNotificationBody(item);

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
        <div className="flex min-w-0 items-start gap-4 text-right">
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

          <div className="min-w-0">
            <div className="flex flex-wrap items-center justify-start gap-2 sm:justify-end">
              <h3 className="text-lg font-extrabold text-text">
                {getFriendlyNotificationTitle(item)}
              </h3>

              <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-bold text-slate-600 dark:bg-white/5 dark:text-slate-300">
                {getChannelLabel(item.channel)}
              </span>

              <span
                className={[
                  'inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-bold',
                  read
                    ? 'bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-300'
                    : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
                ].join(' ')}
              >
                {read ? <CheckCheck className="h-3.5 w-3.5" /> : <Bell className="h-3.5 w-3.5" />}
                {read ? 'خوانده‌شده' : 'جدید'}
              </span>
            </div>

            <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-8 text-slate-600 dark:text-slate-300">
              {body}
            </p>

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

            <div className="mt-4 text-xs font-medium text-slate-500 dark:text-slate-400">
              {formatDate(item.sent_at || item.last_attempt_at || item.created_at)}
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2 self-end lg:self-start">
          {!read ? (
            <button
              type="button"
              onClick={() => onMarkAsRead(item)}
              disabled={marking}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-emerald-600 px-4 text-sm font-bold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Check className="h-4 w-4" />
              {marking ? 'در حال ثبت...' : 'خواندم'}
            </button>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function EmptyState({ filter }: { filter: ViewFilter }) {
  return (
    <div className="rounded-[28px] border border-dashed border-emerald-200 bg-emerald-50/40 p-10 text-center shadow-soft dark:border-emerald-500/20 dark:bg-emerald-500/10">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-white text-emerald-600 shadow-sm dark:bg-white/[0.06] dark:text-emerald-300">
        <Bell className="h-7 w-7" />
      </div>
      <h2 className="text-xl font-extrabold text-text">
        {filter === 'read' ? 'پیام خوانده‌شده‌ای پیدا نشد' : 'پیامی برای نمایش نیست'}
      </h2>
      <p className="mt-2 text-sm leading-7 text-muted">
        {filter === 'read'
          ? 'هر پیامی را که بخوانی، اینجا نگه می‌داریم تا بعداً دوباره به آن سر بزنی.'
          : 'کدهای تایید، یادآوری پرداخت، دریافتی‌ها و پیام‌های مرتبط با هزینه‌ها اینجا نمایش داده می‌شوند.'}
      </p>
    </div>
  );
}

export function NotificationsPage({ onUnreadCountChange }: NotificationsPageProps) {
  const { notify } = useFeedback();

  const [messages, setMessages] = useState<BackendNotificationMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewFilter, setViewFilter] = useState<ViewFilter>('all');
  const [search, setSearch] = useState('');
  const [markingIds, setMarkingIds] = useState<string[]>([]);
  const [localReadIds, setLocalReadIds] = useState<Set<string>>(() => loadPersistedReadIds());

  const allCount = messages.length;
  const readCount = useMemo(
    () => messages.filter((item) => isMessageRead(item, localReadIds)).length,
    [localReadIds, messages],
  );
  const unreadCount = useMemo(
    () => getUnreadCount(messages, localReadIds),
    [localReadIds, messages],
  );

  const filteredMessages = useMemo(() => {
    const query = search.trim().toLowerCase();

    return messages.filter((item) => {
      const read = isMessageRead(item, localReadIds);

      if (viewFilter === 'read' && !read) {
        return false;
      }

      if (!query) return true;

      const haystack = [
        item.title,
        getFriendlyNotificationTitle(item),
        getFriendlyNotificationBody(item),
        getFriendlyNotificationCode(item),
        item.message,
        item.body,
        item.text,
        item.content,
        item.rendered_message,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return haystack.includes(query);
    });
  }, [localReadIds, messages, search, viewFilter]);

  useEffect(() => {
    persistReadIds(localReadIds);
    onUnreadCountChange?.(unreadCount);
  }, [localReadIds, onUnreadCountChange, unreadCount]);

  async function loadMessages() {
    try {
      setLoading(true);
      setError(null);

      const data = await getNotificationMessages();
      setMessages(
        data.map((item) =>
          localReadIds.has(item.id)
            ? {
                ...item,
                is_read: true,
                read_at: item.read_at || new Date().toISOString(),
              }
            : item,
        ),
      );
    } catch (err) {
      console.error(err);
      setError('فعلاً پیام‌ها در دسترس نیستند. کمی بعد دوباره تلاش کن.');
      setMessages([]);
      onUnreadCountChange?.(0);

      notify({
        type: 'error',
        title: 'پیام‌ها بارگذاری نشدند',
        description: 'لطفاً چند لحظه بعد دوباره تلاش کن.',
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleMarkAsRead(item: BackendNotificationMessage) {
    if (isMessageRead(item, localReadIds)) {
      return;
    }

    setMarkingIds((current) => [...current, item.id]);

    setLocalReadIds((current) => {
      const next = new Set(current);
      next.add(item.id);
      return next;
    });

    setMessages((current) =>
      current.map((entry) =>
        entry.id === item.id
          ? {
              ...entry,
              is_read: true,
              read_at: entry.read_at || new Date().toISOString(),
            }
          : entry,
      ),
    );

    try {
      await markNotificationMessageAsRead(item.id);
    } catch (error) {
      console.warn('Could not persist notification read state. Keeping local read state.', error);
    } finally {
      setMarkingIds((current) => current.filter((id) => id !== item.id));
    }
  }

  useEffect(() => {
    loadMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="px-4 py-6 sm:px-6 xl:px-8">
      <div className="mx-auto max-w-[1180px] space-y-6">
        <section className="overflow-hidden rounded-[32px] border border-border bg-[linear-gradient(135deg,rgba(15,23,42,0.02),rgba(16,185,129,0.08))] p-6 shadow-soft dark:bg-[linear-gradient(135deg,rgba(255,255,255,0.03),rgba(16,185,129,0.08))]">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="text-right">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-300">
                <Bell className="h-6 w-6" />
              </div>

              <h1 className="mt-4 text-[32px] font-extrabold tracking-[-0.03em] text-text">
                پیام‌ها و اعلان‌ها
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-muted">
                کدهای تایید، یادآوری پرداخت، دریافتی‌ها و پیام‌های مرتبط با هزینه‌ها را اینجا ببین و بعد از بررسی، آن‌ها را به‌عنوان خوانده‌شده علامت بزن.
              </p>
            </div>

            <button
              type="button"
              onClick={loadMessages}
              disabled={loading}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border bg-white px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white/[0.03] dark:text-slate-200 dark:hover:bg-white/[0.05]"
            >
              <RefreshCw className="h-4 w-4" />
              {loading ? 'در حال بروزرسانی...' : 'بروزرسانی'}
            </button>
          </div>
        </section>

        <section className="space-y-5">
          <div className="rounded-[28px] border border-border bg-white p-5 shadow-soft dark:bg-white/[0.03]">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,220px)_1fr] lg:items-center">
              <div className="rounded-3xl border border-emerald-500/15 bg-emerald-500/5 px-5 py-4 text-right dark:bg-emerald-500/10">
                <div className="text-xs font-semibold text-muted">همه پیام‌ها</div>
                <div className="mt-2 text-3xl font-extrabold text-text">
                  {allCount.toLocaleString('fa-IR')}
                </div>
                <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  {unreadCount.toLocaleString('fa-IR')} پیام جدید
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  {viewTabs.map((tab) => {
                    const count = tab.value === 'all' ? allCount : readCount;

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
                              ? 'bg-white/15 text-white'
                              : 'bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-300',
                          ].join(' ')}
                        >
                          {count.toLocaleString('fa-IR')}
                        </span>
                      </button>
                    );
                  })}
                </div>

                <div className="relative min-w-0">
                  <Search className="pointer-events-none absolute right-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" />
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="جستجو در عنوان یا متن پیام..."
                    className="h-12 w-full rounded-2xl border border-border bg-white pr-11 pl-4 text-right text-sm outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 dark:bg-white/[0.03]"
                  />
                </div>
              </div>
            </div>
          </div>

          {error ? (
            <div className="rounded-[28px] border border-rose-100 bg-rose-50 p-5 text-center text-sm font-bold text-rose-600 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300">
              {error}
            </div>
          ) : null}

          {loading ? (
            <div className="rounded-[28px] border border-border bg-white p-8 text-center text-sm text-muted shadow-soft dark:bg-white/[0.03]">
              در حال دریافت پیام‌ها...
            </div>
          ) : null}

          {!loading && filteredMessages.length === 0 ? <EmptyState filter={viewFilter} /> : null}

          <div className="space-y-4">
            {filteredMessages.map((item) => (
              <NotificationItem
                key={item.id}
                item={item}
                read={isMessageRead(item, localReadIds)}
                marking={markingIds.includes(item.id)}
                onMarkAsRead={handleMarkAsRead}
              />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
