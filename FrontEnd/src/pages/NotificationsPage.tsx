import { type ReactNode, useEffect, useMemo, useState } from 'react';
import {
  Bell,
  Check,
  CheckCheck,
  Mail,
  RefreshCw,
  Search,
  Send,
  Users,
  X,
} from 'lucide-react';
import {
  getNotificationMessages,
  getNotifications,
  markAllNotificationsAsRead,
  markNotificationMessageAsRead,
  sendNotificationEmailTest,
  type BackendNotificationMessage,
} from '../lib/notificationApi';
import {
  acceptDirectGroupInvitation,
  getMyGroups,
  listMyDirectGroupInvitations,
  rejectDirectGroupInvitation,
  type BackendGroup,
  type DirectGroupInvitation,
} from '../lib/groupApi';
import {
  getDashboardActionItems,
  type DashboardActionItem,
} from '../lib/dashboardApi';
import {
  confirmPlanItem,
  confirmSettlement,
  getSettlementPlan,
  rejectPlanItem,
  rejectSettlement,
  type SettlementPlanItem,
} from '../lib/settlementApi';
import { useFeedback } from '../components/feedback/FeedbackProvider';
import { getCurrentUser } from '../lib/userApi';
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

function formatMoneyMinor(amount?: number | null) {
  const value = Math.abs(Number(amount || 0));
  return `تومان ⁦${value.toLocaleString('fa-IR')}⁩`;
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

  const sign = amount < 0 ? '-' : '';
  return `تومان \u2066${sign}${Math.abs(amount).toLocaleString('fa-IR')}\u2069`;
}

function getInvitationSearchText(invitation: DirectGroupInvitation) {
  return [
    invitation.group?.title,
    invitation.invited_by?.art_name,
    invitation.status,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
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
    unavailableMessage: 'فعلاً نمی‌توانیم اعلان‌هایت را نشان بدهیم. چند لحظه بعد دوباره امتحان کن.',
    notFoundMessage: 'اطلاعات اعلان پیدا نشد.',
    codeMap: {
      NOTIFICATION_NOT_FOUND: 'این اعلان پیدا نشد.',
      ALREADY_READ: 'این اعلان قبلاً خوانده شده است.',
      EMAIL_SEND_FAILED: 'پیام تستی ارسال نشد. آدرس ایمیل را بررسی کن و دوباره امتحان کن.',
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

function isSettlementConfirmationAction(item: DashboardActionItem) {
  return item.type === 'CONFIRM_RECEIVED_PAYMENT';
}

function getActionGroupName(item: DashboardActionItem) {
  return item.group?.title || 'گروه';
}

function getActionSourceKind(item: DashboardActionItem) {
  return String(item.source?.type || '').toUpperCase();
}

function isPlanItemAwaitingReceiverReview(item: SettlementPlanItem) {
  return String(item.status || '').toUpperCase() === 'REPORTED';
}

function planItemToSettlementConfirmationAction(
  item: SettlementPlanItem,
  group: BackendGroup,
  referenceDate?: string | null,
): DashboardActionItem {
  const payerName = item.payer_display_name || item.payer_art_name || 'یکی از اعضا';

  return {
    id: `plan-confirmation-${item.id}`,
    type: 'CONFIRM_RECEIVED_PAYMENT',
    priority: 'HIGH',
    title: 'تأیید دریافت پول',
    description: `${payerName} برای گروه «${group.title || 'گروه'}» پرداخت ثبت کرده است.`,
    group: {
      id: group.id,
      title: group.title || 'گروه',
    },
    source: {
      service: 'settlement',
      type: 'SETTLEMENT_PLAN_ITEM',
      id: item.id,
    },
    amount_minor: item.amount_minor,
    currency: 'IRR',
    created_at: referenceDate || null,
    due_at: null,
    allowed_actions: [
      { key: 'confirm', method: 'POST', path: `/settlement-plan-items/${item.id}/confirm/` },
      { key: 'reject', method: 'POST', path: `/settlement-plan-items/${item.id}/reject/` },
    ],
  };
}

async function loadSettlementPlanConfirmationActions() {
  const [currentUser, groups] = await Promise.all([getCurrentUser(), getMyGroups()]);
  const currentUserId = currentUser?.id ? String(currentUser.id) : '';

  if (!currentUserId || groups.length === 0) {
    return [] as DashboardActionItem[];
  }

  const results = await Promise.allSettled(
    groups.map(async (group) => {
      const plan = await getSettlementPlan(group.id);

      return (plan.items || [])
        .filter((item) => item.receiver_user_id === currentUserId && isPlanItemAwaitingReceiverReview(item))
        .map((item) =>
          planItemToSettlementConfirmationAction(
            item,
            group,
            plan.updated_at || plan.created_at || null,
          ),
        );
    }),
  );

  return results.flatMap((result) => (result.status === 'fulfilled' ? result.value : []));
}

function getSettlementActionDedupKey(item: DashboardActionItem) {
  const sourceKind = getActionSourceKind(item);
  const sourceId = item.source?.id || item.id;
  return `${sourceKind}:${sourceId}`;
}

function getActionSearchText(item: DashboardActionItem) {
  return [
    item.title,
    item.description,
    item.group?.title,
    item.amount_minor ? formatMoneyMinor(item.amount_minor) : '',
    formatDate(item.created_at),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

interface SettlementConfirmationActionCardProps {
  item: DashboardActionItem;
  loading: boolean;
  onConfirm: (item: DashboardActionItem) => void;
  onReject: (item: DashboardActionItem) => void;
}

function SettlementConfirmationActionCard({
  item,
  loading,
  onConfirm,
  onReject,
}: SettlementConfirmationActionCardProps) {
  return (
    <article className="overflow-hidden rounded-[28px] border border-amber-500/25 bg-[linear-gradient(180deg,rgba(245,158,11,0.12),rgba(255,255,255,0.96))] p-5 shadow-soft transition sm:p-6 dark:bg-[linear-gradient(180deg,rgba(245,158,11,0.12),rgba(15,23,42,0.96))]">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 flex-1 items-start gap-4 text-right">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-700 dark:text-amber-300">
            <CheckCheck className="h-6 w-6" />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center justify-start gap-2 sm:justify-end">
              <h3 className="text-lg font-extrabold text-text">تأیید دریافت پول</h3>
              <span className="rounded-full bg-amber-500/10 px-3 py-1 text-[11px] font-bold text-amber-700 dark:text-amber-300">
                نیاز به پاسخ
              </span>
            </div>

            <p className="mt-3 text-sm leading-8 text-slate-600 dark:text-slate-300">
              یک پرداخت برای گروه «{getActionGroupName(item)}» ثبت شده است. اگر پول را دریافت کرده‌اید تأیید کنید؛ اگر دریافت نکرده‌اید رد کنید تا برای پرداخت‌کننده تسویه ثبت نشود.
            </p>

            <div className="mt-4 flex flex-wrap items-center justify-start gap-2 sm:justify-end">
              <span className="rounded-full bg-sky-500/10 px-3 py-1 text-xs font-bold text-sky-700 dark:text-sky-300">
                گروه: {getActionGroupName(item)}
              </span>
              <span className="rounded-full bg-amber-500/10 px-3 py-1 text-xs font-bold text-amber-700 dark:text-amber-300">
                مبلغ: {formatMoneyMinor(item.amount_minor)}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600 dark:bg-white/5 dark:text-slate-300">
                {formatDate(item.created_at)}
              </span>
            </div>
          </div>
        </div>

        <div className="grid shrink-0 grid-cols-2 gap-2 lg:min-w-[240px]">
          <button
            type="button"
            onClick={() => onConfirm(item)}
            disabled={loading}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-emerald-600 px-4 text-sm font-bold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            پول را گرفتم
          </button>

          <button
            type="button"
            onClick={() => onReject(item)}
            disabled={loading}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 text-sm font-bold text-rose-700 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-rose-500/25 dark:bg-rose-500/10 dark:text-rose-200 dark:hover:bg-rose-500/15"
          >
            <X className="h-4 w-4" />
            دریافت نکردم
          </button>
        </div>
      </div>
    </article>
  );
}

interface NotificationItemProps {
  item: BackendNotificationMessage;
  read: boolean;
  marking: boolean;
  onMarkAsRead: (item: BackendNotificationMessage) => void;
}

interface DirectInvitationCardProps {
  invitation: DirectGroupInvitation;
  loading: boolean;
  onAccept: (invitation: DirectGroupInvitation) => void;
  onReject: (invitation: DirectGroupInvitation) => void;
}

function DirectInvitationCard({
  invitation,
  loading,
  onAccept,
  onReject,
}: DirectInvitationCardProps) {
  const inviterName = invitation.invited_by?.art_name || 'مدیر گروه';

  return (
    <article className="overflow-hidden rounded-[28px] border border-emerald-500/25 bg-[linear-gradient(180deg,rgba(16,185,129,0.10),rgba(255,255,255,0.96))] p-5 shadow-soft transition sm:p-6 dark:bg-[linear-gradient(180deg,rgba(16,185,129,0.12),rgba(15,23,42,0.96))]">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 flex-1 items-start gap-4 text-right">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
            <Users className="h-6 w-6" />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center justify-start gap-2 sm:justify-end">
              <h3 className="text-lg font-extrabold text-text">دعوت عضویت در گروه</h3>
              <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-[11px] font-bold text-emerald-700 dark:text-emerald-300">
                نیاز به پاسخ
              </span>
            </div>

            <p className="mt-3 text-sm leading-8 text-slate-600 dark:text-slate-300">
              {inviterName} شما را به گروه «{invitation.group?.title || 'بدون نام'}» دعوت کرده است.
            </p>

            <div className="mt-4 flex flex-wrap items-center justify-start gap-2 sm:justify-end">
              <span className="rounded-full bg-sky-500/10 px-3 py-1 text-xs font-bold text-sky-700 dark:text-sky-300">
                گروه: {invitation.group?.title || 'نامشخص'}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600 dark:bg-white/5 dark:text-slate-300">
                {formatDate(invitation.created_at)}
              </span>
            </div>
          </div>
        </div>

        <div className="grid shrink-0 grid-cols-2 gap-2 lg:min-w-[220px]">
          <button
            type="button"
            onClick={() => onAccept(invitation)}
            disabled={loading}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-emerald-600 px-4 text-sm font-bold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            قبول
          </button>

          <button
            type="button"
            onClick={() => onReject(invitation)}
            disabled={loading}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 text-sm font-bold text-rose-700 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-rose-500/25 dark:bg-rose-500/10 dark:text-rose-200 dark:hover:bg-rose-500/15"
          >
            <X className="h-4 w-4" />
            رد
          </button>
        </div>
      </div>
    </article>
  );
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
  const [groupInvitations, setGroupInvitations] = useState<DirectGroupInvitation[]>([]);
  const [dashboardActionItems, setDashboardActionItems] = useState<DashboardActionItem[]>([]);
  const [settlementPlanActionItems, setSettlementPlanActionItems] = useState<DashboardActionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [invitationActionId, setInvitationActionId] = useState<string | null>(null);
  const [settlementActionId, setSettlementActionId] = useState<string | null>(null);
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

  const settlementConfirmationActions = useMemo(() => {
    const actionsBySource = new Map<string, DashboardActionItem>();

    for (const item of dashboardActionItems.filter(isSettlementConfirmationAction)) {
      actionsBySource.set(getSettlementActionDedupKey(item), item);
    }

    for (const item of settlementPlanActionItems) {
      const key = getSettlementActionDedupKey(item);
      if (!actionsBySource.has(key)) {
        actionsBySource.set(key, item);
      }
    }

    return Array.from(actionsBySource.values());
  }, [dashboardActionItems, settlementPlanActionItems]);

  const totalNotificationsCount = notifications.length + groupInvitations.length + settlementConfirmationActions.length;
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

  const visibleSettlementConfirmationActions = useMemo(() => {
    if (dataSource !== 'notifications' || viewFilter === 'read') return [];
    if (channelFilter && !['in_app', 'push'].includes(channelFilter.toLowerCase())) return [];

    const query = search.trim().toLowerCase();
    if (!query) return settlementConfirmationActions;

    return settlementConfirmationActions.filter((item) => getActionSearchText(item).includes(query));
  }, [channelFilter, dataSource, search, settlementConfirmationActions, viewFilter]);

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

  const visibleGroupInvitations = useMemo(() => {
    if (dataSource !== 'notifications' || viewFilter === 'read') return [];
    if (channelFilter && !['in_app', 'push'].includes(channelFilter.toLowerCase())) return [];

    const query = search.trim().toLowerCase();

    return groupInvitations.filter((invitation) => {
      if (String(invitation.status || '').toUpperCase() !== 'PENDING') return false;
      if (!query) return true;
      return getInvitationSearchText(invitation).includes(query);
    });
  }, [channelFilter, dataSource, groupInvitations, search, viewFilter]);

  useEffect(() => {
    persistReadIds(localReadIds);
    onUnreadCountChange?.(
      getUnreadCount(notifications, localReadIds) + groupInvitations.length + settlementConfirmationActions.length,
    );
  }, [groupInvitations.length, localReadIds, notifications, onUnreadCountChange, settlementConfirmationActions.length]);

  async function loadNotificationsPage() {
    try {
      setLoading(true);
      setError(null);

      const [
        notificationResult,
        messagesResult,
        invitationsResult,
        actionItemsResult,
        settlementPlanActionsResult,
      ] = await Promise.allSettled([
        getNotifications({ limit: 100 }),
        getNotificationMessages({ limit: 100 }),
        listMyDirectGroupInvitations({ status: 'PENDING', page_size: 100 }),
        getDashboardActionItems({ pageSize: 100 }),
        loadSettlementPlanConfirmationActions(),
      ]);

      if (
        notificationResult.status === 'rejected' &&
        messagesResult.status === 'rejected' &&
        invitationsResult.status === 'rejected' &&
        actionItemsResult.status === 'rejected' &&
        settlementPlanActionsResult.status === 'rejected'
      ) {
        throw notificationResult.reason || messagesResult.reason || settlementPlanActionsResult.reason;
      }

      const notificationList = notificationResult.status === 'fulfilled' ? notificationResult.value : [];
      const recentMessages = messagesResult.status === 'fulfilled' ? messagesResult.value : [];
      const directInvitationList = invitationsResult.status === 'fulfilled' ? invitationsResult.value : [];
      const dashboardActions = actionItemsResult.status === 'fulfilled' ? actionItemsResult.value : [];
      const settlementPlanActions = settlementPlanActionsResult.status === 'fulfilled' ? settlementPlanActionsResult.value : [];

      if (
        notificationResult.status === 'rejected' ||
        messagesResult.status === 'rejected' ||
        invitationsResult.status === 'rejected' ||
        actionItemsResult.status === 'rejected' ||
        settlementPlanActionsResult.status === 'rejected'
      ) {
        console.warn('One notification source failed, rendering the available source.', {
          notificationError: notificationResult.status === 'rejected' ? notificationResult.reason : undefined,
          messagesError: messagesResult.status === 'rejected' ? messagesResult.reason : undefined,
          invitationsError: invitationsResult.status === 'rejected' ? invitationsResult.reason : undefined,
          actionItemsError: actionItemsResult.status === 'rejected' ? actionItemsResult.reason : undefined,
          settlementPlanActionsError: settlementPlanActionsResult.status === 'rejected' ? settlementPlanActionsResult.reason : undefined,
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

      setGroupInvitations(directInvitationList);
      setDashboardActionItems(dashboardActions);
      setSettlementPlanActionItems(settlementPlanActions);
    } catch (loadError) {
      const message = getActionErrorMessage(
        loadError,
        'فعلاً اعلان‌هایت در دسترس نیستند. چند لحظه بعد دوباره امتحان کن.',
      );
      setError(message);
      setNotifications([]);
      setMessages([]);
      setGroupInvitations([]);
      setDashboardActionItems([]);
      setSettlementPlanActionItems([]);
      onUnreadCountChange?.(0);

      notify({
        type: 'error',
        title: 'اعلان‌ها نمایش داده نشدند',
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
        title: 'این اعلان خوانده شد',
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
        description: 'در این صفحه اعلان خوانده‌نشده‌ای باقی نمانده است.',
      });
    } catch (markAllError) {
      notify({
        type: 'error',
        title: 'وضعیت اعلان‌ها ذخیره نشد',
        description: getActionErrorMessage(
          markAllError,
          'فعلاً امکان ثبت خوانده شدن همه اعلان‌ها وجود ندارد.',
        ),
      });
    } finally {
      setActionLoading(null);
    }
  }

  async function handleAcceptGroupInvitation(invitation: DirectGroupInvitation) {
    try {
      setInvitationActionId(invitation.id);
      await acceptDirectGroupInvitation(invitation.id);
      setGroupInvitations((current) => current.filter((item) => item.id !== invitation.id));

      notify({
        type: 'success',
        title: 'دعوت را قبول کردی',
        description: `شما به گروه «${invitation.group?.title || 'گروه'}» اضافه شدید.`,
      });
    } catch (acceptError) {
      notify({
        type: 'error',
        title: 'دعوت قبول نشد',
        description: getActionErrorMessage(
          acceptError,
          'فعلاً نمی‌توانیم این دعوت را قبول کنیم. صفحه را تازه کن و دوباره امتحان کن.',
        ),
      });
    } finally {
      setInvitationActionId(null);
    }
  }

  async function handleRejectGroupInvitation(invitation: DirectGroupInvitation) {
    try {
      setInvitationActionId(invitation.id);
      await rejectDirectGroupInvitation(invitation.id);
      setGroupInvitations((current) => current.filter((item) => item.id !== invitation.id));

      notify({
        type: 'success',
        title: 'دعوت را رد کردی',
        description: `دعوت گروه «${invitation.group?.title || 'گروه'}» از لیست شما حذف شد.`,
      });
    } catch (rejectError) {
      notify({
        type: 'error',
        title: 'دعوت رد نشد',
        description: getActionErrorMessage(
          rejectError,
          'فعلاً نمی‌توانیم این دعوت را رد کنیم. صفحه را تازه کن و دوباره امتحان کن.',
        ),
      });
    } finally {
      setInvitationActionId(null);
    }
  }

  async function handleSettlementConfirmationAction(
    item: DashboardActionItem,
    action: 'confirm' | 'reject',
  ) {
    const sourceKind = getActionSourceKind(item);

    try {
      setSettlementActionId(`${item.id}-${action}`);

      if (sourceKind === 'SETTLEMENT_PLAN_ITEM') {
        if (action === 'confirm') {
          await confirmPlanItem(item.source.id);
        } else {
          await rejectPlanItem(item.source.id);
        }
      } else if (sourceKind === 'MANUAL_SETTLEMENT') {
        if (action === 'confirm') {
          await confirmSettlement(item.source.id);
        } else {
          await rejectSettlement(item.source.id);
        }
      } else {
        throw new Error('Unsupported settlement action source');
      }

      const actedSourceKey = getSettlementActionDedupKey(item);
      setDashboardActionItems((current) =>
        current.filter((actionItem) => getSettlementActionDedupKey(actionItem) !== actedSourceKey),
      );
      setSettlementPlanActionItems((current) =>
        current.filter((actionItem) => getSettlementActionDedupKey(actionItem) !== actedSourceKey),
      );
      notify({
        type: 'success',
        title: action === 'confirm' ? 'دریافت پول تأیید شد' : 'پرداخت رد شد',
        description:
          action === 'confirm'
            ? 'پرداخت برای طرف مقابل ثبت شد و این مورد از لیست کارهایت برداشته شد.'
            : 'این مورد از لیست کارهایت برداشته شد و بدهی طرف مقابل تسویه نشد.',
      });
    } catch (settlementActionError) {
      notify({
        type: 'error',
        title: action === 'confirm' ? 'دریافت پول تأیید نشد' : 'پرداخت رد نشد',
        description: getActionErrorMessage(
          settlementActionError,
          'فعلاً نمی‌توانیم وضعیت این پرداخت را ثبت کنیم. صفحه را تازه کن و دوباره امتحان کن.',
        ),
      });
    } finally {
      setSettlementActionId(null);
    }
  }

  async function handleSendEmailTest() {
    if (!emailTestForm.email.trim()) {
      notify({
        type: 'error',
        title: 'ایمیل گیرنده را وارد کن',
        description: 'برای ارسال پیام تستی، ایمیل گیرنده را وارد کن.',
      });
      return;
    }

    if (!emailTestForm.message.trim()) {
      notify({
        type: 'error',
        title: 'متن پیام را بنویس',
        description: 'یک متن کوتاه برای پیام تستی بنویس.',
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
        title: 'پیام تستی ارسال شد',
        description: 'اگر سرویس ایمیل فعال باشد، پیام تست به این آدرس می‌رسد.',
      });
    } catch (emailError) {
      notify({
        type: 'error',
        title: 'پیام تستی ارسال نشد',
        description: getActionErrorMessage(
          emailError,
          'پیام تستی ارسال نشد. ایمیل را بررسی کن و دوباره امتحان کن.',
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
    <main className="app-page">
      <div className="app-container app-container-wide space-y-6">
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

            <div className="app-stat-grid">
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

        <section className="app-grid app-notifications-grid">
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
                      const actionableCount =
                        dataSource === 'notifications' ? groupInvitations.length + settlementConfirmationActions.length : 0;
                      const count =
                        tab.value === 'all'
                          ? activeItems.length + actionableCount
                          : tab.value === 'read'
                            ? readCount
                            : unreadCount + actionableCount;

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
                    disabled={actionLoading === 'read-all' || (activeItems.length === 0 && visibleSettlementConfirmationActions.length === 0 && visibleGroupInvitations.length === 0)}
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

            {!loading && filteredItems.length === 0 && visibleGroupInvitations.length === 0 && visibleSettlementConfirmationActions.length === 0 ? (
              <EmptyState source={dataSource} filter={viewFilter} />
            ) : null}

            <div className="space-y-4">
              {visibleSettlementConfirmationActions.map((item) => (
                <SettlementConfirmationActionCard
                  key={`settlement-confirmation-${item.id}`}
                  item={item}
                  loading={settlementActionId?.startsWith(item.id) || false}
                  onConfirm={(actionItem) => void handleSettlementConfirmationAction(actionItem, 'confirm')}
                  onReject={(actionItem) => void handleSettlementConfirmationAction(actionItem, 'reject')}
                />
              ))}

              {visibleGroupInvitations.map((invitation) => (
                <DirectInvitationCard
                  key={`group-invitation-${invitation.id}`}
                  invitation={invitation}
                  loading={invitationActionId === invitation.id}
                  onAccept={handleAcceptGroupInvitation}
                  onReject={handleRejectGroupInvitation}
                />
              ))}

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
