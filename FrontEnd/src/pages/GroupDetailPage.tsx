import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  Archive,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Banknote,
  Bell,
  CalendarDays,
  Check,
  Copy,
  Download,
  Eye,
  HandCoins,
  History,
  Link2,
  Loader2,
  LogOut,
  Plus,
  ReceiptText,
  RefreshCw,
  RotateCcw,
  Save,
  Scale,
  Search,
  Settings,
  Sparkles,
  Trash2,
  Upload,
  UserMinus,
  UserPlus,
  UserRound,
  Users,
  WalletCards,
  X,
} from 'lucide-react';
import { InlineLoader, useFeedback } from '../components/feedback/FeedbackProvider';
import { isApiError } from '../lib/api';
import {
  createIdempotencyKey,
  createPaymentIntent,
  getMyWallet,
  paySettlementItemWithWallet,
  savePendingWalletPayment,
  verifyPaymentIntent,
  type PaymentProvider,
} from '../lib/walletApi';
import type { DashboardActivityItem } from '../lib/dashboardApi';
import { downloadMediaFile, listMyVisibleReceipts, uploadReceipt, type ReceiptListItem } from '../lib/mediaApi';
import { getFriendlyApiErrorMessage, humanizeMachineLabel } from '../lib/userMessages';
import {
  createGroupExpense,
  deleteExpense,
  listGroupExpenses,
  type BackendExpense,
  type ExpenseParticipant,
  type ExpenseSplitMethod,
} from '../lib/expenseApi';
import {
  activateSettlementPlan,
  cancelSettlementPlan,
  cancelSettlement,
  confirmPlanItem,
  confirmSettlement,
  createGroupSettlement,
  generateSettlementPlan,
  getGroupBalances,
  getGroupDebts,
  getGroupReminderSettings,
  getMyGroupBalance,
  getSettlementPlan,
  listGroupSettlements,
  rejectPlanItem,
  rejectSettlement,
  reportPlanItemPaid,
  runGroupReminders,
  sendPlanItemReminder,
  updateGroupReminderSettings,
  type BalanceItem,
  type DebtItem,
  type GroupReminderSettings,
  type MyBalanceResponse,
  type SettlementItem,
  type SettlementPlan,
  type SettlementPlanItem,
} from '../lib/settlementApi';
import {
  archiveGroup,
  createDirectGroupInvite,
  createGroupInvite,
  getBackendGroupMemberId,
  getBackendGroupMemberName,
  getBackendGroupMemberPhone,
  getBackendGroupMemberUserId,
  getGroupDetail,
  getGroupMembers,
  getInviteId,
  getInviteUrl,
  leaveGroup,
  removeGroupMember,
  restoreGroup,
  revokeGroupInvite,
  updateGroup,
  type BackendGroup,
  type BackendGroupMember,
  type BackendGroupType,
  type CreatedInvite,
} from '../lib/groupApi';
import { MoneyWithWords } from '../lib/money';
import { getCurrentUser, searchUsersByArtName, type CurrentUser, type UserSearchResult } from '../lib/userApi';

interface GroupDetailPageProps {
  groupId: string;
  onBack: () => void;
  onGroupUpdated: (group: BackendGroup) => void;
  onGroupRemoved: (groupId: string) => void;
}

type ModalName = 'expense' | 'settlement' | 'settings' | null;
type ManualPaymentMode = 'FULL' | 'PARTIAL';
type SettlementModalTab = 'suggestion' | 'debts' | 'history';
type GroupDetailView = 'expenses' | 'activities' | 'settlement' | 'members';

const reminderIntervalOptions = [
  { value: 24, label: 'هر روز' },
  { value: 48, label: 'هر ۲ روز' },
  { value: 72, label: 'هر ۳ روز' },
  { value: 168, label: 'هر هفته' },
  { value: 336, label: 'هر ۲ هفته' },
];

const reminderFirstDelayOptions = [
  { value: 0, label: 'همین الان' },
  { value: 24, label: 'یک روز بعد' },
  { value: 48, label: 'دو روز بعد' },
  { value: 72, label: 'سه روز بعد' },
  { value: 168, label: 'یک هفته بعد' },
];

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function toPersianNumber(value: string | number) {
  return String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);
}

function normalizeDigits(value: string) {
  const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
  const arabicDigits = '٠١٢٣٤٥٦٧٨٩';

  return value
    .replace(/[۰-۹]/g, (digit) => String(persianDigits.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String(arabicDigits.indexOf(digit)));
}

function parseAmountToMinor(value: string) {
  const digits = normalizeDigits(value).replace(/[^0-9]/g, '');
  return Number(digits || 0);
}

function formatMoney(minor = 0) {
  const absValue = Math.abs(Math.round(minor));
  return `تومان \u2066${toPersianNumber(absValue.toLocaleString('en-US'))}\u2069`;
}

function formatSignedMoney(minor = 0) {
  return formatMoney(minor);
}

function toPersianDate(value?: string) {
  if (!value) return 'بدون تاریخ';

  try {
    return new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function getBackendMessage(error: unknown) {
  return getFriendlyApiErrorMessage(error, {
    defaultMessage: 'فعلاً این کار انجام نشد. چند لحظه بعد دوباره امتحان کن.',
    invalidMessage: 'اطلاعات واردشده کامل یا درست نیست.',
  });
}

function getMemberId(member: BackendGroupMember) {
  return getBackendGroupMemberId(member);
}

function getMemberUserId(member: BackendGroupMember) {
  return getBackendGroupMemberUserId(member);
}

function getMemberName(member: BackendGroupMember) {
  return getBackendGroupMemberName(member);
}

function getMemberPhone(member: BackendGroupMember) {
  return getBackendGroupMemberPhone(member);
}

function getRoleLabel(role?: string) {
  if (role === 'OWNER') return 'مالک';
  if (role === 'ADMIN') return 'مدیر';
  if (role === 'MEMBER') return 'عضو';
  return role || 'عضو';
}

function getCurrentUserId(user: CurrentUser | null) {
  return user?.id ? String(user.id) : '';
}

function getExpenseTotal(expense: BackendExpense) {
  return (
    expense.total_amount_minor ??
    (expense.base_amount_minor || 0) +
      (expense.tax_amount_minor || 0) +
      (expense.service_fee_amount_minor || 0)
  );
}


function getExpenseParticipantShareMinor(participant?: ExpenseParticipant) {
  if (!participant) return 0;

  if (typeof participant.total_share_minor === 'number' && Number.isFinite(participant.total_share_minor)) {
    return Math.max(0, Math.round(participant.total_share_minor));
  }

  return Math.max(0, Math.round(
    (participant.base_share_minor || 0) +
    (participant.tax_share_minor || 0) +
    (participant.service_fee_share_minor || 0),
  ));
}

function getIncludedExpenseParticipants(expense: BackendExpense) {
  return (expense.participants || []).filter((participant) => participant.is_included !== false);
}

function getExpenseUserImpact(expense: BackendExpense, currentUserId?: string | null, memberCount = 1) {
  const totalMinor = getExpenseTotal(expense);
  const fallbackMemberCount = Math.max(1, Number(memberCount) || 1);
  const fallbackUserShareMinor = Math.round(totalMinor / fallbackMemberCount);

  if (!currentUserId) {
    return { type: 'neutral' as const, amountMinor: totalMinor, signedAmountMinor: 0, label: 'اثر نامشخص' };
  }

  const normalizedCurrentUserId = String(currentUserId);
  const payerUserId = String(expense.payer_user_id || '');
  const includedParticipants = getIncludedExpenseParticipants(expense);
  const currentParticipant = includedParticipants.find(
    (participant) => String(participant.user_id || '') === normalizedCurrentUserId,
  );
  const currentShareMinor = getExpenseParticipantShareMinor(currentParticipant);
  const participantTotalMinor = includedParticipants.reduce(
    (sum, participant) => sum + getExpenseParticipantShareMinor(participant),
    0,
  );

  if (payerUserId === normalizedCurrentUserId) {
    const receivableMinor = includedParticipants.length > 0
      ? Math.max(0, participantTotalMinor - currentShareMinor)
      : Math.max(0, totalMinor - fallbackUserShareMinor);

    return {
      type: 'credit' as const,
      amountMinor: receivableMinor,
      signedAmountMinor: receivableMinor,
      label: 'طلب شما از بقیه',
    };
  }

  if (currentParticipant || includedParticipants.length === 0) {
    const payableMinor = currentParticipant ? currentShareMinor : fallbackUserShareMinor;

    return {
      type: 'debt' as const,
      amountMinor: payableMinor,
      signedAmountMinor: -payableMinor,
      label: 'پرداخت شما به پرداخت‌کننده',
    };
  }

  return { type: 'neutral' as const, amountMinor: 0, signedAmountMinor: 0, label: 'بدون اثر روی حساب شما' };
}

type ExpenseReceiptSource =
  | { kind: 'media'; id: string; contentType?: string; fileName?: string; downloadUrl?: string }
  | { kind: 'url'; url: string; contentType?: string; fileName?: string };

interface ReceiptPreviewState {
  title: string;
  sourceUrl: string;
  objectUrl?: string;
  contentType?: string;
  fileName?: string;
  downloadFileId?: string;
  downloadUrl?: string;
}

function getExpenseReceiptSource(
  expense: BackendExpense,
  visibleReceipt?: ReceiptListItem | null,
): ExpenseReceiptSource | null {
  const fileId = String(expense.receipt_file_id || '').trim();
  if (fileId) return { kind: 'media', id: fileId };

  const url = String(expense.receipt_url || '').trim();
  if (url) return { kind: 'url', url, fileName: getFileNameFromUrl(url) };

  if (visibleReceipt?.id) {
    return {
      kind: 'media',
      id: visibleReceipt.id,
      contentType: visibleReceipt.content_type,
      fileName: visibleReceipt.original_filename,
      downloadUrl: visibleReceipt.download_url,
    };
  }

  return null;
}

function getExpenseReceiptBusyKey(expense: BackendExpense, visibleReceipt?: ReceiptListItem | null) {
  const source = getExpenseReceiptSource(expense, visibleReceipt);
  if (!source) return '';
  return source.kind === 'media' ? source.id : source.url;
}

function getFileNameFromUrl(url: string, fallback = 'receipt') {
  try {
    const parsed = new URL(url, window.location.origin);
    const name = parsed.pathname.split('/').filter(Boolean).pop() || '';
    return decodeURIComponent(name) || fallback;
  } catch {
    return fallback;
  }
}

function looksLikeImageReceipt(contentType?: string, value?: string) {
  const normalizedType = String(contentType || '').toLowerCase();
  const normalizedValue = String(value || '').toLowerCase().split('?')[0];

  return (
    normalizedType.startsWith('image/') ||
    /\.(png|jpe?g|webp|gif|bmp|svg)$/i.test(normalizedValue)
  );
}

function looksLikePdfReceipt(contentType?: string, value?: string) {
  const normalizedType = String(contentType || '').toLowerCase();
  const normalizedValue = String(value || '').toLowerCase().split('?')[0];

  return normalizedType.includes('pdf') || normalizedValue.endsWith('.pdf');
}

function getSettlementStatusLabel(status?: string) {
  if (!status) return 'نامشخص';
  if (status === 'PENDING') return 'در انتظار';
  if (status === 'REPORTED') return 'گزارش پرداخت';
  if (status === 'CONFIRMED') return 'تأیید شده';
  if (status === 'REJECTED') return 'رد شده';
  if (status === 'CANCELLED') return 'لغو شده';
  if (status === 'ACTIVE') return 'فعال';
  if (status === 'DRAFT') return 'آماده';
  if (status === 'COMPLETED') return 'تکمیل شده';
  if (status === 'PENDING_CONFIRMATION') return 'در انتظار تأیید';
  if (status === 'EXPIRED') return 'منقضی شده';
  return humanizeMachineLabel(status, 'نامشخص');
}

function isOpenSettlementStatus(status?: string) {
  return !status || ['PENDING', 'PENDING_CONFIRMATION', 'REPORTED', 'ACTIVE', 'DRAFT'].includes(status);
}

function canReportPlanItem(item: SettlementPlanItem, plan?: SettlementPlan | null) {
  return plan?.status === 'ACTIVE' && ['PENDING', 'REJECTED'].includes(item.status || 'PENDING');
}

function canReviewPlanItem(item: SettlementPlanItem) {
  return item.status === 'REPORTED';
}

const dashboardCard =
  'dashboard-section-card rounded-[24px] border border-emerald-100/80 bg-white/95 text-text shadow-[0_18px_44px_rgba(15,23,42,0.075)] backdrop-blur dark:border-emerald-500/20 dark:bg-slate-950/90 dark:text-slate-100';

const dashboardQuietCard =
  'dashboard-section-card dashboard-section-card--quiet rounded-[24px] border border-emerald-100/70 bg-white/[0.90] text-text shadow-[0_12px_32px_rgba(15,23,42,0.055)] backdrop-blur dark:border-emerald-500/15 dark:bg-slate-950/80 dark:text-slate-100';

const dashboardRow =
  'dashboard-list-row dashboard-list-card rounded-[22px] border border-emerald-100/80 bg-white/[0.92] text-right text-text shadow-[0_8px_22px_rgba(15,23,42,0.035)] transition hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-white hover:shadow-[0_14px_32px_rgba(15,23,42,0.07)] dark:border-emerald-500/15 dark:bg-slate-900/80 dark:text-slate-100 dark:hover:border-emerald-400/30 dark:hover:bg-slate-900';

const controlRadius = 'rounded-[18px]';

const inputClass =
  'h-12 w-full rounded-[18px] border border-emerald-200/90 bg-white/90 px-4 text-right text-sm font-bold text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-400 focus:bg-white focus:ring-4 focus:ring-emerald-500/10 disabled:bg-slate-50 disabled:text-slate-400 dark:border-emerald-500/20 dark:bg-slate-900/80 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-emerald-400/50 dark:focus:bg-slate-900 dark:disabled:bg-slate-900/50 dark:disabled:text-slate-500';

const textareaClass =
  'min-h-[96px] w-full resize-none rounded-[18px] border border-emerald-200/90 bg-white/90 px-4 py-3 text-right text-sm font-semibold leading-7 text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-400 focus:bg-white focus:ring-4 focus:ring-emerald-500/10 disabled:bg-slate-50 disabled:text-slate-400 dark:border-emerald-500/20 dark:bg-slate-900/80 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-emerald-400/50 dark:focus:bg-slate-900 dark:disabled:bg-slate-900/50 dark:disabled:text-slate-500';

const scrollAreaClass =
  'min-h-0 overflow-y-auto overscroll-auto pl-1 pr-0 [scrollbar-width:thin] [scrollbar-color:rgba(16,185,129,0.45)_transparent] dark:[scrollbar-color:rgba(52,211,153,0.35)_transparent]';

function readDisplayString(value: unknown) {
  return typeof value === 'string' ? value.trim() : '';
}

function isEmailLikeValue(value?: string) {
  return Boolean(value && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value));
}

function pickUserFacingName(...values: unknown[]) {
  return values.map(readDisplayString).find((value) => value && !isEmailLikeValue(value)) || '';
}

function getMemberPreferredDisplayName(member?: BackendGroupMember) {
  if (!member) return '';

  return (
    pickUserFacingName(
      member.art_name,
      member.username,
      member.display_name,
      member.display_name_snapshot,
      member.full_name,
      member.name,
      [member.first_name, member.last_name].filter(Boolean).join(' '),
      member.user?.art_name,
      member.user?.username,
      member.user?.display_name,
      member.user?.full_name,
      member.user?.name,
      [member.user?.first_name, member.user?.last_name].filter(Boolean).join(' '),
      member.profile?.art_name,
      member.profile?.username,
      member.profile?.display_name,
      member.member?.art_name,
      member.member?.username,
      member.member?.display_name,
    ) || getMemberName(member)
  );
}

function getUserDisplayFromId(userId: string, members: BackendGroupMember[]) {
  const member = members.find((item) => getMemberUserId(item) === userId);
  return getMemberPreferredDisplayName(member) || 'عضو گروه';
}

function toPersianDateTime(value?: string) {
  if (!value) return 'زمان نامشخص';

  try {
    return new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function getActivityMeta(type: string) {
  const items: Record<string, { verb: string; icon: typeof ReceiptText; tone: string }> = {
    GROUP_CREATED: { verb: 'گروه را ساخت', icon: Users, tone: 'bg-violet-50 text-violet-600 dark:bg-violet-500/10 dark:text-violet-200' },
    GROUP_UPDATED: { verb: 'اطلاعات گروه را تغییر داد', icon: Settings, tone: 'bg-violet-50 text-violet-600 dark:bg-violet-500/10 dark:text-violet-200' },
    GROUP_ARCHIVED: { verb: 'گروه را آرشیو کرد', icon: Archive, tone: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-200' },
    GROUP_MEMBER_JOINED: { verb: 'به گروه پیوست', icon: Users, tone: 'bg-sky-50 text-sky-600 dark:bg-sky-500/10 dark:text-sky-200' },
    GROUP_INVITATION_CREATED: { verb: 'دعوت‌نامه گروه ساخت', icon: Link2, tone: 'bg-cyan-50 text-cyan-600 dark:bg-cyan-500/10 dark:text-cyan-200' },
    EXPENSE_CREATED: { verb: 'یک هزینه ثبت کرد', icon: ReceiptText, tone: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200' },
    EXPENSE_UPDATED: { verb: 'یک هزینه را ویرایش کرد', icon: Save, tone: 'bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-200' },
    EXPENSE_DELETED: { verb: 'یک هزینه را حذف کرد', icon: Trash2, tone: 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-200' },
    RECEIPT_UPLOADED: { verb: 'رسید هزینه را بارگذاری کرد', icon: Upload, tone: 'bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-200' },
    SETTLEMENT_REPORTED: { verb: 'پرداخت خود را ثبت کرد', icon: HandCoins, tone: 'bg-orange-50 text-orange-600 dark:bg-orange-500/10 dark:text-orange-200' },
    SETTLEMENT_CONFIRMED: { verb: 'دریافت پول را تأیید کرد', icon: Check, tone: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200' },
    SETTLEMENT_REJECTED: { verb: 'پرداخت ثبت‌شده را رد کرد', icon: X, tone: 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-200' },
    SETTLEMENT_PLAN_ACTIVATED: { verb: 'برنامه تسویه را فعال کرد', icon: Scale, tone: 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-200' },
    WALLET_PAYMENT_COMPLETED: { verb: 'پرداخت کیف پول را انجام داد', icon: WalletCards, tone: 'bg-teal-50 text-teal-600 dark:bg-teal-500/10 dark:text-teal-200' },
  };

  return items[type] || {
    verb: humanizeMachineLabel(type, 'یک تغییر در گروه انجام داد'),
    icon: History,
    tone: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-200',
  };
}

function getActivityActorName(activity: DashboardActivityItem, members: BackendGroupMember[]) {
  return activity.actor?.art_name?.trim() ||
    (activity.actor?.user_id ? getUserDisplayFromId(activity.actor.user_id, members) : 'سیستم');
}

function getActivityDetails(activity: DashboardActivityItem, members: BackendGroupMember[]) {
  const details: Array<{ label: string; value: string }> = [];
  const amount = Number(activity.summary.amount_minor || 0);
  const payerId = typeof activity.summary.payer_user_id === 'string' ? activity.summary.payer_user_id : '';
  const receiverId = typeof activity.summary.receiver_user_id === 'string' ? activity.summary.receiver_user_id : '';
  const status = typeof activity.summary.status === 'string' ? activity.summary.status : '';
  const title = typeof activity.summary.title === 'string' ? activity.summary.title : '';
  const description = typeof activity.summary.description === 'string' ? activity.summary.description : '';
  const role = typeof activity.summary.role === 'string' ? activity.summary.role : '';
  const currentUserEffectLabel = typeof activity.summary.current_user_effect_label === 'string'
    ? activity.summary.current_user_effect_label
    : '';
  const currentUserEffectMinor = Number(activity.summary.current_user_effect_minor || 0);
  const currentUserEffectSignedMinor = Number(activity.summary.current_user_effect_signed_minor || 0);

  if (title) details.push({ label: 'عنوان', value: title });
  if (Number.isFinite(amount) && amount > 0) details.push({ label: 'مبلغ کل', value: formatMoney(amount) });
  if (currentUserEffectLabel && Number.isFinite(currentUserEffectMinor) && currentUserEffectMinor > 0) {
    details.push({
      label: 'اثر روی حساب شما',
      value: `${currentUserEffectLabel}: ${formatSignedMoney(currentUserEffectSignedMinor)}`,
    });
  }
  if (payerId) details.push({ label: 'پرداخت‌کننده', value: getUserDisplayFromId(payerId, members) });
  if (receiverId) details.push({ label: 'دریافت‌کننده', value: getUserDisplayFromId(receiverId, members) });
  if (status) details.push({ label: 'وضعیت', value: getSettlementStatusLabel(status) });
  if (role) details.push({ label: 'نقش', value: getRoleLabel(role) });
  if (description) details.push({ label: 'توضیح', value: description });

  return details;
}

function buildGroupActivityFallback(
  groupId: string,
  group: BackendGroup | null,
  members: BackendGroupMember[],
  expenses: BackendExpense[],
  settlements: SettlementItem[],
  currentUserId?: string | null,
) {
  const items: DashboardActivityItem[] = [];
  const groupInfo = { id: groupId, title: group?.title || '' };

  if (group?.created_at) {
    items.push({
      id: `group-created-${groupId}`,
      type: 'GROUP_CREATED',
      group: groupInfo,
      actor: group.created_by_user_id ? { user_id: group.created_by_user_id } : null,
      occurred_at: group.created_at,
      summary: { title: group.title },
    });
  }

  if (group?.updated_at && group.updated_at !== group.created_at) {
    items.push({
      id: `group-updated-${groupId}-${group.updated_at}`,
      type: group.status === 'ARCHIVED' ? 'GROUP_ARCHIVED' : 'GROUP_UPDATED',
      group: groupInfo,
      actor: null,
      occurred_at: group.updated_at,
      summary: { title: group.title, description: group.description || '' },
    });
  }

  members.forEach((member) => {
    const userId = getMemberUserId(member);
    if (!userId || !member.joined_at) return;
    items.push({
      id: `member-joined-${groupId}-${getMemberId(member) || userId}`,
      type: 'GROUP_MEMBER_JOINED',
      group: groupInfo,
      actor: { user_id: userId, art_name: getMemberPreferredDisplayName(member) },
      occurred_at: member.joined_at,
      summary: { role: member.role || 'MEMBER' },
    });
  });

  expenses
    .filter((expense) => String(expense.group_id || groupId) === String(groupId))
    .forEach((expense) => {
      const currentUserImpact = getExpenseUserImpact(expense, currentUserId, members.length || 1);

      if (expense.created_at) {
        items.push({
          id: `expense-created-${expense.id}`,
          type: expense.status === 'DELETED' ? 'EXPENSE_DELETED' : 'EXPENSE_CREATED',
          group: groupInfo,
          actor: { user_id: expense.created_by_user_id || expense.payer_user_id },
          occurred_at: expense.created_at,
          summary: {
            title: expense.title,
            description: expense.description || '',
            payer_user_id: expense.payer_user_id,
            amount_minor: getExpenseTotal(expense),
            status: expense.status || 'ACTIVE',
            current_user_effect_label: currentUserImpact.label,
            current_user_effect_minor: currentUserImpact.amountMinor,
            current_user_effect_signed_minor: currentUserImpact.signedAmountMinor,
            current_user_effect_type: currentUserImpact.type,
          },
        });
      }

      if (expense.updated_at && expense.updated_at !== expense.created_at && expense.status !== 'DELETED') {
        items.push({
          id: `expense-updated-${expense.id}-${expense.updated_at}`,
          type: 'EXPENSE_UPDATED',
          group: groupInfo,
          actor: { user_id: expense.created_by_user_id || expense.payer_user_id },
          occurred_at: expense.updated_at,
          summary: {
            title: expense.title,
            payer_user_id: expense.payer_user_id,
            amount_minor: getExpenseTotal(expense),
            status: expense.status || 'ACTIVE',
            current_user_effect_label: currentUserImpact.label,
            current_user_effect_minor: currentUserImpact.amountMinor,
            current_user_effect_signed_minor: currentUserImpact.signedAmountMinor,
            current_user_effect_type: currentUserImpact.type,
          },
        });
      }

      if (expense.receipt_file_id && (expense.updated_at || expense.created_at)) {
        items.push({
          id: `receipt-uploaded-${expense.id}-${expense.receipt_file_id}`,
          type: 'RECEIPT_UPLOADED',
          group: groupInfo,
          actor: { user_id: expense.created_by_user_id || expense.payer_user_id },
          occurred_at: expense.updated_at || expense.created_at || '',
          summary: { title: expense.title },
        });
      }
    });

  settlements
    .filter((settlement) => String(settlement.group_id || '') === String(groupId))
    .forEach((settlement) => {
      if (!settlement.created_at) return;
      const status = settlement.status || 'PENDING_CONFIRMATION';
      const type = status === 'CONFIRMED'
        ? 'SETTLEMENT_CONFIRMED'
        : status === 'REJECTED'
          ? 'SETTLEMENT_REJECTED'
          : 'SETTLEMENT_REPORTED';
      const actorId = type === 'SETTLEMENT_REPORTED'
        ? settlement.payer_user_id
        : settlement.receiver_user_id;

      items.push({
        id: `settlement-${settlement.id}-${status}`,
        type,
        group: groupInfo,
        actor: { user_id: actorId },
        occurred_at: settlement.created_at,
        summary: {
          payer_user_id: settlement.payer_user_id,
          receiver_user_id: settlement.receiver_user_id,
          amount_minor: settlement.amount_minor,
          status,
          description: settlement.description || '',
        },
      });
    });

  return items.sort((left, right) => {
    return new Date(right.occurred_at).getTime() - new Date(left.occurred_at).getTime();
  });
}

function getBalanceDisplayName(balance: BalanceItem, members: BackendGroupMember[]) {
  const memberName = getUserDisplayFromId(balance.user_id, members);
  const balanceRecord = balance as BalanceItem & { username?: string; name?: string; full_name?: string };

  return (
    memberName ||
    pickUserFacingName(
      balanceRecord.art_name,
      balanceRecord.username,
      balanceRecord.display_name,
      balanceRecord.full_name,
      balanceRecord.name,
      balanceRecord.phone_number,
    ) ||
    'عضو گروه'
  );
}

function getDebtPartyName(userId: string, members: BackendGroupMember[]) {
  return getUserDisplayFromId(userId, members);
}

function getPlanPartyName(
  item: SettlementPlanItem,
  type: 'payer' | 'receiver',
  members: BackendGroupMember[],
) {
  if (type === 'payer') {
    return (
      item.payer_display_name ||
      item.payer_art_name ||
      getUserDisplayFromId(item.payer_user_id, members)
    );
  }

  return (
    item.receiver_display_name ||
    item.receiver_art_name ||
    getUserDisplayFromId(item.receiver_user_id, members)
  );
}

interface OptimizedSettlementSuggestion {
  id: string;
  payer_user_id: string;
  payerName: string;
  receiver_user_id: string;
  receiverName: string;
  amount_minor: number;
}

function calculateOptimizedSettlements(
  balances: BalanceItem[],
  members: BackendGroupMember[],
): OptimizedSettlementSuggestion[] {
  const debtors = balances
    .map((balance) => ({
      userId: balance.user_id,
      name: getBalanceDisplayName(balance, members),
      amount: Math.max(0, Math.round(Math.abs(Math.min(balance.net_balance_minor || 0, 0)))),
    }))
    .filter((item) => item.userId && item.amount > 0)
    .sort((a, b) => b.amount - a.amount);

  const creditors = balances
    .map((balance) => ({
      userId: balance.user_id,
      name: getBalanceDisplayName(balance, members),
      amount: Math.max(0, Math.round(Math.max(balance.net_balance_minor || 0, 0))),
    }))
    .filter((item) => item.userId && item.amount > 0)
    .sort((a, b) => b.amount - a.amount);

  const suggestions: OptimizedSettlementSuggestion[] = [];
  let debtorIndex = 0;
  let creditorIndex = 0;

  while (debtorIndex < debtors.length && creditorIndex < creditors.length) {
    const debtor = debtors[debtorIndex];
    const creditor = creditors[creditorIndex];
    const amount = Math.min(debtor.amount, creditor.amount);

    if (amount > 0 && debtor.userId !== creditor.userId) {
      suggestions.push({
        id: `optimized-${debtor.userId}-${creditor.userId}-${suggestions.length}`,
        payer_user_id: debtor.userId,
        payerName: debtor.name,
        receiver_user_id: creditor.userId,
        receiverName: creditor.name,
        amount_minor: amount,
      });
    }

    debtor.amount -= amount;
    creditor.amount -= amount;

    if (debtor.amount <= 0) debtorIndex += 1;
    if (creditor.amount <= 0) creditorIndex += 1;
  }

  return suggestions;
}

function getSettlementErrorTitle(action: 'create' | 'plan' | 'item' | 'review') {
  if (action === 'create') return 'پرداخت ثبت نشد';
  if (action === 'plan') return 'محاسبه تسویه انجام نشد';
  if (action === 'item') return 'وضعیت پرداخت تغییر نکرد';
  return 'تأیید پرداخت انجام نشد';
}

function getSettlementErrorDescription(error: unknown) {
  const message = getBackendMessage(error);
  const normalized = message.toLowerCase();

  if (normalized.includes('403') || normalized.includes('permission') || normalized.includes('forbidden')) {
    return 'برای انجام این کار دسترسی نداری یا عضو این گروه نیستی.';
  }

  if (normalized.includes('404') || normalized.includes('not found')) {
    return 'این پرداخت یا گروه پیدا نشد. صفحه را تازه کن و دوباره امتحان کن.';
  }

  if (normalized.includes('amount') || normalized.includes('مبلغ')) {
    return 'مبلغ پرداخت را دقیق و به عدد وارد کن.';
  }

  if (normalized.includes('receiver') || normalized.includes('دریافت')) {
    return 'دریافت‌کننده معتبر نیست. یکی از اعضای گروه را انتخاب کن.';
  }

  return message || 'اطلاعات پرداخت کامل نیست یا ارتباط قطع شده است. صفحه را تازه کن و دوباره امتحان کن.';
}

type VisualTone = 'positive' | 'negative' | 'warning' | 'sky' | 'slate' | 'neutral';
type QuickSection = 'expenses' | 'settlement' | 'settings' | 'members' | 'activity';

function getMyAccountStatus(amount: number) {
  if (amount > 0) {
    return {
      label: 'طلبکار',
      amount: formatSignedMoney(amount),
      tone: 'positive' as VisualTone,
    };
  }

  if (amount < 0) {
    return {
      label: 'بدهکار',
      amount: formatSignedMoney(amount),
      tone: 'negative' as VisualTone,
    };
  }

  return {
    label: 'تسویه',
    amount: formatSignedMoney(amount),
    tone: 'slate' as VisualTone,
  };
}

function getRemainingPaymentsLabel(count: number) {
  return count > 0 ? `${toPersianNumber(count)} پرداخت` : 'بدون پرداخت';
}

function scrollToSection(id: QuickSection) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function MemberAvatar({ name, owner = false }: { name: string; owner?: boolean }) {
  return (
    <div
      className={cn(
        'flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2 text-sm font-black shadow-[inset_3px_0_0_#10B981,0_10px_28px_rgba(15,23,42,0.045)]',
        owner
          ? 'border-orange-300 bg-orange-50 text-orange-700'
          : 'border-emerald-100 bg-gradient-to-br from-emerald-50 via-teal-50 to-white text-emerald-700',
      )}
    >
      {name.slice(0, 1) || '؟'}
    </div>
  );
}

function toneCardClass(tone: VisualTone) {
  if (tone === 'positive') {
    return 'border-2 border-emerald-200/80 bg-gradient-to-l from-white via-emerald-50/85 to-emerald-50/70 text-emerald-700 shadow-[inset_3px_0_0_#10B981,0_18px_44px_rgba(16,185,129,0.075)]';
  }

  if (tone === 'negative') {
    return 'border-2 border-rose-200/80 bg-gradient-to-l from-white via-rose-50/85 to-rose-50/70 text-rose-600 shadow-[inset_3px_0_0_#F43F5E,0_18px_44px_rgba(244,63,94,0.07)]';
  }

  if (tone === 'warning') {
    return 'border-2 border-orange-200/80 bg-gradient-to-l from-white via-orange-50/85 to-orange-50/70 text-orange-700 shadow-[inset_3px_0_0_#F97316,0_18px_44px_rgba(249,115,22,0.07)]';
  }

  if (tone === 'sky') {
    return 'border-2 border-sky-200/80 bg-gradient-to-l from-white via-sky-50/85 to-sky-50/70 text-sky-700 shadow-[inset_3px_0_0_#0EA5E9,0_18px_44px_rgba(14,165,233,0.065)]';
  }

  if (tone === 'slate') {
    return 'border-2 border-slate-200 bg-gradient-to-l from-white via-slate-50/90 to-white text-slate-700 shadow-[inset_3px_0_0_#64748B,0_18px_44px_rgba(15,23,42,0.055)]';
  }

  return 'border-2 border-emerald-100/80 bg-white/[0.88] text-slate-700 shadow-[0_16px_38px_rgba(15,23,42,0.045)]';
}

function iconToneClass(tone: VisualTone) {
  if (tone === 'positive') return 'bg-emerald-600 text-white shadow-[0_12px_28px_rgba(16,185,129,0.16)]';
  if (tone === 'negative') return 'bg-rose-500 text-white shadow-[0_12px_28px_rgba(244,63,94,0.14)]';
  if (tone === 'warning') return 'bg-orange-500 text-white shadow-[0_12px_28px_rgba(249,115,22,0.14)]';
  if (tone === 'sky') return 'bg-sky-500 text-white shadow-[0_12px_28px_rgba(14,165,233,0.14)]';
  if (tone === 'slate') return 'bg-slate-700 text-white shadow-[0_12px_28px_rgba(15,23,42,0.10)]';
  return 'bg-white text-emerald-600 shadow-sm';
}

function SectionCard({
  id,
  title,
  icon,
  badge,
  children,
  accent = 'emerald',
}: {
  id?: string;
  title: string;
  icon?: ReactNode;
  badge?: ReactNode;
  children: ReactNode;
  accent?: 'emerald' | 'sky' | 'orange' | 'slate';
}) {
  const accentClass =
    accent === 'sky'
      ? 'border-sky-100/90 shadow-[0_20px_52px_rgba(14,165,233,0.055)]'
      : accent === 'orange'
        ? 'border-orange-100/90 shadow-[0_20px_52px_rgba(249,115,22,0.055)]'
        : accent === 'slate'
          ? 'border-slate-200 shadow-[0_20px_52px_rgba(15,23,42,0.045)]'
          : 'border-emerald-100/90 shadow-[0_20px_52px_rgba(15,23,42,0.055)]';

  const iconClass =
    accent === 'sky'
      ? 'bg-sky-50 text-sky-600 shadow-[inset_3px_0_0_#0EA5E9]'
      : accent === 'orange'
        ? 'bg-orange-50 text-orange-600 shadow-[inset_3px_0_0_#F97316]'
        : accent === 'slate'
          ? 'bg-slate-50 text-slate-600 shadow-[inset_3px_0_0_#64748B]'
          : 'bg-emerald-50 text-emerald-600 shadow-[inset_3px_0_0_#10B981]';

  return (
    <section
      id={id}
      className={cn(
        'scroll-mt-6 rounded-[28px] border-2 bg-white/95 p-5 backdrop-blur sm:p-6',
        accentClass,
      )}
    >
      <div className="mb-5 flex items-center justify-between gap-4 border-b-2 border-emerald-50/70 pb-4">
        <div className="text-right">
          <h2 className="text-xl font-black text-text sm:text-2xl">{title}</h2>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {badge}
          {icon ? (
            <div className={cn('flex h-12 w-12 items-center justify-center rounded-[18px]', iconClass)}>
              {icon}
            </div>
          ) : null}
        </div>
      </div>

      {children}
    </section>
  );
}

function HeaderMiniCard({
  label,
  value,
  status,
  tone = 'neutral',
  icon,
}: {
  label: string;
  value: string;
  status?: string;
  tone?: 'neutral' | 'positive' | 'negative';
  icon: ReactNode;
}) {
  const visualTone: VisualTone =
    tone === 'positive' ? 'positive' : tone === 'negative' ? 'negative' : 'slate';

  return (
    <div className={cn('rounded-[22px] px-4 py-3 text-right', toneCardClass(visualTone))}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-black opacity-70">{label}</div>
          {status ? <div className="mt-1 text-sm font-black">{status}</div> : null}
          <div className="mt-1 text-lg font-black tracking-[-0.02em]">{value}</div>
        </div>

        <span className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-[16px]', iconToneClass(visualTone))}>
          {icon}
        </span>
      </div>
    </div>
  );
}

function AccountStatusBox({ amount }: { amount: number }) {
  const status = getMyAccountStatus(amount);

  return (
    <div className={cn('rounded-[24px] p-4 text-right', toneCardClass(status.tone))}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-black">حساب من</div>
          <div className="mt-1 text-xs font-bold opacity-75">وضعیت تو در این گروه</div>
        </div>

        <span className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-[16px]', iconToneClass(status.tone))}>
          <HandCoins className="h-4 w-4" />
        </span>
      </div>

      <div className="text-2xl font-black tracking-[-0.03em]">{status.label}</div>
      <div className="mt-2 text-lg font-black">{status.amount}</div>
    </div>
  );
}

function RemainingPaymentsBox({
  count,
  totalMinor,
  tone = 'slate',
}: {
  count: number;
  totalMinor: number;
  tone?: VisualTone;
}) {
  const hasPayments = count > 0;

  return (
    <div className={cn('rounded-[24px] p-4 text-right', toneCardClass(tone))}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-black">پرداخت‌های مانده</div>
          <div className="mt-1 text-xs font-bold opacity-75">
            {hasPayments ? 'جمع پرداخت‌های باقی‌مانده' : 'چیزی باقی نمانده.'}
          </div>
        </div>

        <span className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-[16px]', iconToneClass(tone))}>
          <ReceiptText className="h-4 w-4" />
        </span>
      </div>

      <div className="text-2xl font-black tracking-[-0.03em]">
        {getRemainingPaymentsLabel(count)}
      </div>

      <div className="mt-2 text-lg font-black">
        {hasPayments ? formatMoney(totalMinor) : formatMoney(0)}
      </div>
    </div>
  );
}

function EmptyState({ title, description, icon }: { title: string; description: string; icon?: ReactNode }) {
  return (
    <div className="rounded-[22px] border-2 border-dashed border-emerald-100/80 bg-white/[0.58] p-7 text-center shadow-[0_16px_38px_rgba(15,23,42,0.035)]">
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-[18px] bg-white text-emerald-600 shadow-sm">
        {icon ?? <Users className="h-6 w-6" />}
      </div>

      <h3 className="text-lg font-black text-text">{title}</h3>

      <p className="mx-auto mt-2 max-w-[420px] text-sm font-semibold leading-7 text-muted">
        {description}
      </p>
    </div>
  );
}

function QuickActionButton({
  id,
  label,
  icon,
  tone = 'emerald',
}: {
  id: QuickSection;
  label: string;
  icon: ReactNode;
  tone?: 'emerald' | 'sky' | 'orange' | 'slate';
}) {
  const toneClass =
    tone === 'sky'
      ? 'border-sky-200/90 bg-gradient-to-l from-white via-sky-50/90 to-sky-50/70 text-sky-700 shadow-[inset_3px_0_0_#0EA5E9,0_16px_36px_rgba(14,165,233,0.055)] hover:border-sky-300'
      : tone === 'orange'
        ? 'border-orange-200/90 bg-gradient-to-l from-white via-orange-50/90 to-orange-50/70 text-orange-700 shadow-[inset_3px_0_0_#F97316,0_16px_36px_rgba(249,115,22,0.055)] hover:border-orange-300'
        : tone === 'slate'
          ? 'border-slate-200 bg-gradient-to-l from-white via-slate-50 to-white text-slate-700 shadow-[inset_3px_0_0_#64748B,0_16px_36px_rgba(15,23,42,0.04)] hover:border-slate-300'
          : 'border-emerald-200/90 bg-gradient-to-l from-white via-emerald-50/90 to-emerald-50/70 text-emerald-700 shadow-[inset_3px_0_0_#10B981,0_16px_36px_rgba(16,185,129,0.055)] hover:border-emerald-300';

  return (
    <button
      type="button"
      onClick={() => scrollToSection(id)}
      className={cn(
        'inline-flex h-[76px] w-full flex-col items-center justify-center gap-1.5 rounded-[20px] border-2 px-4 text-sm font-black transition hover:-translate-y-0.5 hover:shadow-[0_20px_44px_rgba(15,23,42,0.07)]',
        toneClass,
      )}
    >
      <span className="flex h-5 w-5 items-center justify-center">
        {icon}
      </span>
      <span>{label}</span>
    </button>
  );
}

function Button({
  children,
  onClick,
  disabled,
  tone = 'primary',
  className,
  type = 'button',
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  tone?: 'primary' | 'secondary' | 'danger' | 'dark' | 'ghost';
  className?: string;
  type?: 'button' | 'submit';
}) {
  const toneClass =
    tone === 'primary'
      ? 'bg-emerald-600 text-white shadow-[0_14px_32px_rgba(16,185,129,0.22)] ring-1 ring-emerald-500/20 hover:-translate-y-0.5 hover:bg-emerald-700 dark:bg-emerald-500 dark:text-white dark:hover:bg-emerald-400'
      : tone === 'danger'
        ? 'border border-rose-200 bg-rose-50 text-rose-600 hover:bg-rose-100 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200 dark:hover:bg-rose-500/15'
        : tone === 'dark'
          ? 'bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-950 dark:hover:bg-white'
          : tone === 'ghost'
            ? 'bg-transparent text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
            : 'border border-emerald-200 bg-emerald-50/80 text-emerald-700 shadow-[0_10px_24px_rgba(15,23,42,0.045)] hover:-translate-y-0.5 hover:border-emerald-300 hover:bg-emerald-50 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-200 dark:hover:border-emerald-400/40 dark:hover:bg-emerald-500/15';

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex min-h-11 items-center justify-center gap-2 px-4 text-sm font-black transition disabled:cursor-not-allowed disabled:opacity-55 disabled:hover:translate-y-0',
        controlRadius,
        toneClass,
        className,
      )}
    >
      {children}
    </button>
  );
}

function ActionButton({
  children,
  onClick,
  disabled,
  tone = 'primary',
  className,
  type = 'button',
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  tone?: 'primary' | 'secondary' | 'danger' | 'dark' | 'ghost';
  className?: string;
  type?: 'button' | 'submit';
}) {
  const toneClass =
    tone === 'primary'
      ? 'bg-emerald-600 text-white shadow-[0_14px_32px_rgba(16,185,129,0.22)] ring-1 ring-emerald-500/20 hover:-translate-y-0.5 hover:bg-emerald-700 dark:bg-emerald-500 dark:text-white dark:hover:bg-emerald-400'
      : tone === 'danger'
        ? 'border border-rose-200 bg-rose-50 text-rose-600 hover:bg-rose-100 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200 dark:hover:bg-rose-500/15'
        : tone === 'dark'
          ? 'bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-950 dark:hover:bg-white'
          : tone === 'ghost'
            ? 'bg-transparent text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
            : 'border border-emerald-200 bg-emerald-50/80 text-emerald-700 shadow-[0_10px_24px_rgba(15,23,42,0.045)] hover:-translate-y-0.5 hover:border-emerald-300 hover:bg-emerald-50 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-200 dark:hover:border-emerald-400/40 dark:hover:bg-emerald-500/15';

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex min-h-11 items-center justify-center gap-2 px-4 text-sm font-black transition disabled:cursor-not-allowed disabled:opacity-55 disabled:hover:translate-y-0',
        controlRadius,
        toneClass,
        className,
      )}
    >
      {children}
    </button>
  );
}

function Modal({
  open,
  title,
  description,
  icon,
  children,
  onClose,
  size = 'md',
}: {
  open: boolean;
  title: string;
  description?: string;
  icon?: ReactNode;
  children: ReactNode;
  onClose: () => void;
  size?: 'md' | 'lg' | 'xl';
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/36 px-3 py-3 backdrop-blur-sm sm:items-center dark:bg-black/55"
      dir="rtl"
    >
      <div
        className={cn(
          'max-h-[92vh] w-full overflow-hidden rounded-[32px] border border-white/90 bg-white text-right text-text shadow-[0_28px_90px_rgba(15,23,42,0.18)] dark:border-emerald-500/15 dark:bg-slate-950 dark:text-slate-100 dark:shadow-[0_28px_90px_rgba(0,0,0,0.45)]',
          size === 'xl' ? 'max-w-[1080px]' : size === 'lg' ? 'max-w-[900px]' : 'max-w-[620px]',
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-emerald-100/70 bg-white/[0.45] px-4 py-4 sm:px-5 dark:border-emerald-500/15 dark:bg-slate-900/60">
          <div className="flex min-w-0 items-start gap-3 text-right">
            {icon ? (
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[18px] bg-emerald-50 text-emerald-600 shadow-[inset_3px_0_0_#10B981] dark:bg-emerald-500/10 dark:text-emerald-300 dark:shadow-[inset_3px_0_0_#34D399]">
                {icon}
              </span>
            ) : null}

            <div className="min-w-0 text-right">
              <h2 className="text-xl font-black tracking-[-0.03em] text-text dark:text-slate-100">{title}</h2>
              {description ? (
                <p className="mt-1 text-sm font-bold leading-6 text-muted dark:text-slate-400">{description}</p>
              ) : null}
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[18px] bg-slate-50 text-slate-500 transition hover:bg-rose-50 hover:text-rose-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-rose-500/10 dark:hover:text-rose-200"
            aria-label="بستن"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="max-h-[calc(92vh-92px)] overflow-y-auto px-4 py-4 text-right sm:px-5">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-right">
      <span className="mb-2 block text-sm font-black text-text dark:text-slate-100">{label}</span>
      {children}
    </label>
  );
}

function MetaTags({ user, date }: { user: string; date: string }) {
  return (
    <div className="mt-2 flex flex-wrap items-center justify-start gap-2 text-right text-xs font-semibold text-muted dark:text-slate-400">
      <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300">
        {user}
      </span>

      <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300">
        {date}
      </span>
    </div>
  );
}

function MiniNumberCard({
  label,
  value,
  tone,
  signed = false,
}: {
  label: string;
  value: number | string | null | undefined;
  tone: 'rose' | 'emerald' | 'slate';
  signed?: boolean;
}) {
  const classes =
    tone === 'rose'
      ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200'
      : tone === 'emerald'
        ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200'
        : 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-200';

  return (
    <div className={cn('rounded-[20px] border px-4 py-3 text-right', classes)}>
      <p className="text-xs font-extrabold opacity-75">{label}</p>
      <div className="mt-1">
        <MoneyWithWords
          amount={value}
          signed={signed}
          className="min-w-0"
          valueClassName="truncate text-lg font-black"
          textClassName="mt-1 text-[10px] font-semibold opacity-70"
          showText={true}
        />
      </div>
    </div>
  );
}

function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="dashboard-section-header mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[20px] border border-transparent p-0 text-right">
      <h2 className="text-lg font-black tracking-[-0.02em] text-text dark:text-slate-100">{title}</h2>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function GroupDetailPage({
  groupId,
  onBack,
  onGroupUpdated,
  onGroupRemoved,
}: GroupDetailPageProps) {
  const { notify, confirm } = useFeedback();
  const activitiesGroupIdRef = useRef(groupId);
  activitiesGroupIdRef.current = groupId;

  const [modal, setModal] = useState<ModalName>(null);
  const [activeView, setActiveView] = useState<GroupDetailView>('expenses');
  const [showAdvancedExpense, setShowAdvancedExpense] = useState(false);

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [group, setGroup] = useState<BackendGroup | null>(null);
  const [members, setMembers] = useState<BackendGroupMember[]>([]);
  const [expenses, setExpenses] = useState<BackendExpense[]>([]);
  const [expenseReceiptsByExpenseId, setExpenseReceiptsByExpenseId] = useState<Record<string, ReceiptListItem[]>>({});
  const [balances, setBalances] = useState<BalanceItem[]>([]);
  const [debts, setDebts] = useState<DebtItem[]>([]);
  const [myBalance, setMyBalance] = useState<MyBalanceResponse | null>(null);
  const [settlementPlan, setSettlementPlan] = useState<SettlementPlan | null>(null);
  const [settlements, setSettlements] = useState<SettlementItem[]>([]);
  const [reminderSettings, setReminderSettings] = useState<GroupReminderSettings | null>(null);
  const [activities, setActivities] = useState<DashboardActivityItem[]>([]);
  const [activitiesNextCursor, setActivitiesNextCursor] = useState<string | null>(null);
  const [invite, setInvite] = useState<CreatedInvite | null>(null);
  const [directInviteSearch, setDirectInviteSearch] = useState('');
  const [directInviteResults, setDirectInviteResults] = useState<UserSearchResult[]>([]);
  const [directInviteLoading, setDirectInviteLoading] = useState(false);
  const [directInviteError, setDirectInviteError] = useState('');
  const [sendingDirectInviteId, setSendingDirectInviteId] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [groupType, setGroupType] = useState<BackendGroupType>('GENERAL');

  const [expenseTitle, setExpenseTitle] = useState('');
  const [expenseAmount, setExpenseAmount] = useState('');
  const [expenseDescription, setExpenseDescription] = useState('');
  const [expensePayerId, setExpensePayerId] = useState('');
  const [expenseParticipantIds, setExpenseParticipantIds] = useState<string[]>([]);
  const [expenseSplitMethod, setExpenseSplitMethod] = useState<ExpenseSplitMethod>('EQUAL');
  const [expenseCustomShares, setExpenseCustomShares] = useState<Record<string, string>>({});
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [openingReceiptId, setOpeningReceiptId] = useState<string | null>(null);
  const [receiptPreview, setReceiptPreview] = useState<ReceiptPreviewState | null>(null);

  const [manualReceiverId, setManualReceiverId] = useState('');
  const [manualAmount, setManualAmount] = useState('');
  const [manualDescription, setManualDescription] = useState('');
  const [manualPaymentMode, setManualPaymentMode] = useState<ManualPaymentMode>('FULL');
  const [selectedManualPlanItemId, setSelectedManualPlanItemId] = useState('');
  const [settlementModalTab, setSettlementModalTab] = useState<SettlementModalTab>('suggestion');
  const [enableReminderAfterExpense, setEnableReminderAfterExpense] = useState(false);
  const [sendExpenseReminderImmediately, setSendExpenseReminderImmediately] = useState(false);

  const [loading, setLoading] = useState(true);
  const [membersLoading, setMembersLoading] = useState(true);
  const [expensesLoading, setExpensesLoading] = useState(true);
  const [settlementLoading, setSettlementLoading] = useState(true);
  const [activitiesLoading, setActivitiesLoading] = useState(true);
  const [activitiesLoadingMore, setActivitiesLoadingMore] = useState(false);
  const [activitiesError, setActivitiesError] = useState<string | null>(null);
  const [settlementDataError, setSettlementDataError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [expenseSaving, setExpenseSaving] = useState(false);
  const [settlementSaving, setSettlementSaving] = useState(false);
  const [walletAvailableMinor, setWalletAvailableMinor] = useState(0);
  const [walletPaymentItemId, setWalletPaymentItemId] = useState<string | null>(null);
  const [walletTopUpItem, setWalletTopUpItem] = useState<SettlementPlanItem | null>(null);
  const [walletTopUpProvider, setWalletTopUpProvider] = useState<PaymentProvider>('FAKE');
  const [walletTopUpLoading, setWalletTopUpLoading] = useState(false);
  const [reminderLoading, setReminderLoading] = useState(false);
  const [reminderSaving, setReminderSaving] = useState(false);
  const [reminderRunning, setReminderRunning] = useState(false);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [leaveLoading, setLeaveLoading] = useState(false);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [autoSettlementTried, setAutoSettlementTried] = useState(false);

  const inviteUrl = useMemo(() => (invite ? getInviteUrl(invite) : ''), [invite]);
  const memberUserIds = useMemo(
    () => new Set(members.map((member) => getMemberUserId(member)).filter(Boolean)),
    [members],
  );

  const currentUserId = getCurrentUserId(currentUser);
  const isArchived = group?.status === 'ARCHIVED';
  const isOwner = group?.my_role === 'OWNER';
  const canManageGroup = ['OWNER', 'ADMIN'].includes(group?.my_role || '');

  const activeExpenses = useMemo(
    () => expenses.filter((expense) => expense.status !== 'DELETED' && expense.status !== 'CANCELLED'),
    [expenses],
  );

  const recentExpenses = useMemo(() => {
    return [...activeExpenses].sort((a, b) => {
      const left = new Date(a.expense_date || a.created_at || 0).getTime();
      const right = new Date(b.expense_date || b.created_at || 0).getTime();
      return right - left;
    });
  }, [activeExpenses]);

  function getVisibleReceiptForExpense(expense: BackendExpense) {
    return expenseReceiptsByExpenseId[expense.id]?.[0] || null;
  }

  function getResolvedExpenseReceiptSource(expense: BackendExpense) {
    return getExpenseReceiptSource(expense, getVisibleReceiptForExpense(expense));
  }

  function getResolvedExpenseReceiptBusyKey(expense: BackendExpense) {
    return getExpenseReceiptBusyKey(expense, getVisibleReceiptForExpense(expense));
  }

  function canCurrentUserViewExpenseReceipt(expense: BackendExpense) {
    if (!currentUserId || !getResolvedExpenseReceiptSource(expense)) return false;

    if (expense.payer_user_id === currentUserId || expense.created_by_user_id === currentUserId) {
      return true;
    }

    if (expense.participants?.length) {
      return expense.participants.some(
        (participant) => participant.user_id === currentUserId && participant.is_included !== false,
      );
    }

    // اگر بک‌اند لیست participants را در پاسخ هزینه ندهد، همین که receipt از API مجاز
    // /users/me/receipts برگشته یعنی کاربر اجازه دیدن آن را دارد.
    return Boolean(getVisibleReceiptForExpense(expense));
  }

  const allPlanItems = settlementPlan?.items || [];
  const openPlanItems = allPlanItems.filter((item) => isOpenSettlementStatus(item.status));
  const myDebtItems = openPlanItems.filter((item) => item.payer_user_id === currentUserId);
  const myCreditItems = openPlanItems.filter((item) => item.receiver_user_id === currentUserId);
  const pendingReceivedPlanItems = myCreditItems.filter(canReviewPlanItem);
  const myRegisteredSettlements = currentUserId
    ? settlements.filter((item) => item.payer_user_id === currentUserId || item.receiver_user_id === currentUserId)
    : settlements;
  const myPendingOutgoingSettlements = myRegisteredSettlements.filter(
    (item) =>
      item.payer_user_id === currentUserId &&
      ['PENDING', 'PENDING_CONFIRMATION', 'REPORTED'].includes(item.status || 'PENDING_CONFIRMATION') &&
      !myDebtItems.some(
        (planItem) =>
          planItem.receiver_user_id === item.receiver_user_id &&
          planItem.amount_minor === item.amount_minor &&
          planItem.status === 'REPORTED',
      ),
  );
  const pendingPlanManualSettlementIds = new Set(
    pendingReceivedPlanItems
      .map((item) => item.manual_settlement_id)
      .filter((id): id is string => Boolean(id)),
  );
  const myPendingIncomingSettlements = myRegisteredSettlements.filter(
    (item) =>
      item.receiver_user_id === currentUserId &&
      item.status === 'PENDING_CONFIRMATION' &&
      !pendingPlanManualSettlementIds.has(item.id),
  );
  const pendingConfirmationCount = pendingReceivedPlanItems.length + myPendingIncomingSettlements.length;

  const totalMyDebtMinor = myDebtItems.reduce((sum, item) => sum + (item.amount_minor || 0), 0);
  const totalMyCreditMinor = myCreditItems.reduce((sum, item) => sum + (item.amount_minor || 0), 0);

  const manualPayOptions = openPlanItems.filter(
    (item) => item.payer_user_id === currentUserId && ['PENDING', 'REJECTED'].includes(item.status || 'PENDING'),
  );

  const totalExpenseMinor = activeExpenses.reduce((sum, expense) => sum + getExpenseTotal(expense), 0);
  const optimizedSettlements = useMemo(
    () => calculateOptimizedSettlements(balances, members),
    [balances, members],
  );
  const fallbackPaymentSuggestions = optimizedSettlements.filter(
    (suggestion) =>
      suggestion.payer_user_id === currentUserId &&
      !openPlanItems.some(
        (item) =>
          item.payer_user_id === suggestion.payer_user_id &&
          item.receiver_user_id === suggestion.receiver_user_id,
      ) &&
      !settlements.some(
        (item) =>
          item.payer_user_id === suggestion.payer_user_id &&
          item.receiver_user_id === suggestion.receiver_user_id &&
          ['PENDING', 'PENDING_CONFIRMATION', 'REPORTED'].includes(item.status || 'PENDING_CONFIRMATION'),
      ),
  );
  const fallbackReceiptSuggestions = optimizedSettlements.filter(
    (suggestion) =>
      suggestion.receiver_user_id === currentUserId &&
      !openPlanItems.some(
        (item) =>
          item.payer_user_id === suggestion.payer_user_id &&
          item.receiver_user_id === suggestion.receiver_user_id,
      ) &&
      !settlements.some(
        (item) =>
          item.payer_user_id === suggestion.payer_user_id &&
          item.receiver_user_id === suggestion.receiver_user_id &&
          ['PENDING', 'PENDING_CONFIRMATION', 'REPORTED'].includes(item.status || 'PENDING_CONFIRMATION'),
      ),
  );
  const currentUserBalance = balances.find((balance) => balance.user_id === currentUserId);
  const myNetMinor = currentUserBalance?.net_balance_minor ?? myBalance?.net_balance_minor ?? 0;
  const myAccount = getMyAccountStatus(myNetMinor);
  const visibleMyDebtMinor = totalMyDebtMinor || fallbackPaymentSuggestions.reduce(
    (sum, item) => sum + item.amount_minor,
    0,
  );
  const visibleMyCreditMinor = totalMyCreditMinor || fallbackReceiptSuggestions.reduce(
    (sum, item) => sum + item.amount_minor,
    0,
  );
  const myLedgerEntries = useMemo(
    () => debts.filter(
      (item) => item.debtor_user_id === currentUserId || item.creditor_user_id === currentUserId,
    ),
    [currentUserId, debts],
  );
  const pairNetByUserId = useMemo(() => {
    const result = new Map<string, number>();
    myLedgerEntries.forEach((item) => {
      const isDebtor = item.debtor_user_id === currentUserId;
      const counterpartyId = isDebtor ? item.creditor_user_id : item.debtor_user_id;
      const signedAmount = isDebtor ? -(item.amount_minor || 0) : (item.amount_minor || 0);
      result.set(counterpartyId, (result.get(counterpartyId) || 0) + signedAmount);
    });
    return result;
  }, [currentUserId, myLedgerEntries]);
  const outstandingDetailedDebts = useMemo(() => {
    if (myNetMinor === 0) return [];
    const result: DebtItem[] = [];

    pairNetByUserId.forEach((pairNet, counterpartyId) => {
      let remainingMinor = Math.abs(pairNet);
      if (remainingMinor === 0) return;

      const currentUserOwes = pairNet < 0;
      const candidates = myLedgerEntries.filter((item) => {
        const isExpenseDebt = item.entry_type === 'EXPENSE_SHARE' || Boolean(item.source_expense_id);
        if (!isExpenseDebt) return false;
        return currentUserOwes
          ? item.debtor_user_id === currentUserId && item.creditor_user_id === counterpartyId
          : item.creditor_user_id === currentUserId && item.debtor_user_id === counterpartyId;
      });

      candidates.forEach((item) => {
        if (remainingMinor <= 0) return;
        const visibleAmount = Math.min(item.amount_minor || 0, remainingMinor);
        if (visibleAmount <= 0) return;
        result.push({ ...item, amount_minor: visibleAmount });
        remainingMinor -= visibleAmount;
      });
    });

    return result;
  }, [currentUserId, myLedgerEntries, myNetMinor, pairNetByUserId]);
  const detailedPayableMinor = outstandingDetailedDebts.reduce(
    (sum, item) => sum + (item.debtor_user_id === currentUserId ? item.amount_minor || 0 : 0),
    0,
  );
  const detailedReceivableMinor = outstandingDetailedDebts.reduce(
    (sum, item) => sum + (item.creditor_user_id === currentUserId ? item.amount_minor || 0 : 0),
    0,
  );
  const expenseById = useMemo(
    () => new Map(expenses.map((expense) => [expense.id, expense])),
    [expenses],
  );

  const optimizedTotalDebtMinor = optimizedSettlements.reduce(
    (sum, item) => sum + (item.amount_minor || 0),
    0,
  );
  const totalOpenDebtMinor = optimizedTotalDebtMinor;
  const remainingPaymentCount = optimizedSettlements.length;
  const backendPaymentCount = openPlanItems.length;

  const selectedManualPlanItem = manualPayOptions.find((item) => item.id === selectedManualPlanItemId) || null;

  const accountTitle = myNetMinor < 0 ? 'بدهکار هستی' : myNetMinor > 0 ? 'طلبکار هستی' : 'حسابت صاف است';
  const accountTone = myNetMinor < 0 ? 'rose' : myNetMinor > 0 ? 'emerald' : 'slate';

  const baseAmountMinor = parseAmountToMinor(expenseAmount);

  const expenseFinalTotalMinor = baseAmountMinor;

  const customSharesTotalMinor = expenseParticipantIds.reduce((sum, userId) => {
    return sum + parseAmountToMinor(expenseCustomShares[userId] || '');
  }, 0);

  async function loadGroup() {
    try {
      setLoading(true);
      const backendGroup = await getGroupDetail(groupId);

      setGroup(backendGroup);
      setTitle(backendGroup.title || '');
      setDescription(backendGroup.description || '');
      setGroupType(backendGroup.group_type || 'GENERAL');
      onGroupUpdated(backendGroup);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'اطلاعات گروه نمایش داده نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setLoading(false);
    }
  }

  async function loadMembers() {
    try {
      setMembersLoading(true);

      const [backendMembers, me] = await Promise.all([
        getGroupMembers(groupId),
        getCurrentUser().catch(() => null),
      ]);

      setCurrentUser(me);

      const currentUserName =
        me?.art_name ||
        me?.display_name ||
        me?.username ||
        [me?.first_name, me?.last_name].filter(Boolean).join(' ').trim() ||
        me?.phone_number ||
        me?.phone ||
        '';

      const normalizedMembers = backendMembers.map((member) => {
        const isCurrentUser = Boolean(me?.id) && getMemberUserId(member) === String(me?.id);
        if (!isCurrentUser || !currentUserName) return member;
        return { ...member, display_name: currentUserName };
      });

      setMembers(normalizedMembers);

      const ids = normalizedMembers.map(getMemberUserId).filter(Boolean);
      setExpenseParticipantIds(ids);
      setExpensePayerId(me?.id ? String(me.id) : ids[0] || '');
      setManualReceiverId(ids.find((id) => id !== String(me?.id || '')) || '');
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'اعضای گروه نمایش داده نشدند',
        description: getBackendMessage(err),
      });
    } finally {
      setMembersLoading(false);
    }
  }

  async function loadExpenses() {
    try {
      setExpensesLoading(true);
      const [expensesResult, receiptsResult] = await Promise.allSettled([
        listGroupExpenses(groupId, { page_size: 100 }),
        listMyVisibleReceipts({ group_id: groupId, page_size: 100 }),
      ]);

      if (expensesResult.status === 'rejected') {
        throw expensesResult.reason;
      }

      setExpenses(expensesResult.value);

      if (receiptsResult.status === 'fulfilled') {
        const receiptMap = receiptsResult.value.results.reduce<Record<string, ReceiptListItem[]>>((acc, receipt) => {
          const expenseId = String(receipt.expense_id || '').trim();
          if (!expenseId) return acc;
          acc[expenseId] = [...(acc[expenseId] || []), receipt];
          return acc;
        }, {});
        setExpenseReceiptsByExpenseId(receiptMap);
      } else {
        console.warn('Could not load visible receipts for group expenses.', receiptsResult.reason);
        setExpenseReceiptsByExpenseId({});
      }
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'هزینه‌های گروه نمایش داده نشدند',
        description: getBackendMessage(err),
      });
    } finally {
      setExpensesLoading(false);
    }
  }

  async function loadGroupActivities(cursor?: string, append = false) {
    const requestedGroupId = groupId;
    if (activitiesGroupIdRef.current !== requestedGroupId) return;
    void cursor;

    try {
      if (append) setActivitiesLoadingMore(true);
      else setActivitiesLoading(true);
      setActivitiesError(null);

      const [groupResult, membersResult, expensesResult, settlementsResult] = await Promise.allSettled([
        getGroupDetail(requestedGroupId),
        getGroupMembers(requestedGroupId),
        listGroupExpenses(requestedGroupId, { page_size: 100 }),
        listGroupSettlements(requestedGroupId),
      ]);

      if (activitiesGroupIdRef.current !== requestedGroupId) return;

      if ([groupResult, membersResult, expensesResult, settlementsResult].every((result) => result.status === 'rejected')) {
        const firstError = groupResult.status === 'rejected' ? groupResult.reason : new Error('Activity data unavailable');
        throw firstError;
      }

      const groupActivities = buildGroupActivityFallback(
        requestedGroupId,
        groupResult.status === 'fulfilled' ? groupResult.value : null,
        membersResult.status === 'fulfilled' ? membersResult.value : [],
        expensesResult.status === 'fulfilled' ? expensesResult.value : [],
        settlementsResult.status === 'fulfilled' ? settlementsResult.value : [],
        currentUserId,
      );

      setActivities((current) => {
        const combined = append ? [...current, ...groupActivities] : groupActivities;
        return combined.filter(
          (item, index) => combined.findIndex((candidate) => candidate.id === item.id) === index,
        );
      });
      setActivitiesNextCursor(null);
    } catch (err) {
      if (activitiesGroupIdRef.current !== requestedGroupId) return;
      console.error(err);
      setActivitiesError(getBackendMessage(err));
      if (!append) {
        setActivities([]);
        setActivitiesNextCursor(null);
      }
    } finally {
      if (activitiesGroupIdRef.current === requestedGroupId) {
        setActivitiesLoading(false);
        setActivitiesLoadingMore(false);
      }
    }
  }

  async function loadWalletBalance() {
    try {
      const wallet = await getMyWallet();
      setWalletAvailableMinor(wallet.available_balance_minor || 0);
    } catch (err) {
      console.warn('Wallet balance unavailable.', err);
      setWalletAvailableMinor(0);
    }
  }

  async function loadSettlementData() {
    try {
      setSettlementLoading(true);
      setSettlementDataError(null);

      const [balancesResult, myBalanceResult, debtsResult, planResult, settlementsResult, walletResult] = await Promise.allSettled([
        getGroupBalances(groupId),
        getMyGroupBalance(groupId),
        getGroupDebts(groupId),
        getSettlementPlan(groupId),
        listGroupSettlements(groupId),
        getMyWallet(),
      ]);

      setBalances(balancesResult.status === 'fulfilled' ? balancesResult.value.balances || [] : []);
      setMyBalance(myBalanceResult.status === 'fulfilled' ? myBalanceResult.value : null);
      setDebts(debtsResult.status === 'fulfilled' ? debtsResult.value.debts || [] : []);
      setSettlementPlan(planResult.status === 'fulfilled' ? planResult.value : null);
      setSettlements(settlementsResult.status === 'fulfilled' ? settlementsResult.value || [] : []);
      setWalletAvailableMinor(walletResult.status === 'fulfilled' ? walletResult.value.available_balance_minor || 0 : 0);

      const failedRequiredRequests = [balancesResult, myBalanceResult, debtsResult, settlementsResult]
        .filter((result) => result.status === 'rejected');

      if (failedRequiredRequests.length > 0) {
        failedRequiredRequests.forEach((result) => {
          if (result.status === 'rejected') console.warn('Group settlement request failed.', result.reason);
        });
        setSettlementDataError('فعلاً بخشی از اطلاعات تسویه نمایش داده نمی‌شود. چند لحظه بعد دوباره امتحان کن.');
      }

      if (planResult.status === 'rejected' && !(isApiError(planResult.reason) && planResult.reason.status === 404)) {
        console.warn('Settlement plan request failed.', planResult.reason);
        setSettlementDataError('پیشنهاد تسویه آماده نیست. برای ساخت پیشنهاد جدید، دوباره محاسبه کن.');
      }
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'اطلاعات تسویه نمایش داده نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setSettlementLoading(false);
    }
  }

  async function loadReminderSettings() {
    try {
      setReminderLoading(true);
      const settings = await getGroupReminderSettings(groupId);
      setReminderSettings(settings);
      return settings;
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'تنظیمات یادآوری نمایش داده نشد',
        description: getBackendMessage(err),
      });
      return null;
    } finally {
      setReminderLoading(false);
    }
  }

  async function saveReminderSettings(
    showNotification = true,
    overrides: Partial<GroupReminderSettings> = {},
  ) {
    if (!canManageGroup || !reminderSettings) return false;
    const nextSettings = { ...reminderSettings, ...overrides };
    if (nextSettings.is_enabled && !nextSettings.send_email && !nextSettings.send_in_app) {
      notify({
        type: 'error',
        title: 'روش ارسال یادآوری را انتخاب کن',
        description: 'برای ارسال یادآوری، حداقل ایمیل یا اعلان داخل برنامه را فعال کن.',
      });
      return false;
    }

    try {
      setReminderSaving(true);
      const saved = await updateGroupReminderSettings(groupId, {
        is_enabled: nextSettings.is_enabled,
        first_reminder_after_hours: nextSettings.first_reminder_after_hours,
        repeat_interval_hours: nextSettings.repeat_interval_hours,
        maximum_reminders: nextSettings.maximum_reminders,
        send_in_app: nextSettings.send_in_app,
        send_email: nextSettings.send_email,
      });
      setReminderSettings(saved);
      if (showNotification) {
        notify({
          type: 'success',
          title: 'تنظیمات یادآوری تغییرات ذخیره شد',
          description: 'از این به بعد یادآوری‌های همین گروه طبق برنامه‌ای که انتخاب کردی ارسال می‌شوند.',
        });
      }
      return true;
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'تنظیمات یادآوری ذخیره نشد',
        description: getBackendMessage(err),
      });
      return false;
    } finally {
      setReminderSaving(false);
    }
  }

  async function handleEnableGroupReminders() {
    if (!canManageGroup) return;
    try {
      setReminderRunning(true);
      const settingsSaved = await saveReminderSettings(false, {
        is_enabled: true,
        send_email: true,
      });
      if (!settingsSaved) return;

      const result = await runGroupReminders(groupId, true);
      notify({
        type: 'success',
        title: 'یادآوری ایمیلی فعال شد',
        description: result.eligible_count > 0
          ? `${toPersianNumber(result.eligible_count)} بدهی همین حالا آماده یادآوری است؛ بقیه نیز طبق زمان انتخاب‌شده بررسی می‌شوند.`
          : 'از این پس بدهی‌های باز طبق زمان انتخاب‌شده بررسی می‌شوند.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'یادآوری ارسال نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setReminderRunning(false);
    }
  }

  async function reloadAll() {
    await Promise.all([loadGroup(), loadMembers(), loadExpenses(), loadGroupActivities(), loadSettlementData(), loadReminderSettings()]);
  }

  useEffect(() => {
    setActiveView('expenses');
    setAutoSettlementTried(false);
    setSettlementPlan(null);
    setSettlements([]);
    setReminderSettings(null);
    setActivities([]);
    setExpenseReceiptsByExpenseId({});
    setActivitiesNextCursor(null);
    void reloadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  useEffect(() => {
    const query = directInviteSearch.trim().replace(/^@/, '');

    if (modal !== 'settings' || query.length < 2) {
      setDirectInviteResults([]);
      setDirectInviteLoading(false);
      setDirectInviteError('');
      return;
    }

    let ignore = false;
    const timeoutId = window.setTimeout(async () => {
      try {
        setDirectInviteLoading(true);
        setDirectInviteError('');
        const results = await searchUsersByArtName(query, 12);

        if (ignore) return;

        setDirectInviteResults(
          results.filter((result) => result.user_id !== currentUserId && !memberUserIds.has(result.user_id)),
        );
      } catch (error) {
        if (!ignore) {
          setDirectInviteResults([]);
          setDirectInviteError('فعلاً نمی‌توانیم این کاربر را پیدا کنیم. نام کاربری را بررسی کن و دوباره امتحان کن.');
        }
        console.warn('Could not search users for direct group invite.', error);
      } finally {
        if (!ignore) setDirectInviteLoading(false);
      }
    }, 350);

    return () => {
      ignore = true;
      window.clearTimeout(timeoutId);
    };
  }, [currentUserId, directInviteSearch, memberUserIds, modal]);

  useEffect(() => {
    const objectUrl = receiptPreview?.objectUrl;

    return () => {
      if (objectUrl) {
        window.URL.revokeObjectURL(objectUrl);
      }
    };
  }, [receiptPreview?.objectUrl]);

  function openSettlementModal() {
    setSettlementModalTab('suggestion');
    setModal('settlement');
    void loadSettlementData();
  }

  function openExpenseModal() {
    setEnableReminderAfterExpense(Boolean(reminderSettings?.is_enabled));
    setSendExpenseReminderImmediately(false);
    setModal('expense');
    void loadReminderSettings().then((settings) => {
      if (settings) setEnableReminderAfterExpense(settings.is_enabled);
    });
  }

  function refreshActivitiesAfterMutation() {
    window.setTimeout(() => void loadGroupActivities(), 1200);
    window.setTimeout(() => void loadGroupActivities(), 3200);
  }

  async function refreshSmartSettlement(showNotification = true) {
    try {
      setSettlementSaving(true);
      const generatedPlan = await generateSettlementPlan(groupId);
      let resolvedPlan = generatedPlan;

      if (generatedPlan?.id && generatedPlan.status === 'DRAFT') {
        try {
          await activateSettlementPlan(generatedPlan.id);
          const latestPlan = await getSettlementPlan(groupId).catch(() => ({
            ...generatedPlan,
            status: 'ACTIVE',
          }));
          resolvedPlan = latestPlan;
          setSettlementPlan(latestPlan);
        } catch (activationError) {
          // The API allows only one active plan. A newly registered expense
          // makes that plan stale, so replace it with the freshly generated
          // plan before looking for reminder recipients.
          if (!isApiError(activationError) || activationError.status !== 409) {
            throw activationError;
          }

          const activePlan = await getSettlementPlan(groupId);
          if (activePlan.status !== 'ACTIVE' || activePlan.id === generatedPlan.id) {
            throw activationError;
          }

          await cancelSettlementPlan(activePlan.id);
          await activateSettlementPlan(generatedPlan.id);
          const latestPlan = await getSettlementPlan(groupId).catch(() => ({
            ...generatedPlan,
            status: 'ACTIVE',
          }));
          resolvedPlan = latestPlan;
          setSettlementPlan(latestPlan);
        }
      } else {
        setSettlementPlan(generatedPlan);
      }

      await loadSettlementData();
      refreshActivitiesAfterMutation();

      if (showNotification) {
        notify({
          type: 'success',
          title: 'پیشنهاد تسویه به‌روز شد',
          description: 'همدنگ دوباره حساب کرد چه کسی باید به چه کسی پرداخت کند.',
        });
      }
      return resolvedPlan;
    } catch (err) {
      console.error(err);
      if (showNotification) {
        notify({
          type: 'error',
          title: getSettlementErrorTitle('plan'),
          description: getSettlementErrorDescription(err),
        });
      }
      return null;
    } finally {
      setSettlementSaving(false);
    }
  }

  async function sendImmediateExpenseReminderEmails(
    participantIds: string[],
    payerId: string,
    sendInApp: boolean,
  ) {
    const recipientIds = new Set(participantIds.filter((userId) => userId && userId !== payerId));
    if (recipientIds.size === 0) return;

    // The settlement projection is updated asynchronously after expense creation.
    // Retry briefly so the immediate reminder targets the newly calculated open items.
    for (const delayMs of [1200, 2400, 3600]) {
      await new Promise<void>((resolve) => window.setTimeout(resolve, delayMs));
      const plan = await refreshSmartSettlement(false);
      const reminderItems = plan?.status === 'ACTIVE'
        ? (plan.items || []).filter(
          (item) => item.status === 'PENDING' && recipientIds.has(item.payer_user_id),
        )
        : [];

      if (reminderItems.length === 0) continue;

      const results = await Promise.allSettled(
        reminderItems.map((item) => sendPlanItemReminder(item.id, {
          send_email: true,
          send_in_app: sendInApp,
        })),
      );
      const sentCount = results.filter((result) => result.status === 'fulfilled').length;

      notify({
        type: sentCount > 0 ? 'success' : 'error',
        title: sentCount > 0 ? 'ایمیل فوری یادآوری ارسال شد' : 'ایمیل فوری ارسال نشد',
        description: sentCount > 0
          ? `برای ${toPersianNumber(sentCount)} نفر از بدهکاران این هزینه، ایمیل یادآوری در صف ارسال قرار گرفت.`
          : 'هزینه ثبت شد، اما ایمیل یادآوری ارسال نشد. بعداً می‌توانی از جزئیات بدهی دوباره یادآوری بفرستی.',
      });
      return;
    }

    notify({
      type: 'info',
      title: 'بدهی قابل یادآوری پیدا نشد',
      description: 'برای افراد انتخاب‌شده بدهی بازی وجود ندارد، پس یادآوری ارسال نشد.',
    });
  }

  async function handleSmartSettlementCalculation() {
    if (canManageGroup) {
      await refreshSmartSettlement();
      return;
    }

    await loadSettlementData();
    notify({
      type: 'success',
      title: 'پیشنهاد تسویه آماده شد',
      description: 'همدنگ ساده‌ترین مسیر پرداخت بین اعضای این گروه را محاسبه کرد.',
    });
  }

  useEffect(() => {
    if (
      !canManageGroup ||
      autoSettlementTried ||
      settlementLoading ||
      expensesLoading ||
      settlementPlan ||
      activeExpenses.length === 0 ||
      isArchived
    ) {
      return;
    }

    setAutoSettlementTried(true);
    void refreshSmartSettlement(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSettlementTried, settlementLoading, expensesLoading, settlementPlan, activeExpenses.length, isArchived]);

  function selectManualPlanItem(item: SettlementPlanItem) {
    setSelectedManualPlanItemId(item.id);
    setManualReceiverId(item.receiver_user_id);
    setManualPaymentMode('FULL');
    setManualAmount(String(item.amount_minor));
    setManualDescription('');
  }

  function openManualPaymentForItem(item: SettlementPlanItem) {
    selectManualPlanItem(item);
    setModal('settlement');
  }

  function resetManualPaymentForm() {
    const firstOtherMember = members.find((member) => getMemberUserId(member) !== currentUserId);

    setSelectedManualPlanItemId('');
    setManualPaymentMode('FULL');
    setManualAmount('');
    setManualDescription('');
    setManualReceiverId(firstOtherMember ? getMemberUserId(firstOtherMember) : '');
  }

  async function handleSave() {
    if (!title.trim()) {
      notify({
        type: 'error',
        title: 'عنوان گروه را وارد کن',
        description: 'برای اینکه گروه در لیستت مشخص باشد، یک عنوان بنویس.',
      });
      return;
    }

    try {
      setSaving(true);

      const updatedGroup = await updateGroup(groupId, {
        title: title.trim(),
        description: description.trim(),
        group_type: groupType,
      });

      setGroup(updatedGroup);
      onGroupUpdated(updatedGroup);
      setModal(null);

      notify({
        type: 'success',
        title: 'تغییرات ذخیره شد',
        description: 'اطلاعات گروه به‌روز شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'تغییرات ذخیره نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleArchive() {
    const confirmed = await confirm({
      title: 'این گروه آرشیو شود؟',
      description: 'گروه از لیست فعال‌ها خارج می‌شود، اما اطلاعاتش حذف نمی‌شود.',
      confirmText: 'آرشیو کن',
      cancelText: 'انصراف',
      tone: 'warning',
    });

    if (!confirmed) return;

    try {
      setArchiveLoading(true);
      await archiveGroup(groupId);
      const refreshedGroup = await getGroupDetail(groupId);

      setGroup(refreshedGroup);
      onGroupUpdated(refreshedGroup);

      notify({
        type: 'success',
        title: 'گروه آرشیو شد',
        description: 'این گروه دیگر در لیست گروه‌های فعال نمایش داده نمی‌شود.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'گروه آرشیو نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setArchiveLoading(false);
    }
  }

  async function handleRestore() {
    const confirmed = await confirm({
      title: 'این گروه دوباره فعال شود؟',
      description: 'بعد از فعال‌سازی، دوباره می‌توانی برای این گروه هزینه و تسویه ثبت کنی.',
      confirmText: 'فعال کن',
      cancelText: 'انصراف',
      tone: 'success',
    });

    if (!confirmed) return;

    try {
      setArchiveLoading(true);
      const restoredGroup = await restoreGroup(groupId);

      setGroup(restoredGroup);
      onGroupUpdated(restoredGroup);

      notify({
        type: 'success',
        title: 'گروه دوباره فعال شد',
        description: 'حالا می‌توانی دوباره از این گروه استفاده کنی.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'گروه فعال نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setArchiveLoading(false);
    }
  }

  async function handleLeave() {
    if (isOwner) {
      notify({
        type: 'info',
        title: 'مالک گروه نمی‌تواند خارج شود',
        description: 'اول مالکیت را به شخص دیگری بده یا گروه را آرشیو کن.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'از این گروه خارج می‌شوی؟',
      description: 'بعد از خروج، دیگر به هزینه‌ها و تسویه‌های این گروه دسترسی نداری.',
      confirmText: 'خارج شو',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      setLeaveLoading(true);
      await leaveGroup(groupId);

      notify({
        type: 'success',
        title: 'از گروه خارج شدی',
        description: 'این گروه دیگر در لیست گروه‌هایت نمایش داده نمی‌شود.',
      });

      onGroupRemoved(groupId);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'از گروه خارج نشدی',
        description: getBackendMessage(err),
      });
    } finally {
      setLeaveLoading(false);
    }
  }

  async function handleRemoveMember(member: BackendGroupMember) {
    const memberId = getMemberId(member);

    if (!memberId) {
      notify({
        type: 'error',
        title: 'عضو حذف نشد',
        description: 'اطلاعات این عضو کامل نیست. صفحه را تازه کن و دوباره امتحان کن.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'این عضو حذف شود؟',
      description: `${getMemberName(member)} از گروه حذف شود؟`,
      confirmText: 'حذف کن',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      await removeGroupMember(groupId, memberId);
      setMembers((prev) => prev.filter((item) => getMemberId(item) !== memberId));

      notify({
        type: 'success',
        title: 'عضو از گروه حذف شد',
        description: 'لیست اعضای گروه به‌روز شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'عضو حذف نشد',
        description: getBackendMessage(err),
      });
    }
  }

  function toggleExpenseParticipant(userId: string) {
    setExpenseParticipantIds((prev) =>
      prev.includes(userId) ? prev.filter((item) => item !== userId) : [...prev, userId],
    );
  }

  function resetExpenseForm() {
    setExpenseTitle('');
    setExpenseAmount('');
    setExpenseDescription('');
    setReceiptFile(null);
    setExpenseSplitMethod('EQUAL');
    setExpenseCustomShares({});
    setShowAdvancedExpense(false);
    setSendExpenseReminderImmediately(false);
  }

  async function handleCreateExpense() {
    if (isArchived) {
      notify({
        type: 'error',
        title: 'این گروه آرشیو شده است',
        description: 'برای ثبت هزینه جدید، اول گروه را دوباره فعال کن.',
      });
      return;
    }

    if (!expenseTitle.trim()) {
      notify({
        type: 'error',
        title: 'عنوان هزینه را وارد کن',
        description: 'مثلاً بنویس شام، تاکسی یا خرید سوپرمارکت.',
      });
      return;
    }

    if (!baseAmountMinor || baseAmountMinor <= 0) {
      notify({
        type: 'error',
        title: 'مبلغ را اصلاح کن',
        description: 'مبلغ هزینه را وارد کن تا سهم هر نفر محاسبه شود.',
      });
      return;
    }

    if (!expensePayerId) {
      notify({
        type: 'error',
        title: 'پرداخت‌کننده را انتخاب کن',
        description: 'مشخص کن چه کسی این هزینه را پرداخت کرده است.',
      });
      return;
    }

    if (expenseParticipantIds.length === 0) {
      notify({
        type: 'error',
        title: 'شرکت‌کننده‌ها را انتخاب کن',
        description: 'حداقل یک نفر را انتخاب کن تا سهم هزینه برای او حساب شود.',
      });
      return;
    }

    const customParticipants = expenseParticipantIds.map((userId) => ({
      user_id: userId,
      base_share_minor: parseAmountToMinor(expenseCustomShares[userId] || ''),
    }));

    if (expenseSplitMethod === 'CUSTOM_AMOUNT') {
      const hasInvalidShare = customParticipants.some((participant) => participant.base_share_minor <= 0);

      if (hasInvalidShare) {
        notify({
          type: 'error',
          title: 'سهم همه اعضا را وارد کن',
          description: 'برای هر عضو انتخاب‌شده، سهمش از این هزینه را وارد کن.',
        });
        return;
      }

      if (customSharesTotalMinor !== baseAmountMinor) {
        notify({
          type: 'error',
          title: 'جمع سهم‌ها با مبلغ هزینه یکی نیست',
          description: `جمع سهم‌ها باید ${formatMoney(baseAmountMinor)} باشد.`,
        });
        return;
      }
    }

    const reminderParticipantIds = [...expenseParticipantIds];
    const reminderPayerId = expensePayerId;
    const shouldSendImmediateReminder = canManageGroup && enableReminderAfterExpense && sendExpenseReminderImmediately;
    const shouldSendReminderInApp = reminderSettings?.send_in_app ?? true;

    try {
      setExpenseSaving(true);

      const createdExpense = await createGroupExpense(groupId, {
        title: expenseTitle.trim(),
        description: expenseDescription.trim(),
        payer_user_id: expensePayerId,
        base_amount_minor: baseAmountMinor,
        currency: 'IRR',
        split_method: expenseSplitMethod,
        participant_user_ids: expenseSplitMethod === 'EQUAL' ? expenseParticipantIds : undefined,
        participants: expenseSplitMethod === 'CUSTOM_AMOUNT' ? customParticipants : undefined,
      });

      let receiptUploadFailed = false;

      if (receiptFile) {
        try {
          const uploadedReceipt = await uploadReceipt({
            groupId,
            file: receiptFile,
            relatedExpenseId: createdExpense.id,
          });

          setExpenseReceiptsByExpenseId((current) => ({
            ...current,
            [createdExpense.id]: [
              {
                id: uploadedReceipt.id,
                expense_id: createdExpense.id,
                group_id: uploadedReceipt.group_id,
                original_filename: uploadedReceipt.original_filename,
                content_type: uploadedReceipt.content_type,
                size_bytes: uploadedReceipt.size_bytes,
                uploaded_by_user_id: currentUserId,
                created_at: uploadedReceipt.created_at,
                download_url: `/api/v1/media/files/${uploadedReceipt.id}/download/`,
              },
              ...(current[createdExpense.id] || []),
            ],
          }));
        } catch (receiptError) {
          receiptUploadFailed = true;
          console.warn('Expense was created but receipt upload failed.', receiptError);
        }
      }

      if (canManageGroup && reminderSettings) {
        try {
          const savedReminderSettings = await updateGroupReminderSettings(groupId, {
            is_enabled: enableReminderAfterExpense,
            first_reminder_after_hours: shouldSendImmediateReminder
              ? reminderSettings.repeat_interval_hours
              : reminderSettings.first_reminder_after_hours,
            repeat_interval_hours: reminderSettings.repeat_interval_hours,
            maximum_reminders: reminderSettings.maximum_reminders,
            send_in_app: reminderSettings.send_in_app,
            send_email: enableReminderAfterExpense ? true : reminderSettings.send_email,
          });
          setReminderSettings(savedReminderSettings);
        } catch (reminderError) {
          console.error(reminderError);
          notify({
            type: 'info',
            title: 'هزینه ثبت شد، اما یادآوری ذخیره نشد',
            description: getBackendMessage(reminderError),
          });
        }
      }

      resetExpenseForm();
      setModal(null);
      await Promise.all([loadExpenses(), loadSettlementData()]);
      refreshActivitiesAfterMutation();
      if (shouldSendImmediateReminder) {
        void sendImmediateExpenseReminderEmails(
          reminderParticipantIds,
          reminderPayerId,
          shouldSendReminderInApp,
        );
      } else {
        void refreshSmartSettlement(false);
      }

      notify({
        type: receiptUploadFailed ? 'info' : 'success',
        title: 'هزینه ثبت شد',
        description: receiptUploadFailed
          ? 'حساب گروه بروزرسانی شد، اما آپلود رسید انجام نشد. دوباره از فرم هزینه رسید را بارگذاری کن.'
          : 'حساب گروه بروزرسانی شد و رسید، اگر انتخاب شده باشد، کنار همین هزینه نمایش داده می‌شود.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'هزینه ثبت نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setExpenseSaving(false);
    }
  }

  function closeReceiptPreview() {
    setReceiptPreview(null);
  }

  async function handlePreviewExpenseReceipt(expense: BackendExpense) {
    const source = getResolvedExpenseReceiptSource(expense);
    if (!source) {
      notify({
        type: 'info',
        title: 'برای این هزینه رسیدی ثبت نشده است',
        description: 'اگر رسید داری، آن را هنگام ثبت هزینه یا ویرایش هزینه اضافه کن.',
      });
      return;
    }

    const busyKey = getResolvedExpenseReceiptBusyKey(expense);

    try {
      setOpeningReceiptId(busyKey);

      if (source.kind === 'media') {
        const downloaded = await downloadMediaFile(source.id);
        const objectUrl = window.URL.createObjectURL(downloaded.blob);

        setReceiptPreview({
          title: `رسید ${expense.title}`,
          sourceUrl: objectUrl,
          objectUrl,
          contentType: downloaded.contentType || source.contentType,
          fileName: downloaded.fileName || source.fileName,
          downloadFileId: source.id,
          downloadUrl: source.downloadUrl,
        });
        return;
      }

      setReceiptPreview({
        title: `رسید ${expense.title}`,
        sourceUrl: source.url,
        contentType: source.contentType || '',
        fileName: source.fileName || getFileNameFromUrl(source.url),
        downloadUrl: source.url,
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'رسید باز نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setOpeningReceiptId(null);
    }
  }

  async function downloadReceiptFile(fileId: string) {
    const downloaded = await downloadMediaFile(fileId);
    const objectUrl = window.URL.createObjectURL(downloaded.blob);
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = downloaded.fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 60_000);
  }

  function downloadReceiptUrl(url: string, fileName?: string) {
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = fileName || getFileNameFromUrl(url);
    anchor.target = '_blank';
    anchor.rel = 'noopener noreferrer';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  }

  async function handleDownloadExpenseReceipt(expense: BackendExpense) {
    const source = getResolvedExpenseReceiptSource(expense);
    if (!source) return;

    const busyKey = getResolvedExpenseReceiptBusyKey(expense);

    try {
      setOpeningReceiptId(busyKey);

      if (source.kind === 'media') {
        await downloadReceiptFile(source.id);
        return;
      }

      downloadReceiptUrl(source.url);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'رسید دانلود نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setOpeningReceiptId(null);
    }
  }

  async function handleDownloadReceiptPreview() {
    if (!receiptPreview) return;

    try {
      if (receiptPreview.downloadFileId) {
        setOpeningReceiptId(receiptPreview.downloadFileId);
        await downloadReceiptFile(receiptPreview.downloadFileId);
        return;
      }

      if (receiptPreview.downloadUrl) {
        downloadReceiptUrl(receiptPreview.downloadUrl, receiptPreview.fileName);
      }
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'رسید دانلود نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setOpeningReceiptId(null);
    }
  }

  async function handlePayDetailedDebt(debt: DebtItem) {
    if (!currentUserId || debt.debtor_user_id !== currentUserId) return;

    const receiverUserId = debt.creditor_user_id;
    const hasPendingPayment = settlements.some(
      (item) =>
        item.payer_user_id === currentUserId &&
        item.receiver_user_id === receiverUserId &&
        ['PENDING', 'PENDING_CONFIRMATION', 'REPORTED'].includes(item.status || 'PENDING_CONFIRMATION'),
    );

    if (hasPendingPayment) {
      notify({
        type: 'info',
        title: 'پرداخت قبلی هنوز در انتظار تأیید است',
        description: 'بعد از تأیید دریافت‌کننده، می‌توانی پرداخت جدیدی برای این بدهی ثبت کنی.',
      });
      return;
    }

    const expense = debt.source_expense_id ? expenseById.get(debt.source_expense_id) : undefined;
    const confirmed = await confirm({
      title: 'این پرداخت دستی ثبت شود؟',
      description: `${formatMoney(debt.amount_minor)} به ${getDebtPartyName(receiverUserId, members)} پرداخت شود؟`,
      confirmText: 'ثبت پرداخت دستی',
      cancelText: 'انصراف',
    });

    if (!confirmed) return;

    try {
      setSettlementSaving(true);
      await createGroupSettlement(groupId, {
        receiver_user_id: receiverUserId,
        amount_minor: debt.amount_minor,
        currency: 'IRR',
        description: expense?.title ? `پرداخت بدهی هزینه «${expense.title}»` : 'پرداخت یکی از بدهی‌های گروه',
      });
      await loadSettlementData();
      refreshActivitiesAfterMutation();

      notify({
        type: 'success',
        title: 'پرداخت دستی ثبت شد',
        description: 'وقتی دریافت‌کننده پول را تأیید کند، این مبلغ از بدهی تو کم می‌شود.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: getSettlementErrorTitle('create'),
        description: getSettlementErrorDescription(err),
      });
    } finally {
      setSettlementSaving(false);
    }
  }

  async function handleCreateManualSettlement(receiverUserId?: string, amountMinor?: number) {
    const hasExplicitPayment = Boolean(receiverUserId) && amountMinor !== undefined;
    const selectedItem = hasExplicitPayment ? null : selectedManualPlanItem;
    const isSelectedFullPayment = selectedItem && manualPaymentMode === 'FULL';
    const targetReceiverId = selectedItem?.receiver_user_id || receiverUserId || manualReceiverId;
    const targetAmountMinor = selectedItem
      ? manualPaymentMode === 'FULL'
        ? selectedItem.amount_minor
        : parseAmountToMinor(manualAmount)
      : amountMinor ?? parseAmountToMinor(manualAmount);
    const targetSuggestion = optimizedSettlements.find(
      (item) => item.receiver_user_id === targetReceiverId && item.payer_user_id === currentUserId,
    );

    if (isArchived) {
      notify({
        type: 'error',
        title: 'این گروه آرشیو شده است',
        description: 'برای ثبت پرداخت، اول این گروه را دوباره فعال کن.',
      });
      return;
    }

    if (!currentUserId) {
      notify({
        type: 'error',
        title: 'حساب کاربری مشخص نیست',
        description: 'یک بار از حساب خارج شو و دوباره وارد شو تا پرداخت به نام خودت ثبت شود.',
      });
      return;
    }

    if (!targetReceiverId) {
      notify({
        type: 'error',
        title: 'دریافت‌کننده را انتخاب کن',
        description: 'مشخص کن این مبلغ را به چه کسی پرداخت کرده‌ای.',
      });
      return;
    }

    if (!targetAmountMinor || targetAmountMinor <= 0) {
      notify({
        type: 'error',
        title: 'مبلغ را اصلاح کن',
        description: 'مبلغی را که پرداخت کرده‌ای وارد کن.',
      });
      return;
    }

    if (selectedItem && targetAmountMinor > selectedItem.amount_minor) {
      notify({
        type: 'error',
        title: 'مبلغ واردشده بیشتر از بدهی است',
        description: `حداکثر مبلغ این پرداخت ${formatMoney(selectedItem.amount_minor)} است.`,
      });
      return;
    }

    if (!selectedItem && targetSuggestion && targetAmountMinor > targetSuggestion.amount_minor) {
      notify({
        type: 'info',
        title: 'مبلغ از پیشنهاد تسویه بیشتر است',
        description: `برای این عضو، مبلغ پیشنهادی ${formatMoney(targetSuggestion.amount_minor)} است. مبلغ را اصلاح کن یا از دکمه پیشنهاد استفاده کن.`,
      });
      return;
    }

    try {
      setSettlementSaving(true);

      if (isSelectedFullPayment) {
        await reportPlanItemPaid(selectedItem.id);
      } else {
        await createGroupSettlement(groupId, {
          receiver_user_id: targetReceiverId,
          amount_minor: targetAmountMinor,
          currency: 'IRR',
          description:
            (hasExplicitPayment ? '' : manualDescription) ||
            (selectedItem
              ? `پرداخت بخشی از بدهی به ${getPlanPartyName(selectedItem, 'receiver', members)}`
              : targetSuggestion
                ? `پرداخت بدهی به ${targetSuggestion.receiverName}`
                : 'تسویه دستی'),
        });
      }

      setManualReceiverId('');
      setManualAmount('');
      setManualDescription('');

      resetManualPaymentForm();
      await loadSettlementData();
      refreshActivitiesAfterMutation();

      notify({
        type: 'success',
        title: isSelectedFullPayment ? 'پرداخت گزارش شد' : 'پرداخت دستی ثبت شد',
        description: isSelectedFullPayment
          ? 'در انتظار تأیید دریافت‌کننده است.'
          : 'بعد از تأیید دریافت‌کننده، مبلغ از بدهی باقی‌مانده کم می‌شود.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: getSettlementErrorTitle('create'),
        description: getSettlementErrorDescription(err),
      });
    } finally {
      setSettlementSaving(false);
    }
  }

  async function handlePlanItemAction(item: SettlementPlanItem, action: 'paid' | 'confirm' | 'reject') {
    try {
      setSettlementSaving(true);

      if (action === 'paid') await reportPlanItemPaid(item.id);
      if (action === 'confirm') await confirmPlanItem(item.id);
      if (action === 'reject') await rejectPlanItem(item.id);

      await loadSettlementData();
      refreshActivitiesAfterMutation();

      if (action === 'confirm') {
        void refreshSmartSettlement(false);
      }

      notify({
        type: 'success',
        title: 'وضعیت تسویه به‌روز شد',
        description: 'وضعیت پرداخت در این گروه به‌روز شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: getSettlementErrorTitle('item'),
        description: getSettlementErrorDescription(err),
      });
    } finally {
      setSettlementSaving(false);
    }
  }

  function isInsufficientWalletBalanceError(err: unknown) {
    const message = getBackendMessage(err).toLowerCase();
    const body = isApiError(err) && typeof err.body === 'object' && err.body ? err.body as Record<string, unknown> : null;
    const errorObject = body && typeof body.error === 'object' && body.error ? body.error as Record<string, unknown> : null;
    const code = String(errorObject?.code || '').toUpperCase();

    return code.includes('INSUFFICIENT') || message.includes('insufficient') || message.includes('موجودی');
  }

  async function handleWalletSettlementPayment(item: SettlementPlanItem) {
    if (!canReportPlanItem(item, settlementPlan)) return;

    const confirmed = await confirm({
      title: 'پرداخت از کیف پول انجام شود؟',
      description: `${formatMoney(item.amount_minor)} از کیف پول شما به ${getPlanPartyName(item, 'receiver', members)} پرداخت می‌شود.`,
      confirmText: walletAvailableMinor >= item.amount_minor ? 'پرداخت از کیف پول' : 'ادامه و شارژ کیف پول',
      cancelText: 'انصراف',
    });

    if (!confirmed) return;

    if (walletAvailableMinor < item.amount_minor) {
      setWalletTopUpItem(item);
      return;
    }

    try {
      setWalletPaymentItemId(item.id);
      await paySettlementItemWithWallet(item.id, createIdempotencyKey('wallet-settlement'));
      await loadSettlementData();
      refreshActivitiesAfterMutation();
      void refreshSmartSettlement(false);

      notify({
        type: 'success',
        title: 'پرداخت از کیف پول انجام شد',
        description: 'مبلغ از کیف پول تو کم شد و به کیف پول دریافت‌کننده اضافه شد.',
      });
    } catch (err) {
      console.error(err);

      if (isInsufficientWalletBalanceError(err)) {
        setWalletTopUpItem(item);
        return;
      }

      notify({
        type: 'error',
        title: 'پرداخت از کیف پول انجام نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setWalletPaymentItemId(null);
    }
  }

  function findWalletPlanItemForDebt(debt: DebtItem, plan: SettlementPlan | null = settlementPlan) {
    if (!currentUserId || debt.debtor_user_id !== currentUserId) return null;

    const payableItems = (plan?.items || []).filter(
      (item) =>
        item.payer_user_id === currentUserId &&
        item.receiver_user_id === debt.creditor_user_id &&
        canReportPlanItem(item, plan),
    );

    return payableItems.find((item) => item.amount_minor === debt.amount_minor) || null;
  }

  async function handleWalletDetailedDebtPayment(debt: DebtItem) {
    if (!currentUserId || debt.debtor_user_id !== currentUserId) return;

    let payableItem = findWalletPlanItemForDebt(debt);

    if (!payableItem) {
      const refreshedPlan = await refreshSmartSettlement(false);
      payableItem = findWalletPlanItemForDebt(debt, refreshedPlan);
    }

    if (!payableItem) {
      notify({
        type: 'info',
        title: 'این بدهی از اینجا با کیف پول پرداخت نمی‌شود',
        description: 'برای پرداخت این مورد با کیف پول، از تب «پیشنهاد تسویه» استفاده کن. اگر نمی‌خواهی از کیف پول پرداخت کنی، ثبت پرداخت دستی را بزن.',
      });
      return;
    }

    await handleWalletSettlementPayment(payableItem);
  }

  async function handleTopUpAndPaySettlementItem() {
    if (!walletTopUpItem) return;

    const shortageMinor = Math.max(walletTopUpItem.amount_minor - walletAvailableMinor, walletTopUpItem.amount_minor);
    const walletPayIdempotencyKey = createIdempotencyKey('wallet-settlement-after-top-up');

    try {
      setWalletTopUpLoading(true);
      const intent = await createPaymentIntent({
        amountMinor: shortageMinor,
        provider: walletTopUpProvider,
        idempotencyKey: createIdempotencyKey('settlement-top-up'),
      });

      savePendingWalletPayment({
        paymentIntentId: intent.payment_intent_id,
        provider: intent.provider,
        amountMinor: shortageMinor,
        settlementPlanItemId: walletTopUpItem.id,
        groupId,
        walletPayIdempotencyKey,
        createdAt: new Date().toISOString(),
      });

      if (walletTopUpProvider === 'FAKE') {
        const verifyResult = await verifyPaymentIntent({
          provider: 'FAKE',
          paymentIntentId: intent.payment_intent_id,
          providerReference: intent.provider_reference || intent.payment_intent_id,
        });

        if (String(verifyResult.status).toUpperCase() !== 'SUCCEEDED') {
          throw new Error(verifyResult.failure_reason || 'شارژ آزمایشی کیف پول تأیید نشد.');
        }

        await paySettlementItemWithWallet(walletTopUpItem.id, walletPayIdempotencyKey);
        setWalletTopUpItem(null);
        await loadSettlementData();
        await loadWalletBalance();
        refreshActivitiesAfterMutation();
        void refreshSmartSettlement(false);

        notify({
          type: 'success',
          title: 'کیف پول شارژ شد و پرداخت انجام شد',
          description: 'موجودی کیف پولت افزایش پیدا کرد و بدهی انتخاب‌شده پرداخت شد.',
        });
        return;
      }

      window.location.href = intent.payment_url;
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'شارژ یا پرداخت انجام نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setWalletTopUpLoading(false);
    }
  }

  async function handleSettlementAction(settlement: SettlementItem, action: 'confirm' | 'reject' | 'cancel') {
    try {
      setSettlementSaving(true);

      if (action === 'confirm') await confirmSettlement(settlement.id);
      if (action === 'reject') await rejectSettlement(settlement.id);
      if (action === 'cancel') await cancelSettlement(settlement.id);

      await loadSettlementData();
      refreshActivitiesAfterMutation();

      if (action === 'confirm' || action === 'cancel') {
        void refreshSmartSettlement(false);
      }

      notify({
        type: 'success',
        title: 'وضعیت پرداخت به‌روز شد',
        description: 'لیست پرداخت‌ها به‌روز شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: getSettlementErrorTitle('review'),
        description: getSettlementErrorDescription(err),
      });
    } finally {
      setSettlementSaving(false);
    }
  }

  async function handleCreateInvite() {
    try {
      setInviteLoading(true);

      const createdInvite = await createGroupInvite(groupId, {
        expires_in_hours: 72,
        max_uses: 10,
      });

      setInvite(createdInvite);
      refreshActivitiesAfterMutation();

      notify({
        type: 'success',
        title: 'لینک دعوت ساخته شد',
        description: 'حالا می‌توانی لینک را کپی کنی و برای دوستانت بفرستی.',
      });
    } catch (err) {
      console.error(err);

      const permissionDenied = isApiError(err) && err.status === 403;

      notify({
        type: 'error',
        title: permissionDenied ? 'اجازه ساخت لینک دعوت را نداری' : 'لینک دعوت ساخته نشد',
        description: permissionDenied ? 'فقط مدیر یا مالک می‌تواند لینک بسازد.' : getBackendMessage(err),
      });
    } finally {
      setInviteLoading(false);
    }
  }

  async function handleCreateDirectInvite(user: UserSearchResult) {
    if (!canManageGroup) {
      notify({
        type: 'error',
        title: 'اجازه دعوت عضو جدید را نداری',
        description: 'برای دعوت عضو جدید، باید مالک یا مدیر این گروه باشی.',
      });
      return;
    }

    if (memberUserIds.has(user.user_id)) {
      notify({
        type: 'info',
        title: 'این کاربر از قبل عضو گروه است',
        description: 'لازم نیست برای او دعوت جدید بفرستی.',
      });
      return;
    }

    try {
      setSendingDirectInviteId(user.user_id);
      await createDirectGroupInvite(groupId, {
        recipient_user_id: user.user_id,
        expires_in_hours: 168,
      });

      setDirectInviteResults((current) => current.filter((item) => item.user_id !== user.user_id));
      setDirectInviteSearch('');
      refreshActivitiesAfterMutation();

      notify({
        type: 'success',
        title: 'دعوت ارسال شد',
        description: `دعوت برای ${user.art_name || 'کاربر انتخاب‌شده'} داخل اعلان‌های خودش نمایش داده می‌شود. بعد از قبول دعوت، به اعضای گروه اضافه می‌شود.`,
      });
    } catch (err) {
      console.error(err);

      const alreadyPending =
        isApiError(err) &&
        String((err.body as { error?: { code?: string } } | undefined)?.error?.code || '') ===
          'DIRECT_INVITE_ALREADY_PENDING';

      notify({
        type: alreadyPending ? 'info' : 'error',
        title: alreadyPending ? 'دعوت قبلاً ارسال شده است' : 'دعوت ارسال نشد',
        description: alreadyPending
          ? 'برای این کاربر هنوز یک دعوت فعال وجود دارد. باید همان دعوت را قبول یا رد کند.'
          : getBackendMessage(err),
      });
    } finally {
      setSendingDirectInviteId(null);
    }
  }

  async function handleCopyInvite() {
    if (!inviteUrl) return;

    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);

      notify({
        type: 'success',
        title: 'لینک کپی شد',
        description: 'لینک دعوت لینک کپی شد.',
      });
    } catch {
      notify({
        type: 'error',
        title: 'لینک کپی نشد',
        description: 'مرورگر اجازه کپی خودکار نداد؛ لینک را دستی انتخاب و کپی کن.',
      });
    }
  }

  async function handleRevokeInvite() {
    if (!invite) return;

    const inviteId = getInviteId(invite);

    if (!inviteId) {
      notify({
        type: 'error',
        title: 'لغو لینک انجام نشد',
        description: 'اطلاعات این لینک کامل نیست. صفحه را تازه کن و دوباره امتحان کن.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'این لینک دعوت لغو شود؟',
      description: 'بعد از لغو، کسی با این لینک نمی‌تواند وارد گروه شود.',
      confirmText: 'لغو کن',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      await revokeGroupInvite(groupId, inviteId);
      setInvite(null);

      notify({
        type: 'success',
        title: 'لینک دعوت لغو شد',
        description: 'این لینک دیگر برای عضویت در گروه قابل استفاده نیست.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'لینک دعوت لغو نشد',
        description: getBackendMessage(err),
      });
    }
  }

  if (loading && !group) {
    return (
      <main className="app-page min-h-[70vh]" dir="rtl">
        <div className="dashboard-section-card mx-auto flex max-w-[1100px] items-center justify-center rounded-[24px] border border-emerald-100/80 bg-white/95 p-10 text-center shadow-[0_18px_44px_rgba(15,23,42,0.07)] backdrop-blur dark:border-emerald-500/20 dark:bg-slate-950/90">
          <InlineLoader label="در حال دریافت گروه..." />
        </div>
      </main>
    );
  }

  return (
    <main className="app-page relative overflow-x-hidden text-right" dir="rtl">
      <div className="app-container app-container-dashboard">
        <section className="overflow-visible rounded-[28px] border border-slate-200/90 bg-white/95 p-3 shadow-[0_22px_60px_rgba(15,23,42,0.08)] backdrop-blur sm:p-5 dark:border-emerald-500/15 dark:bg-slate-950/90 dark:shadow-[0_26px_70px_rgba(0,0,0,0.3)]">
          <header className="flex items-center justify-between gap-3 px-1 py-1 sm:px-2">
            <button
              type="button"
              onClick={() => setModal('settings')}
              className="group flex min-w-0 flex-1 items-center gap-3 rounded-[18px] p-1 text-right transition hover:bg-emerald-50/70 dark:hover:bg-emerald-500/10"
            >
              <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50 text-xl font-black text-emerald-700 shadow-[inset_0_0_0_6px_rgba(255,255,255,0.5)] dark:border-emerald-500/25 dark:from-emerald-500/15 dark:to-teal-500/10 dark:text-emerald-200 dark:shadow-none">
                {(group?.title || 'گ').slice(0, 1)}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-lg font-black text-text dark:text-slate-100 sm:text-xl">
                  {group?.title || 'جزئیات گروه'}
                </span>
                <span className="mt-1 block text-xs font-bold text-muted dark:text-slate-400">
                  {membersLoading ? 'در حال دریافت اعضا...' : `${toPersianNumber(members.length)} عضو`}
                </span>
              </span>
              <span className={cn(
                'hidden rounded-full px-3 py-1.5 text-xs font-black sm:inline-flex',
                accountTone === 'rose'
                  ? 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-200'
                  : accountTone === 'emerald'
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200'
                    : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-200',
              )}>
                {accountTitle}
              </span>
            </button>

            <Button tone="secondary" onClick={onBack} className="min-h-11 shrink-0 px-3 sm:px-4">
              بازگشت
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </header>

          <section className="mt-5 rounded-[24px] border border-slate-200/90 bg-slate-50/40 p-3 sm:p-5 dark:border-slate-700/80 dark:bg-slate-900/35">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-[1.15fr_0.85fr_0.85fr]">
              <div className="col-span-2 flex min-h-[124px] items-center justify-between gap-4 rounded-[22px] bg-gradient-to-br from-emerald-600 via-emerald-600 to-teal-700 p-4 text-white shadow-[0_18px_38px_rgba(5,150,105,0.2)] sm:p-5 lg:col-span-1 lg:min-h-[132px]">
                <div className="min-w-0 text-right">
                  <p className="text-xs font-extrabold text-white/75">در مجموع</p>
                  <div className="mt-2">
                    <MoneyWithWords
                      amount={Math.abs(myNetMinor)}
                      valueClassName="text-3xl font-black tracking-[-0.04em] sm:text-4xl"
                      textClassName="mt-1 text-xs font-semibold text-white/70"
                      showText={true}
                    />
                  </div>
                  <p className="mt-2 text-xs font-black text-white/85">{accountTitle}</p>
                </div>
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-white/14 text-white ring-1 ring-white/20">
                  <Banknote className="h-6 w-6" />
                </span>
              </div>

              <div className="flex min-h-[112px] items-center justify-between gap-2 rounded-[22px] border border-emerald-200 bg-emerald-50/70 p-3 text-right dark:border-emerald-500/25 dark:bg-emerald-500/10 sm:p-4 lg:min-h-[132px]">
                <div>
                  <p className="text-xs font-black text-emerald-700 dark:text-emerald-200">باید دریافت کنید</p>
                  <MoneyWithWords amount={visibleMyCreditMinor} valueClassName="mt-2 break-words text-base font-black text-emerald-700 dark:text-emerald-200 sm:text-xl" textClassName="mt-1 hidden text-[10px] font-semibold text-emerald-700/65 dark:text-emerald-200/65 sm:block" showText={true} />
                </div>
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-200 sm:h-11 sm:w-11">
                  <ArrowDown className="h-5 w-5" />
                </span>
              </div>

              <div className="flex min-h-[112px] items-center justify-between gap-2 rounded-[22px] border border-rose-200 bg-rose-50/60 p-3 text-right dark:border-rose-500/25 dark:bg-rose-500/10 sm:p-4 lg:min-h-[132px]">
                <div>
                  <p className="text-xs font-black text-rose-600 dark:text-rose-200">باید پرداخت کنید</p>
                  <MoneyWithWords amount={visibleMyDebtMinor} valueClassName="mt-2 break-words text-base font-black text-rose-600 dark:text-rose-200 sm:text-xl" textClassName="mt-1 hidden text-[10px] font-semibold text-rose-600/65 dark:text-rose-200/65 sm:block" showText={true} />
                </div>
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-rose-100 text-rose-600 dark:bg-rose-500/15 dark:text-rose-200 sm:h-11 sm:w-11">
                  <ArrowUp className="h-5 w-5" />
                </span>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2">
              <Button onClick={openExpenseModal} disabled={isArchived} className="h-12 w-full text-sm sm:text-base">
                <Plus className="h-5 w-5" />
                ثبت هزینه
              </Button>
              <Button tone="secondary" onClick={openSettlementModal} className="h-12 w-full text-sm sm:text-base">
                <HandCoins className="h-5 w-5" />
                تسویه حساب
              </Button>
            </div>
          </section>

          <nav className="mt-4 flex w-full items-center overflow-x-auto border-b border-slate-200 px-1 dark:border-slate-700" aria-label="بخش‌های گروه">
            {([
              { id: 'expenses', label: 'هزینه‌ها', icon: WalletCards },
              { id: 'activities', label: 'فعالیت‌ها', icon: History },
            ] as Array<{ id: GroupDetailView; label: string; icon: typeof WalletCards }>).map((tab) => {
              const TabIcon = tab.icon;
              const active = activeView === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => {
                    setActiveView(tab.id);
                    if (tab.id === 'activities') void loadGroupActivities();
                  }}
                  className={cn(
                    'relative flex min-w-[116px] flex-1 items-center justify-center gap-2 px-4 py-4 text-sm font-black transition',
                    active
                      ? 'text-emerald-700 dark:text-emerald-200'
                      : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200',
                  )}
                  aria-current={active ? 'page' : undefined}
                >
                  <TabIcon className="h-[18px] w-[18px]" />
                  {tab.label}
                  {active ? <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-emerald-500" /> : null}
                </button>
              );
            })}
          </nav>

          <div dir="ltr" className="mt-4 grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
            <aside dir="rtl" className="order-2 rounded-[22px] border border-slate-200 bg-white p-4 text-right dark:border-slate-700 dark:bg-slate-900/65 xl:order-1">
              <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-emerald-600 dark:text-emerald-300" />
                  <h2 className="text-sm font-black text-text dark:text-slate-100">تسویه هوشمند</h2>
                </div>
                <button
                  type="button"
                  onClick={() => void refreshSmartSettlement()}
                  disabled={settlementSaving || isArchived}
                  className="flex h-9 w-9 items-center justify-center rounded-full text-slate-500 transition hover:bg-emerald-50 hover:text-emerald-700 disabled:opacity-50 dark:text-slate-400 dark:hover:bg-emerald-500/10 dark:hover:text-emerald-200"
                  aria-label="محاسبه دوباره تسویه"
                >
                  {settlementSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                </button>
              </div>

              <div className="flex min-h-[238px] flex-col items-center justify-center py-5 text-center">
                <span className={cn(
                  'flex h-16 w-16 items-center justify-center rounded-full',
                  myDebtItems.length || myCreditItems.length || fallbackPaymentSuggestions.length || fallbackReceiptSuggestions.length
                    ? 'bg-orange-50 text-orange-600 dark:bg-orange-500/10 dark:text-orange-200'
                    : 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200',
                )}>
                  {myDebtItems.length || myCreditItems.length || fallbackPaymentSuggestions.length || fallbackReceiptSuggestions.length ? <Scale className="h-7 w-7" /> : <Check className="h-7 w-7" />}
                </span>

                {settlementLoading ? (
                  <div className="mt-4 flex items-center gap-2 text-sm font-bold text-muted dark:text-slate-400">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    در حال محاسبه...
                  </div>
                ) : myDebtItems.length === 0 && myCreditItems.length === 0 && fallbackPaymentSuggestions.length === 0 && fallbackReceiptSuggestions.length === 0 ? (
                  <>
                    <p className="mt-4 text-sm font-black text-text dark:text-slate-100">فعلاً نیازی به تسویه ندارید.</p>
                    <p className="mt-2 text-xs font-semibold leading-6 text-muted dark:text-slate-400">با ثبت هزینه جدید، این بخش خودکار به‌روز می‌شود.</p>
                  </>
                ) : (
                  <>
                    <p className="mt-4 text-sm font-black text-text dark:text-slate-100">{toPersianNumber(myDebtItems.length + myCreditItems.length + fallbackPaymentSuggestions.length + fallbackReceiptSuggestions.length)} مورد تسویه باز دارید</p>
                    <p className="mt-2 text-xs font-semibold leading-6 text-muted dark:text-slate-400">پرداخت‌ها و دریافت‌های باقی‌مانده را بررسی کنید.</p>
                  </>
                )}
              </div>

              <Button tone="secondary" onClick={openSettlementModal} className="w-full text-xs">
                مشاهده جزئیات تسویه
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </aside>

            <section dir="rtl" className="order-1 min-w-0 rounded-[22px] border border-slate-200 bg-white p-3 text-right dark:border-slate-700 dark:bg-slate-900/65 sm:p-4 xl:order-2">
              {activeView === 'expenses' ? (
                <>
                  <div className="mb-2 flex items-center justify-between gap-3 px-1 pb-2">
                    <div>
                      <h2 className="text-base font-black text-text dark:text-slate-100">هزینه‌های اخیر</h2>
                      <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">{toPersianNumber(activeExpenses.length)} هزینه ثبت شده</p>
                    </div>
                    <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-black text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200">
                      {formatMoney(totalExpenseMinor)}
                    </span>
                  </div>

                  {expensesLoading ? (
                    <div className="flex min-h-[280px] items-center justify-center gap-2 text-sm font-bold text-muted dark:text-slate-400">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      در حال دریافت هزینه‌ها...
                    </div>
                  ) : recentExpenses.length === 0 ? (
                    <EmptyState title="هنوز هزینه‌ای ثبت نشده" description="اولین هزینه گروه را ثبت کنید." icon={<ReceiptText className="h-6 w-6" />} />
                  ) : (
                    <div className="divide-y divide-slate-100 dark:divide-slate-800">
                      {recentExpenses.map((expense) => (
                        <div key={expense.id} className="grid min-w-0 gap-3 px-1 py-3.5 md:grid-cols-[minmax(160px,1.3fr)_minmax(100px,0.75fr)_minmax(100px,0.75fr)_minmax(110px,0.7fr)] md:items-center">
                          <div className="flex min-w-0 items-center gap-3 overflow-hidden">
                            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-sky-50 text-sky-600 dark:bg-sky-500/10 dark:text-sky-200">
                              <ReceiptText className="h-5 w-5" />
                            </span>
                            <div className="min-w-0 flex-1 overflow-hidden">
                              <p title={expense.title} className="block max-w-full truncate text-sm font-black text-text dark:text-slate-100">{expense.title}</p>
                              {expense.description ? <p title={expense.description} className="mt-1 block max-w-full truncate text-[11px] font-semibold text-muted dark:text-slate-400">{expense.description}</p> : null}
                              {canCurrentUserViewExpenseReceipt(expense) ? (
                                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                                  <button
                                    type="button"
                                    onClick={() => void handlePreviewExpenseReceipt(expense)}
                                    disabled={openingReceiptId === getResolvedExpenseReceiptBusyKey(expense)}
                                    className="inline-flex h-8 items-center gap-1.5 rounded-full border border-sky-200 bg-sky-50 px-2.5 text-[10px] font-black text-sky-700 transition hover:bg-sky-100 disabled:opacity-50 dark:border-sky-500/20 dark:bg-sky-500/10 dark:text-sky-200"
                                  >
                                    {openingReceiptId === getResolvedExpenseReceiptBusyKey(expense) ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Eye className="h-3.5 w-3.5" />}
                                    مشاهده فاکتور
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => void handleDownloadExpenseReceipt(expense)}
                                    disabled={openingReceiptId === getResolvedExpenseReceiptBusyKey(expense)}
                                    className="inline-flex h-8 items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 text-[10px] font-black text-slate-600 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                                  >
                                    <Download className="h-3.5 w-3.5" />
                                    دانلود
                                  </button>
                                </div>
                              ) : null}
                            </div>
                          </div>

                          <div className="flex min-w-0 items-center gap-2 overflow-hidden text-xs font-semibold text-muted dark:text-slate-400">
                            <CalendarDays className="h-4 w-4 shrink-0" />
                            <span title={toPersianDate(expense.expense_date || expense.created_at)} className="block min-w-0 flex-1 truncate">{toPersianDate(expense.expense_date || expense.created_at)}</span>
                          </div>

                          <div className="min-w-0 overflow-hidden text-right">
                            <p className="truncate text-[10px] font-semibold text-muted dark:text-slate-400">پرداخت‌کننده</p>
                            <p title={getUserDisplayFromId(expense.payer_user_id, members)} className="mt-1 block max-w-full truncate text-xs font-black text-slate-700 dark:text-slate-200">{getUserDisplayFromId(expense.payer_user_id, members)}</p>
                          </div>

                          <div title={formatMoney(getExpenseTotal(expense))} className="min-w-0 overflow-hidden text-left">
                            <MoneyWithWords amount={getExpenseTotal(expense)} className="min-w-0 max-w-full overflow-hidden" valueClassName="block max-w-full truncate text-sm font-black text-emerald-700 dark:text-emerald-200" showText={false} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {recentExpenses.length > 0 ? (
                    <div className="mt-3 flex justify-center border-t border-slate-100 pt-3 dark:border-slate-800">
                      <Button tone="secondary" onClick={() => setActiveView('activities')} className="min-h-10 px-4 text-xs">مشاهده همه فعالیت‌ها</Button>
                    </div>
                  ) : null}
                </>
              ) : null}

              {activeView === 'activities' ? (
                <>
                  <div className="mb-3 flex items-center justify-between gap-3 px-1 pb-2">
                    <div>
                      <h2 className="text-base font-black text-text dark:text-slate-100">فعالیت‌های گروه</h2>
                      <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">فقط رویدادهای همین گروه</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => void loadGroupActivities()}
                      disabled={activitiesLoading}
                      className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700 disabled:opacity-50 dark:border-slate-700 dark:text-slate-400 dark:hover:border-emerald-500/25 dark:hover:bg-emerald-500/10 dark:hover:text-emerald-200"
                      aria-label="بروزرسانی فعالیت‌ها"
                    >
                      <RefreshCw className={cn('h-4 w-4', activitiesLoading && 'animate-spin')} />
                    </button>
                  </div>

                  {activitiesError ? (
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-[16px] border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs font-bold text-amber-700 dark:border-amber-500/25 dark:bg-amber-500/10 dark:text-amber-200">
                      <span>فعلاً فعالیت‌ها نمایش داده نمی‌شوند. چند لحظه بعد دوباره امتحان کن.</span>
                      <button type="button" onClick={() => void loadGroupActivities()} className="rounded-full px-3 py-1.5 font-black hover:bg-amber-100 dark:hover:bg-amber-500/10">تلاش دوباره</button>
                    </div>
                  ) : null}

                  {activitiesLoading ? (
                    <div className="flex min-h-[280px] items-center justify-center gap-2 text-sm font-bold text-muted dark:text-slate-400">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      در حال دریافت فعالیت‌ها...
                    </div>
                  ) : activities.length === 0 ? (
                    <EmptyState title="هنوز فعالیتی ثبت نشده" description="کارهای انجام‌شده در این گروه اینجا نمایش داده می‌شوند." icon={<History className="h-6 w-6" />} />
                  ) : (
                    <div className="space-y-2">
                      {activities.map((activity) => {
                        const meta = getActivityMeta(activity.type);
                        const ActivityIcon = meta.icon;
                        const details = getActivityDetails(activity, members);

                        return (
                          <article key={activity.id} className="rounded-[18px] border border-slate-100 bg-slate-50/55 p-3.5 text-right dark:border-slate-800 dark:bg-slate-900/80 sm:p-4">
                            <div className="flex min-w-0 items-start gap-3">
                              <span className={cn('flex h-11 w-11 shrink-0 items-center justify-center rounded-full', meta.tone)}>
                                <ActivityIcon className="h-5 w-5" />
                              </span>

                              <div className="min-w-0 flex-1">
                                <p className="text-sm font-black leading-6 text-text dark:text-slate-100">
                                  <span>{getActivityActorName(activity, members)}</span>{' '}
                                  <span className="font-bold text-slate-600 dark:text-slate-300">{meta.verb}</span>
                                </p>
                                <p className="mt-1 flex items-center gap-1.5 text-[11px] font-semibold text-muted dark:text-slate-400">
                                  <CalendarDays className="h-3.5 w-3.5 shrink-0" />
                                  {toPersianDateTime(activity.occurred_at)}
                                </p>

                                {details.length > 0 ? (
                                  <div className="mt-3 flex flex-wrap gap-2">
                                    {details.map((detail) => (
                                      <span key={`${activity.id}-${detail.label}`} className="max-w-full rounded-full border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-bold text-slate-600 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300">
                                        {detail.label}: <span className="font-black text-slate-800 dark:text-slate-100">{detail.value}</span>
                                      </span>
                                    ))}
                                  </div>
                                ) : null}
                              </div>
                            </div>
                          </article>
                        );
                      })}

                      {activitiesNextCursor ? (
                        <div className="flex justify-center border-t border-slate-100 pt-3 dark:border-slate-800">
                          <Button
                            tone="secondary"
                            onClick={() => void loadGroupActivities(activitiesNextCursor, true)}
                            disabled={activitiesLoadingMore}
                            className="min-h-10 px-4 text-xs"
                          >
                            {activitiesLoadingMore ? <Loader2 className="h-4 w-4 animate-spin" /> : <History className="h-4 w-4" />}
                            نمایش فعالیت‌های قدیمی‌تر
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  )}
                </>
              ) : null}

              {activeView === 'settlement' ? (
                <>
                  <div className="mb-3 flex items-center justify-between gap-3 px-1">
                    <div>
                      <h2 className="text-base font-black text-text dark:text-slate-100">وضعیت تسویه</h2>
                      <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">پرداخت‌ها و دریافت‌های باز شما</p>
                    </div>
                    <Button tone="secondary" onClick={openSettlementModal} className="min-h-10 px-3 text-xs">همه جزئیات</Button>
                  </div>

                  {settlementDataError ? (
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-[16px] border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs font-bold text-amber-700 dark:border-amber-500/25 dark:bg-amber-500/10 dark:text-amber-200">
                      <span>{settlementDataError}</span>
                      <button type="button" onClick={() => void loadSettlementData()} className="rounded-full px-3 py-1.5 font-black hover:bg-amber-100 dark:hover:bg-amber-500/10">تلاش دوباره</button>
                    </div>
                  ) : null}

                  {settlementLoading ? (
                    <div className="flex min-h-[280px] items-center justify-center gap-2 text-sm font-bold text-muted dark:text-slate-400"><Loader2 className="h-4 w-4 animate-spin" />در حال دریافت تسویه...</div>
                  ) : myDebtItems.length === 0 && myCreditItems.length === 0 && fallbackPaymentSuggestions.length === 0 && fallbackReceiptSuggestions.length === 0 && myRegisteredSettlements.length === 0 ? (
                    <EmptyState title="همه‌چیز تسویه است" description="در حال حاضر پرداخت یا دریافتی ندارید." icon={<Check className="h-6 w-6" />} />
                  ) : (
                    <div className="space-y-2">
                      {myDebtItems.map((item) => (
                        <div key={item.id} className="flex flex-col gap-3 rounded-[18px] border border-rose-100 bg-rose-50/45 p-3 sm:flex-row sm:items-center sm:justify-between dark:border-rose-500/20 dark:bg-rose-500/10">
                          <div><p className="text-sm font-black text-text dark:text-slate-100">باید به {getPlanPartyName(item, 'receiver', members)} پرداخت کنید</p><p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">{getSettlementStatusLabel(item.status)}</p></div>
                          <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-black text-rose-600 dark:text-rose-200">{formatMoney(item.amount_minor)}</span>{canReportPlanItem(item, settlementPlan) ? <><Button onClick={() => void handleWalletSettlementPayment(item)} disabled={walletPaymentItemId === item.id} className="min-h-9 px-3 text-xs">پرداخت با کیف پول</Button><Button tone="secondary" onClick={() => openManualPaymentForItem(item)} className="min-h-9 px-3 text-xs">دستی</Button></> : null}</div>
                        </div>
                      ))}
                      {fallbackPaymentSuggestions.map((suggestion) => (
                        <div key={suggestion.id} className="flex flex-col gap-3 rounded-[18px] border border-rose-100 bg-rose-50/45 p-3 sm:flex-row sm:items-center sm:justify-between dark:border-rose-500/20 dark:bg-rose-500/10">
                          <div>
                            <p className="text-sm font-black text-text dark:text-slate-100">باید به {suggestion.receiverName} پرداخت کنید</p>
                            <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">آماده ثبت پرداخت</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-black text-rose-600 dark:text-rose-200">{formatMoney(suggestion.amount_minor)}</span>
                            <Button
                              onClick={() => void handleCreateManualSettlement(suggestion.receiver_user_id, suggestion.amount_minor)}
                              disabled={settlementSaving}
                              className="min-h-9 px-3 text-xs"
                            >
                              ثبت پرداخت
                            </Button>
                          </div>
                        </div>
                      ))}
                      {myCreditItems.map((item) => (
                        <div key={item.id} className="flex flex-col gap-3 rounded-[18px] border border-emerald-100 bg-emerald-50/45 p-3 sm:flex-row sm:items-center sm:justify-between dark:border-emerald-500/20 dark:bg-emerald-500/10">
                          <div><p className="text-sm font-black text-text dark:text-slate-100">باید از {getPlanPartyName(item, 'payer', members)} پول بگیرید</p><p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">{getSettlementStatusLabel(item.status)}</p></div>
                          <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-black text-emerald-700 dark:text-emerald-200">{formatMoney(item.amount_minor)}</span>{canReviewPlanItem(item) ? <><Button onClick={() => void handlePlanItemAction(item, 'confirm')} className="min-h-9 px-3 text-xs">پول را گرفتم</Button><Button tone="danger" onClick={() => void handlePlanItemAction(item, 'reject')} className="min-h-9 px-3 text-xs">نگرفتم</Button></> : null}</div>
                        </div>
                      ))}
                      {fallbackReceiptSuggestions.map((suggestion) => (
                        <div key={suggestion.id} className="flex flex-col gap-3 rounded-[18px] border border-emerald-100 bg-emerald-50/45 p-3 sm:flex-row sm:items-center sm:justify-between dark:border-emerald-500/20 dark:bg-emerald-500/10">
                          <div>
                            <p className="text-sm font-black text-text dark:text-slate-100">باید از {suggestion.payerName} پول بگیرید</p>
                            <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">منتظر ثبت پرداخت</p>
                          </div>
                          <span className="text-sm font-black text-emerald-700 dark:text-emerald-200">{formatMoney(suggestion.amount_minor)}</span>
                        </div>
                      ))}

                      {myRegisteredSettlements.length > 0 ? (
                        <div className="mt-4 border-t border-slate-100 pt-4 dark:border-slate-800">
                          <h3 className="mb-2 text-sm font-black text-text dark:text-slate-100">پرداخت‌های ثبت‌شده</h3>
                          <div className="space-y-2">
                            {myRegisteredSettlements.slice(0, 10).map((settlement) => {
                              const isPayer = settlement.payer_user_id === currentUserId;
                              const isReceiver = settlement.receiver_user_id === currentUserId;

                              return (
                                <div key={settlement.id} className="flex flex-col gap-3 rounded-[18px] border border-slate-100 bg-slate-50/55 p-3 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900/80">
                                  <div className="min-w-0 text-right">
                                    <p className="truncate text-sm font-black text-text dark:text-slate-100">{getUserDisplayFromId(settlement.payer_user_id, members)} به {getUserDisplayFromId(settlement.receiver_user_id, members)}</p>
                                    <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">{getSettlementStatusLabel(settlement.status)} · {toPersianDate(settlement.created_at)}</p>
                                  </div>
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className="text-sm font-black text-slate-700 dark:text-slate-200">{formatMoney(settlement.amount_minor)}</span>
                                    {isReceiver && settlement.status === 'PENDING_CONFIRMATION' ? <><Button onClick={() => void handleSettlementAction(settlement, 'confirm')} className="min-h-9 px-3 text-xs">پول را گرفتم</Button><Button tone="danger" onClick={() => void handleSettlementAction(settlement, 'reject')} className="min-h-9 px-3 text-xs">نگرفتم</Button></> : null}
                                    {isPayer && settlement.status === 'PENDING_CONFIRMATION' ? <Button tone="secondary" onClick={() => void handleSettlementAction(settlement, 'cancel')} className="min-h-9 px-3 text-xs">لغو پرداخت</Button> : null}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  )}
                </>
              ) : null}

              {activeView === 'members' ? (
                <>
                  <div className="mb-3 flex items-center justify-between gap-3 px-1">
                    <div><h2 className="text-base font-black text-text dark:text-slate-100">اعضای گروه</h2><p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">{toPersianNumber(members.length)} عضو</p></div>
                    <Button tone="secondary" onClick={() => setModal('settings')} className="min-h-10 px-3 text-xs">مدیریت اعضا</Button>
                  </div>
                  {membersLoading ? (
                    <div className="flex min-h-[280px] items-center justify-center gap-2 text-sm font-bold text-muted dark:text-slate-400"><Loader2 className="h-4 w-4 animate-spin" />در حال دریافت اعضا...</div>
                  ) : (
                    <div className="grid gap-2 sm:grid-cols-2">
                      {members.map((member) => (
                        <div key={getMemberId(member) || getMemberUserId(member)} className="flex items-center justify-between gap-3 rounded-[18px] border border-slate-100 bg-slate-50/55 p-3 dark:border-slate-800 dark:bg-slate-900/80">
                          <div className="flex min-w-0 items-center gap-3"><MemberAvatar name={getMemberName(member)} owner={member.role === 'OWNER'} /><div className="min-w-0"><p className="truncate text-sm font-black text-text dark:text-slate-100">{getMemberName(member)}</p><p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">{getRoleLabel(member.role)}</p></div></div>
                          <UserRound className="h-4 w-4 shrink-0 text-slate-400" />
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : null}
            </section>
          </div>
        </section>
      </div>


     <Modal
        open={modal === 'expense'}
        onClose={() => setModal(null)}
        title="ثبت هزینه"
        icon={<ReceiptText className="h-5 w-5" />}
        size="lg"
      >
        <div className="space-y-4 text-right">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="عنوان">
              <input
                dir="rtl"
                value={expenseTitle}
                onChange={(event) => setExpenseTitle(event.target.value)}
                placeholder="مثلاً شام"
                className={inputClass}
              />
            </Field>

            <Field label="مبلغ">
              <input
                dir="rtl"
                value={expenseAmount}
                onChange={(event) => setExpenseAmount(event.target.value)}
                placeholder="مثلاً ۲۵۰٬۰۰۰"
                inputMode="numeric"
                className={inputClass}
              />
            </Field>
          </div>

          <Field label="پرداخت‌کننده">
            <select
              value={expensePayerId}
              onChange={(event) => setExpensePayerId(event.target.value)}
              className={inputClass}
            >
              {members.map((member) => {
                const userId = getMemberUserId(member);
                return (
                  <option key={userId} value={userId}>
                    {getMemberName(member)}
                  </option>
                );
              })}
            </select>
          </Field>

          <div className={cn(dashboardQuietCard, 'flex max-h-[420px] flex-col overflow-hidden p-4 text-right')}>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-sm font-black text-text dark:text-slate-100">تقسیم بین اعضا</h3>

              <div className="flex rounded-[18px] bg-white p-1 shadow-[0_8px_20px_rgba(15,23,42,0.035)] dark:bg-slate-900">
                <button
                  type="button"
                  onClick={() => setExpenseSplitMethod('EQUAL')}
                  className={cn(
                    'rounded-[18px] px-3 py-2 text-xs font-black transition',
                    expenseSplitMethod === 'EQUAL'
                      ? 'bg-emerald-600 text-white dark:bg-emerald-500'
                      : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800',
                  )}
                >
                  مساوی
                </button>

                <button
                  type="button"
                  onClick={() => setExpenseSplitMethod('CUSTOM_AMOUNT')}
                  className={cn(
                    'rounded-[18px] px-3 py-2 text-xs font-black transition',
                    expenseSplitMethod === 'CUSTOM_AMOUNT'
                      ? 'bg-emerald-600 text-white dark:bg-emerald-500'
                      : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800',
                  )}
                >
                  متفاوت
                </button>
              </div>
            </div>

            <div className={cn(scrollAreaClass, 'flex-1')}>
              <div className="grid gap-2 sm:grid-cols-2">
                {members.map((member) => {
                  const userId = getMemberUserId(member);
                  const selected = expenseParticipantIds.includes(userId);

                  return (
                    <div
                      key={userId}
                      className={cn(
                        'dashboard-list-card rounded-[20px] border bg-white/92 p-3 text-right shadow-[0_8px_22px_rgba(15,23,42,0.035)] transition dark:bg-slate-900/80',
                        selected
                          ? 'border-emerald-300/80 dark:border-emerald-500/30'
                          : 'border-emerald-200/70 opacity-70 dark:border-slate-700',
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => toggleExpenseParticipant(userId)}
                        className="flex w-full items-center justify-between gap-3 text-right"
                      >
                        <div className="flex min-w-0 items-center gap-3 text-right">
                          <MemberAvatar name={getMemberName(member)} owner={member.role === 'OWNER'} />
                          <span className="truncate text-sm font-black text-text dark:text-slate-100">{getMemberName(member)}</span>
                        </div>

                        <span
                          className={cn(
                            'flex h-8 w-8 items-center justify-center rounded-[18px]',
                            selected
                              ? 'bg-emerald-600 text-white dark:bg-emerald-500'
                              : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500',
                          )}
                        >
                          {selected ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                        </span>
                      </button>

                      {expenseSplitMethod === 'CUSTOM_AMOUNT' && selected ? (
                        <input
                          dir="rtl"
                          inputMode="numeric"
                          value={expenseCustomShares[userId] || ''}
                          onChange={(event) => setExpenseCustomShares((prev) => ({ ...prev, [userId]: event.target.value }))}
                          placeholder="سهم این نفر"
                          className="mt-3 h-10 w-full rounded-[18px] border border-emerald-200/90 bg-slate-50 px-3 text-right text-xs font-bold outline-none focus:border-emerald-400 focus:bg-white dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:bg-slate-950"
                        />
                      ) : null}
                    </div>
                  );
                })}
              </div>

              {expenseSplitMethod === 'CUSTOM_AMOUNT' ? (
                <p className="mt-3 rounded-[18px] border border-emerald-200/70 bg-white px-3 py-2 text-right text-xs font-black text-slate-600 shadow-[0_8px_20px_rgba(15,23,42,0.035)] dark:border-emerald-500/20 dark:bg-slate-900 dark:text-slate-300">
                  جمع سهم‌ها: {formatMoney(customSharesTotalMinor)} از {formatMoney(baseAmountMinor)}
                </p>
              ) : null}
            </div>
          </div>

          {!showAdvancedExpense ? (
            <button
              type="button"
              onClick={() => setShowAdvancedExpense(true)}
              className="flex w-full items-center justify-between rounded-[18px] border border-emerald-200/80 bg-white px-4 py-3 text-right text-sm font-black text-slate-700 shadow-[0_10px_26px_rgba(15,23,42,0.04)] transition hover:bg-emerald-50/40 dark:border-emerald-500/20 dark:bg-slate-900/80 dark:text-slate-200 dark:hover:bg-emerald-500/10"
            >
              گزینه‌های بیشتر
              <Plus className="h-4 w-4" />
            </button>
          ) : (
            <div className={cn(dashboardQuietCard, 'max-h-[420px] space-y-3 overflow-y-auto p-4 text-right')}>
              <button
                type="button"
                onClick={() => setShowAdvancedExpense(false)}
                className="flex w-full items-center justify-between border-b border-emerald-100 pb-3 text-right text-sm font-black text-slate-800 dark:border-emerald-500/15 dark:text-slate-100"
              >
                <span>گزینه‌های بیشتر</span>
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                  <X className="h-4 w-4" />
                </span>
              </button>

              <Field label="توضیح">
                <textarea
                  dir="rtl"
                  value={expenseDescription}
                  onChange={(event) => setExpenseDescription(event.target.value)}
                  placeholder="اختیاری"
                  className={textareaClass}
                />
              </Field>

              <Field label="رسید">
                <div className="flex min-h-12 items-center rounded-[18px] border border-emerald-200/90 bg-white px-3 py-2 text-right dark:border-emerald-500/20 dark:bg-slate-900/80">
                  <Upload className="ml-2 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-300" />
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/jpg,image/webp,application/pdf"
                    onChange={(event) => setReceiptFile(event.target.files?.[0] || null)}
                    className="w-full text-right text-xs font-bold text-slate-600 file:ml-3 file:rounded-[18px] file:border-0 file:bg-emerald-50 file:px-3 file:py-2 file:text-xs file:font-black file:text-emerald-700 dark:text-slate-300 dark:file:bg-emerald-500/10 dark:file:text-emerald-200"
                  />
                </div>
              </Field>

              {canManageGroup ? (
                <div className="rounded-[20px] border border-sky-200 bg-sky-50/55 p-3 text-right dark:border-sky-500/20 dark:bg-sky-500/10">
                  <label className="flex cursor-pointer items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 text-sm font-black text-slate-800 dark:text-slate-100">
                        <Bell className="h-4 w-4 text-sky-600 dark:text-sky-300" />
                        یادآوری پرداخت بدهی‌های گروه
                      </div>
                      <p className="mt-1 text-xs font-semibold leading-6 text-muted dark:text-slate-400">
                        بعد از ثبت هزینه، ایمیل برای بدهی‌های باز همین گروه طبق برنامه ارسال می‌شود.
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={enableReminderAfterExpense}
                      disabled={reminderLoading || !reminderSettings}
                      onChange={(event) => {
                        const enabled = event.target.checked;
                        setEnableReminderAfterExpense(enabled);
                        if (!enabled) setSendExpenseReminderImmediately(false);
                        setReminderSettings((current) => current ? { ...current, is_enabled: enabled, send_email: enabled ? true : current.send_email } : current);
                      }}
                      className="mt-1 h-5 w-5 accent-emerald-600 disabled:opacity-50"
                    />
                  </label>

                  {enableReminderAfterExpense && reminderSettings ? (
                    <div className="mt-4 grid gap-3 sm:grid-cols-3">
                      <Field label="اولین ایمیل">
                        <select
                          value={sendExpenseReminderImmediately ? 0 : reminderSettings.first_reminder_after_hours}
                          onChange={(event) => {
                            const hours = Number(event.target.value);
                            setSendExpenseReminderImmediately(hours === 0);
                            if (hours > 0) {
                              setReminderSettings((current) => current ? { ...current, first_reminder_after_hours: hours } : current);
                            }
                          }}
                          className={inputClass}
                        >
                          <option value={0}>همان موقع ثبت هزینه</option>
                          {reminderFirstDelayOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                        </select>
                      </Field>
                      <Field label="تکرار ایمیل">
                        <select
                          value={reminderSettings.repeat_interval_hours}
                          onChange={(event) => setReminderSettings((current) => current ? { ...current, repeat_interval_hours: Number(event.target.value) } : current)}
                          className={inputClass}
                        >
                          {reminderIntervalOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                        </select>
                      </Field>
                      <Field label="حداکثر دفعات">
                        <select
                          value={reminderSettings.maximum_reminders}
                          onChange={(event) => setReminderSettings((current) => current ? { ...current, maximum_reminders: Number(event.target.value) } : current)}
                          className={inputClass}
                        >
                          {[1, 2, 3, 5].map((count) => <option key={count} value={count}>{toPersianNumber(count)} بار</option>)}
                        </select>
                      </Field>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          )}

          <div className="dashboard-balance-mini dashboard-balance-mini--credit rounded-[22px] border border-emerald-300/80 bg-gradient-to-l from-white via-emerald-50/70 to-emerald-50/60 p-4 text-right shadow-[inset_3px_0_0_#10B981,0_0_0_1px_rgba(16,185,129,0.10),0_10px_24px_rgba(15,23,42,0.06)] dark:border-emerald-500/30 dark:bg-slate-900/80">
            <p className="text-xs font-extrabold text-muted dark:text-slate-400">مبلغ نهایی</p>
            <p className="mt-1 text-3xl font-black tracking-[-0.05em] text-emerald-700 dark:text-emerald-200">
              {formatMoney(expenseFinalTotalMinor)}
            </p>
          </div>

          <Button onClick={handleCreateExpense} disabled={expenseSaving || members.length === 0 || isArchived} className="h-12 w-full text-base">
            {expenseSaving ? (
              <InlineLoader label={receiptFile ? 'آپلود و ثبت...' : 'در حال ثبت...'} />
            ) : (
              <>
                <Plus className="h-5 w-5" />
                ثبت هزینه
              </>
            )}
          </Button>
        </div>
      </Modal>

      <Modal
        open={modal === 'settlement'}
        onClose={() => setModal(null)}
        title="جزئیات تسویه"
        icon={<Users className="h-5 w-5" />}
        size="xl"
      >
        <div className="space-y-4 text-right">
          <div className="flex items-center justify-between gap-3 px-1">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200">
                <Users className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <h3 className="truncate text-base font-black text-text dark:text-slate-100">{group?.title || 'گروه'}</h3>
                <p className="mt-1 text-xs font-bold text-muted dark:text-slate-400">{toPersianNumber(members.length)} نفر عضو</p>
              </div>
            </div>
            <Button
              tone="secondary"
              onClick={() => void handleSmartSettlementCalculation()}
              disabled={settlementSaving || settlementLoading || isArchived}
              className="min-h-10 shrink-0 px-3 text-xs"
            >
              {settlementSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              محاسبه دوباره
            </Button>
          </div>

          {settlementDataError ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-[18px] border border-amber-200 bg-amber-50 px-4 py-3 text-xs font-bold text-amber-700 dark:border-amber-500/25 dark:bg-amber-500/10 dark:text-amber-200">
              <span>{settlementDataError}</span>
              <button type="button" onClick={() => void loadSettlementData()} className="rounded-full px-3 py-1.5 font-black hover:bg-amber-100 dark:hover:bg-amber-500/10">تلاش دوباره</button>
            </div>
          ) : null}

          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-[22px] border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/80">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-bold text-muted dark:text-slate-400">وضعیت نهایی شما</p>
                  <p className={cn(
                    'mt-2 text-lg font-black',
                    myNetMinor < 0
                      ? 'text-rose-600 dark:text-rose-200'
                      : myNetMinor > 0
                        ? 'text-emerald-700 dark:text-emerald-200'
                        : 'text-slate-700 dark:text-slate-200',
                  )}>
                    {accountTitle} · {formatMoney(Math.abs(myNetMinor))}
                  </p>
                </div>
                <span className={cn(
                  'flex h-11 w-11 shrink-0 items-center justify-center rounded-full',
                  myNetMinor < 0
                    ? 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-200'
                    : 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200',
                )}>
                  <WalletCards className="h-5 w-5" />
                </span>
              </div>
              <p className="mt-3 text-[11px] font-semibold leading-5 text-muted dark:text-slate-400">
                با تأیید پرداخت‌های پیشنهادی، خالص حساب همین گروه بروزرسانی می‌شود.
              </p>
            </div>

            <div className="rounded-[22px] border border-rose-100 bg-rose-50/45 p-4 dark:border-rose-500/20 dark:bg-rose-500/10">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-bold text-slate-600 dark:text-slate-300">بدهی شما به این گروه</p>
                  <p className="mt-2 text-lg font-black text-rose-600 dark:text-rose-200">
                    {formatMoney(detailedPayableMinor || Math.abs(Math.min(myNetMinor, 0)))}
                  </p>
                </div>
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-rose-100 text-rose-600 dark:bg-rose-500/15 dark:text-rose-200">
                  <ArrowUp className="h-5 w-5" />
                </span>
              </div>
            </div>

            <div className="rounded-[22px] border border-emerald-100 bg-emerald-50/45 p-4 dark:border-emerald-500/20 dark:bg-emerald-500/10">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-bold text-slate-600 dark:text-slate-300">طلب شما از این گروه</p>
                  <p className="mt-2 text-lg font-black text-emerald-700 dark:text-emerald-200">
                    {formatMoney(detailedReceivableMinor || Math.max(myNetMinor, 0))}
                  </p>
                </div>
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-200">
                  <ArrowDown className="h-5 w-5" />
                </span>
              </div>
            </div>
          </div>


          <div className="grid grid-cols-3 rounded-[20px] bg-slate-50 p-1 dark:bg-slate-900">
            {([
              { id: 'suggestion', label: 'پیشنهاد تسویه', icon: Sparkles },
              { id: 'debts', label: 'جزئیات بدهی‌ها', icon: Scale },
              { id: 'history', label: 'تاریخچه پرداخت‌ها', icon: History },
            ] as Array<{ id: SettlementModalTab; label: string; icon: typeof Sparkles }>).map((tab) => {
              const TabIcon = tab.icon;
              const active = settlementModalTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setSettlementModalTab(tab.id)}
                  className={cn(
                    'relative flex min-h-12 items-center justify-center gap-2 rounded-[17px] px-2 text-xs font-black transition sm:text-sm',
                    active
                      ? 'bg-white text-emerald-700 shadow-sm dark:bg-slate-800 dark:text-emerald-200'
                      : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200',
                  )}
                >
                  <TabIcon className="h-4 w-4" />
                  <span className="truncate">{tab.label}</span>
                  {active ? <span className="absolute inset-x-4 bottom-0 h-0.5 rounded-full bg-emerald-500" /> : null}
                </button>
              );
            })}
          </div>

          {settlementModalTab === 'suggestion' ? (
            <section className="rounded-[24px] border border-emerald-100 bg-gradient-to-b from-emerald-50/70 to-white p-4 dark:border-emerald-500/20 dark:from-emerald-500/10 dark:to-slate-950 sm:p-5">
              <div className="mb-4 text-center">
                <div className="flex items-center justify-center gap-2 text-emerald-700 dark:text-emerald-200">
                  <Sparkles className="h-5 w-5" />
                  <h3 className="text-base font-black">پیشنهاد هوشمند برای تسویه شما</h3>
                </div>
                <p className="mt-2 text-xs font-semibold leading-6 text-muted dark:text-slate-400">
                  بدهی‌ها و طلب‌ها با هم خالص شده‌اند تا با کمترین تعداد پرداخت، حساب شما در این گروه صاف شود.
                </p>
              </div>

              {settlementLoading ? (
                <div className="flex min-h-[220px] items-center justify-center gap-2 text-sm font-bold text-muted dark:text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  در حال محاسبه پیشنهادها...
                </div>
              ) : pendingReceivedPlanItems.length === 0 && myPendingIncomingSettlements.length === 0 && myDebtItems.length === 0 && fallbackPaymentSuggestions.length === 0 && myPendingOutgoingSettlements.length === 0 ? (
                <EmptyState
                  title={myNetMinor >= 0 ? 'پرداختی برای شما وجود ندارد' : 'پیشنهادی ساخته نشده'}
                  description={myNetMinor >= 0 ? 'در حال حاضر بدهی قابل پرداختی در این گروه ندارید.' : 'دکمه محاسبه دوباره را بزنید.'}
                  icon={<Check className="h-6 w-6" />}
                />
              ) : (
                <div className="space-y-3">
                  {pendingReceivedPlanItems.map((item) => (
                    <div key={`incoming-plan-${item.id}`} className="rounded-[22px] border border-amber-200 bg-amber-50/80 p-4 shadow-[0_12px_30px_rgba(15,23,42,0.05)] dark:border-amber-500/25 dark:bg-amber-500/10">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex min-w-0 items-center gap-3">
                          <MemberAvatar name={getPlanPartyName(item, 'payer', members)} />
                          <div className="min-w-0">
                            <p className="text-xs font-bold text-amber-700 dark:text-amber-200">پرداخت ثبت‌شده از طرف</p>
                            <p className="mt-1 truncate text-base font-black text-text dark:text-slate-100">{getPlanPartyName(item, 'payer', members)}</p>
                          </div>
                        </div>
                        <div className="text-right sm:text-left">
                          <p className="text-xs font-bold text-amber-700 dark:text-amber-200">مبلغ اعلام‌شده</p>
                          <p className="mt-1 text-xl font-black text-amber-700 dark:text-amber-200">{formatMoney(item.amount_minor)}</p>
                        </div>
                      </div>

                      <p className="mt-4 rounded-[16px] bg-white/80 px-3 py-2.5 text-xs font-semibold leading-6 text-amber-800 dark:bg-slate-950/60 dark:text-amber-100">
                        این پرداخت فقط بعد از تأیید شما بدهی پرداخت‌کننده را تسویه می‌کند.
                      </p>

                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        <Button onClick={() => void handlePlanItemAction(item, 'confirm')} disabled={settlementSaving} className="h-11 text-sm">
                          <Check className="h-4 w-4" />
                          پول را گرفتم
                        </Button>
                        <Button tone="danger" onClick={() => void handlePlanItemAction(item, 'reject')} disabled={settlementSaving} className="h-11 text-sm">
                          <X className="h-4 w-4" />
                          دریافت نکردم
                        </Button>
                      </div>
                    </div>
                  ))}

                  {myPendingIncomingSettlements.map((settlement) => (
                    <div key={`incoming-manual-${settlement.id}`} className="rounded-[22px] border border-amber-200 bg-amber-50/80 p-4 shadow-[0_12px_30px_rgba(15,23,42,0.05)] dark:border-amber-500/25 dark:bg-amber-500/10">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex min-w-0 items-center gap-3">
                          <MemberAvatar name={getUserDisplayFromId(settlement.payer_user_id, members)} />
                          <div className="min-w-0">
                            <p className="text-xs font-bold text-amber-700 dark:text-amber-200">پرداخت ثبت‌شده از طرف</p>
                            <p className="mt-1 truncate text-base font-black text-text dark:text-slate-100">{getUserDisplayFromId(settlement.payer_user_id, members)}</p>
                          </div>
                        </div>
                        <div className="text-right sm:text-left">
                          <p className="text-xs font-bold text-amber-700 dark:text-amber-200">مبلغ اعلام‌شده</p>
                          <p className="mt-1 text-xl font-black text-amber-700 dark:text-amber-200">{formatMoney(settlement.amount_minor)}</p>
                        </div>
                      </div>

                      <p className="mt-4 rounded-[16px] bg-white/80 px-3 py-2.5 text-xs font-semibold leading-6 text-amber-800 dark:bg-slate-950/60 dark:text-amber-100">
                        این پرداخت دستی فقط بعد از تأیید شما در حساب پرداخت‌کننده ثبت می‌شود.
                      </p>

                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        <Button onClick={() => void handleSettlementAction(settlement, 'confirm')} disabled={settlementSaving} className="h-11 text-sm">
                          <Check className="h-4 w-4" />
                          پول را گرفتم
                        </Button>
                        <Button tone="danger" onClick={() => void handleSettlementAction(settlement, 'reject')} disabled={settlementSaving} className="h-11 text-sm">
                          <X className="h-4 w-4" />
                          دریافت نکردم
                        </Button>
                      </div>
                    </div>
                  ))}

                  {myDebtItems.map((item) => {
                    const outgoingCount = outstandingDetailedDebts.filter(
                      (debt) => debt.debtor_user_id === currentUserId && debt.creditor_user_id === item.receiver_user_id,
                    ).length;
                    const incomingCount = outstandingDetailedDebts.filter(
                      (debt) => debt.creditor_user_id === currentUserId && debt.debtor_user_id === item.receiver_user_id,
                    ).length;

                    return (
                      <div key={item.id} className="rounded-[22px] border border-emerald-200 bg-white p-4 shadow-[0_12px_30px_rgba(15,23,42,0.06)] dark:border-emerald-500/20 dark:bg-slate-900/90">
                        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                          <div className="flex min-w-0 items-center gap-3">
                            <MemberAvatar name={getPlanPartyName(item, 'receiver', members)} />
                            <div className="min-w-0">
                              <p className="text-xs font-bold text-muted dark:text-slate-400">پرداخت به</p>
                              <p className="mt-1 truncate text-base font-black text-text dark:text-slate-100">{getPlanPartyName(item, 'receiver', members)}</p>
                            </div>
                          </div>
                          <div className="text-right sm:text-left">
                            <p className="text-xs font-bold text-muted dark:text-slate-400">مبلغ پرداخت</p>
                            <p className="mt-1 text-xl font-black text-emerald-700 dark:text-emerald-200">{formatMoney(item.amount_minor)}</p>
                          </div>
                        </div>

                        <p className="mt-4 rounded-[16px] bg-slate-50 px-3 py-2.5 text-xs font-semibold leading-6 text-slate-600 dark:bg-slate-950 dark:text-slate-300">
                          این پرداخت، {toPersianNumber(outgoingCount)} بدهی شما و {toPersianNumber(incomingCount)} طلب شما در برابر {getPlanPartyName(item, 'receiver', members)} را در محاسبه خالص گروه لحاظ می‌کند.
                        </p>

                        {canReportPlanItem(item, settlementPlan) ? (
                          <div className="mt-3 grid gap-2 sm:grid-cols-2">
                            <Button onClick={() => void handleWalletSettlementPayment(item)} disabled={settlementSaving || walletPaymentItemId === item.id} className="h-12 w-full text-base">
                              {walletPaymentItemId === item.id ? <Loader2 className="h-5 w-5 animate-spin" /> : <WalletCards className="h-5 w-5" />}
                              پرداخت با کیف پول
                            </Button>
                            <Button tone="secondary" onClick={() => void handlePlanItemAction(item, 'paid')} disabled={settlementSaving || walletPaymentItemId === item.id} className="h-12 w-full text-base">
                              <Check className="h-5 w-5" />
                              ثبت پرداخت دستی
                            </Button>
                          </div>
                        ) : (
                          <div className="mt-3 rounded-[16px] border border-slate-200 bg-slate-50 px-3 py-3 text-center text-xs font-black text-slate-600 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300">
                            {getSettlementStatusLabel(item.status)}
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {fallbackPaymentSuggestions.map((suggestion) => {
                    const outgoingCount = outstandingDetailedDebts.filter(
                      (debt) => debt.debtor_user_id === currentUserId && debt.creditor_user_id === suggestion.receiver_user_id,
                    ).length;
                    const incomingCount = outstandingDetailedDebts.filter(
                      (debt) => debt.creditor_user_id === currentUserId && debt.debtor_user_id === suggestion.receiver_user_id,
                    ).length;

                    return (
                      <div key={suggestion.id} className="rounded-[22px] border border-emerald-200 bg-white p-4 shadow-[0_12px_30px_rgba(15,23,42,0.06)] dark:border-emerald-500/20 dark:bg-slate-900/90">
                        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                          <div className="flex min-w-0 items-center gap-3">
                            <MemberAvatar name={suggestion.receiverName} />
                            <div className="min-w-0"><p className="text-xs font-bold text-muted dark:text-slate-400">پرداخت به</p><p className="mt-1 truncate text-base font-black text-text dark:text-slate-100">{suggestion.receiverName}</p></div>
                          </div>
                          <div className="text-right sm:text-left"><p className="text-xs font-bold text-muted dark:text-slate-400">مبلغ پرداخت</p><p className="mt-1 text-xl font-black text-emerald-700 dark:text-emerald-200">{formatMoney(suggestion.amount_minor)}</p></div>
                        </div>
                        <p className="mt-4 rounded-[16px] bg-slate-50 px-3 py-2.5 text-xs font-semibold leading-6 text-slate-600 dark:bg-slate-950 dark:text-slate-300">
                          این مبلغ پس از خالص‌کردن {toPersianNumber(outgoingCount)} بدهی و {toPersianNumber(incomingCount)} طلب شما محاسبه شده است.
                        </p>
                        <Button
                          onClick={() => void handleCreateManualSettlement(suggestion.receiver_user_id, suggestion.amount_minor)}
                          disabled={settlementSaving}
                          className="mt-3 h-12 w-full text-base"
                        >
                          <Check className="h-5 w-5" />
                          ثبت پرداخت و تسویه
                        </Button>
                      </div>
                    );
                  })}

                  {myPendingOutgoingSettlements.map((settlement) => (
                    <div key={`pending-${settlement.id}`} className="rounded-[22px] border border-amber-200 bg-amber-50/70 p-4 dark:border-amber-500/25 dark:bg-amber-500/10">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="text-xs font-bold text-amber-700 dark:text-amber-200">پرداخت دستی ثبت شده به</p>
                          <p className="mt-1 text-base font-black text-text dark:text-slate-100">{getUserDisplayFromId(settlement.receiver_user_id, members)}</p>
                        </div>
                        <div className="sm:text-left">
                          <p className="text-lg font-black text-amber-700 dark:text-amber-200">{formatMoney(settlement.amount_minor)}</p>
                          <p className="mt-1 text-xs font-bold text-amber-700/80 dark:text-amber-200/80">در انتظار تأیید دریافت‌کننده</p>
                        </div>
                      </div>
                    </div>
                  ))}

                  <p className="text-center text-[11px] font-semibold leading-5 text-muted dark:text-slate-400">
                    پرداخت ابتدا ثبت می‌شود؛ پس از تأیید دریافت‌کننده، بدهی‌های پوشش‌داده‌شده در همین گروه از فهرست بدهی‌های باز خارج می‌شوند.
                  </p>
                </div>
              )}
            </section>
          ) : null}

          {settlementModalTab === 'debts' ? (
            <section className="rounded-[24px] border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/70 sm:p-5">
              <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-base font-black text-text dark:text-slate-100">بدهی‌ها و طلب‌های تشکیل‌دهنده حساب شما</h3>
                  <p className="mt-1 text-xs font-semibold leading-6 text-muted dark:text-slate-400">هر ردیف از هزینه‌های همین گروه ساخته شده است.</p>
                </div>
              </div>

              {settlementLoading ? (
                <div className="flex min-h-[220px] items-center justify-center gap-2 text-sm font-bold text-muted dark:text-slate-400"><Loader2 className="h-4 w-4 animate-spin" />در حال دریافت بدهی‌ها...</div>
              ) : outstandingDetailedDebts.length === 0 ? (
                <EmptyState title="بدهی بازی وجود ندارد" description="حساب شما در این گروه صاف است." icon={<Check className="h-6 w-6" />} />
              ) : (
                <div className="space-y-2">
                  {outstandingDetailedDebts.map((debt) => {
                    const isPayable = debt.debtor_user_id === currentUserId;
                    const counterpartyId = isPayable ? debt.creditor_user_id : debt.debtor_user_id;
                    const expense = debt.source_expense_id ? expenseById.get(debt.source_expense_id) : undefined;
                    const hasPendingPayment = isPayable && settlements.some(
                      (item) =>
                        item.payer_user_id === currentUserId &&
                        item.receiver_user_id === counterpartyId &&
                        ['PENDING', 'PENDING_CONFIRMATION', 'REPORTED'].includes(item.status || 'PENDING_CONFIRMATION'),
                    );
                    const walletPlanItem = isPayable ? findWalletPlanItemForDebt(debt) : null;
                    const walletPaymentBusy = walletPlanItem ? walletPaymentItemId === walletPlanItem.id : false;
                    return (
                      <div key={debt.id} className={cn(
                        'rounded-[18px] border p-3',
                        isPayable
                          ? 'border-rose-100 bg-rose-50/45 dark:border-rose-500/20 dark:bg-rose-500/10'
                          : 'border-emerald-100 bg-emerald-50/45 dark:border-emerald-500/20 dark:bg-emerald-500/10',
                      )}>
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-black text-text dark:text-slate-100">{expense?.title || 'هزینه گروه'}</p>
                            <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">
                              {isPayable ? `شما به ${getDebtPartyName(counterpartyId, members)} بدهکارید` : `${getDebtPartyName(counterpartyId, members)} به شما بدهکار است`}
                            </p>
                          </div>
                          <div className="flex shrink-0 flex-wrap items-center gap-2">
                            <span className={cn('text-sm font-black', isPayable ? 'text-rose-600 dark:text-rose-200' : 'text-emerald-700 dark:text-emerald-200')}>
                              {formatMoney(debt.amount_minor)}
                            </span>
                            {isPayable ? (
                              <>
                                <Button
                                  onClick={() => void handleWalletDetailedDebtPayment(debt)}
                                  disabled={settlementSaving || hasPendingPayment || walletPaymentBusy}
                                  className="min-h-9 px-3 text-xs"
                                >
                                  {walletPaymentBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <WalletCards className="h-4 w-4" />}
                                  {hasPendingPayment ? 'منتظر تأیید' : 'پرداخت با کیف پول'}
                                </Button>
                                <Button
                                  tone="secondary"
                                  onClick={() => void handlePayDetailedDebt(debt)}
                                  disabled={settlementSaving || hasPendingPayment}
                                  className="min-h-9 px-3 text-xs"
                                >
                                  <HandCoins className="h-4 w-4" />
                                  ثبت پرداخت دستی
                                </Button>
                              </>
                            ) : null}
                          </div>
                        </div>

                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          ) : null}

          {settlementModalTab === 'history' ? (
            <section className="rounded-[24px] border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/70 sm:p-5">
              <h3 className="mb-4 text-base font-black text-text dark:text-slate-100">تاریخچه پرداخت‌های شما در این گروه</h3>
              {myRegisteredSettlements.length === 0 ? (
                <EmptyState title="پرداختی ثبت نشده" description="پرداخت‌های این گروه بعد از ثبت در این بخش نمایش داده می‌شوند." icon={<History className="h-6 w-6" />} />
              ) : (
                <div className="space-y-2">
                  {myRegisteredSettlements.map((settlement) => {
                    const isPayer = settlement.payer_user_id === currentUserId;
                    const isReceiver = settlement.receiver_user_id === currentUserId;
                    return (
                      <div key={settlement.id} className="flex flex-col gap-3 rounded-[18px] border border-slate-100 bg-slate-50/60 p-3 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-950">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-black text-text dark:text-slate-100">{getUserDisplayFromId(settlement.payer_user_id, members)} به {getUserDisplayFromId(settlement.receiver_user_id, members)}</p>
                          <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">{getSettlementStatusLabel(settlement.status)} · {toPersianDate(settlement.created_at)}</p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-black text-slate-700 dark:text-slate-200">{formatMoney(settlement.amount_minor)}</span>
                          {isReceiver && settlement.status === 'PENDING_CONFIRMATION' ? (
                            <><Button onClick={() => void handleSettlementAction(settlement, 'confirm')} className="min-h-9 px-3 text-xs">پول را گرفتم</Button><Button tone="danger" onClick={() => void handleSettlementAction(settlement, 'reject')} className="min-h-9 px-3 text-xs">نگرفتم</Button></>
                          ) : null}
                          {isPayer && settlement.status === 'PENDING_CONFIRMATION' ? <Button tone="secondary" onClick={() => void handleSettlementAction(settlement, 'cancel')} className="min-h-9 px-3 text-xs">لغو پرداخت</Button> : null}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          ) : null}

        </div>
      </Modal>

      <Modal
        open={false}
        onClose={() => setModal(null)}
        title="جزئیات تسویه"
        icon={<HandCoins className="h-5 w-5" />}
        size="lg"
      >
        <div className="space-y-4 text-right">
          <div className="dashboard-section-card dashboard-section-card--quiet rounded-[22px] border border-emerald-300/80 bg-gradient-to-l from-white via-emerald-50/80 to-emerald-50/70 p-4 text-right shadow-[0_12px_30px_rgba(15,23,42,0.07)] dark:border-emerald-500/20 dark:bg-slate-900/80">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h3 className="text-base font-black text-emerald-800 dark:text-emerald-200">تسویه هوشمند</h3>

              <Button
                tone="primary"
                onClick={() => void refreshSmartSettlement()}
                disabled={settlementSaving || isArchived}
                className="h-11 shrink-0 px-4"
              >
                {settlementSaving ? (
                  <InlineLoader label="در حال محاسبه..." />
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    محاسبه
                  </>
                )}
              </Button>
            </div>
          </div>

          {settlementDataError ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-[18px] border border-amber-200 bg-amber-50 px-4 py-3 text-xs font-bold text-amber-700 dark:border-amber-500/25 dark:bg-amber-500/10 dark:text-amber-200">
              <span>{settlementDataError}</span>
              <button type="button" onClick={() => void loadSettlementData()} className="rounded-full px-3 py-1.5 font-black hover:bg-amber-100 dark:hover:bg-amber-500/10">تلاش دوباره</button>
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-3">
            <MiniNumberCard label="پرداخت من" value={formatMoney(visibleMyDebtMinor)} tone="rose" />
            <MiniNumberCard label="دریافت من" value={formatMoney(visibleMyCreditMinor)} tone="emerald" />
            <MiniNumberCard label="خالص حساب من" value={formatSignedMoney(myNetMinor)} tone={accountTone} />
          </div>

          <div className={cn(dashboardQuietCard, 'flex max-h-[460px] flex-col overflow-hidden p-4 text-right')}>
            <h3 className="mb-3 text-right text-sm font-black text-text dark:text-slate-100">ثبت پرداخت</h3>

            <div className={cn(scrollAreaClass, 'flex-1')}>
              {manualPayOptions.length > 0 || fallbackPaymentSuggestions.length > 0 ? (
                <div className="mb-4 space-y-2">
                  {manualPayOptions.map((item) => {
                    const selected = selectedManualPlanItemId === item.id;
                    const remainingAmount = item.amount_minor;
                    const partialAmount = parseAmountToMinor(manualAmount);
                    const restAfterPartial =
                      selected && manualPaymentMode === 'PARTIAL'
                        ? Math.max(remainingAmount - partialAmount, 0)
                        : remainingAmount;

                    return (
                      <div
                        key={item.id}
                        className={cn(
                          'dashboard-list-row dashboard-list-card rounded-[22px] border p-3 text-right transition',
                          selected
                            ? 'border-emerald-400 bg-emerald-50/80 shadow-[0_12px_28px_rgba(16,185,129,0.10)] dark:border-emerald-400/40 dark:bg-emerald-500/10'
                            : 'border-emerald-200 bg-white/90 hover:border-emerald-300 dark:border-emerald-500/15 dark:bg-slate-900/80 dark:hover:border-emerald-400/30',
                        )}
                      >
                        <button
                          type="button"
                          onClick={() => selectManualPlanItem(item)}
                          className="flex w-full items-center justify-between gap-3 text-right"
                        >
                          <span
                            className={cn(
                              'flex h-8 w-8 items-center justify-center rounded-[18px]',
                              selected
                                ? 'bg-emerald-600 text-white dark:bg-emerald-500'
                                : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500',
                            )}
                          >
                            {selected ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                          </span>

                          <div className="min-w-0 flex-1 text-right">
                            <p className="truncate text-sm font-black text-text dark:text-slate-100">
                              پرداخت به {getPlanPartyName(item, 'receiver', members)}
                            </p>
                            <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">
                              مانده: {formatMoney(remainingAmount)}
                            </p>
                          </div>
                        </button>

                        {selected ? (
                          <div className="mt-3 space-y-3">
                            <div className="grid grid-cols-2 gap-2">
                              <button
                                type="button"
                                onClick={() => {
                                  setManualPaymentMode('FULL');
                                  setManualAmount(String(item.amount_minor));
                                }}
                                className={cn(
                                  'rounded-[18px] border px-3 py-2 text-xs font-black transition',
                                  manualPaymentMode === 'FULL'
                                    ? 'border-emerald-400 bg-emerald-600 text-white dark:bg-emerald-500'
                                    : 'border-emerald-200 bg-white text-slate-600 hover:bg-emerald-50 dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-300 dark:hover:bg-emerald-500/10',
                                )}
                              >
                                پرداخت کامل
                              </button>

                              <button
                                type="button"
                                onClick={() => {
                                  setManualPaymentMode('PARTIAL');
                                  setManualAmount('');
                                }}
                                className={cn(
                                  'rounded-[18px] border px-3 py-2 text-xs font-black transition',
                                  manualPaymentMode === 'PARTIAL'
                                    ? 'border-emerald-400 bg-emerald-600 text-white dark:bg-emerald-500'
                                    : 'border-emerald-200 bg-white text-slate-600 hover:bg-emerald-50 dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-300 dark:hover:bg-emerald-500/10',
                                )}
                              >
                                پرداخت بخشی
                              </button>
                            </div>

                            {manualPaymentMode === 'PARTIAL' ? (
                              <div className="space-y-2">
                                <input
                                  dir="rtl"
                                  inputMode="numeric"
                                  value={manualAmount}
                                  onChange={(event) => setManualAmount(event.target.value)}
                                  placeholder="مبلغ"
                                  className={inputClass}
                                />

                                <div className="rounded-[18px] border border-emerald-200 bg-white/90 px-3 py-2 text-right text-xs font-black text-slate-600 dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-300">
                                  باقی‌مانده: {formatMoney(restAfterPartial)}
                                </div>
                              </div>
                            ) : null}

                            <input
                              dir="rtl"
                              value={manualDescription}
                              onChange={(event) => setManualDescription(event.target.value)}
                              placeholder="توضیح"
                              className={inputClass}
                            />

                            <Button onClick={() => void handleCreateManualSettlement()} disabled={settlementSaving} className="h-12 w-full text-base">
                              {manualPaymentMode === 'FULL' ? 'گزارش پرداخت کامل' : 'ثبت پرداخت بخشی'}
                            </Button>
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                  {fallbackPaymentSuggestions.map((suggestion) => (
                    <div
                      key={suggestion.id}
                      className="dashboard-list-row dashboard-list-card flex flex-col gap-3 rounded-[22px] border border-emerald-200 bg-white/90 p-3 text-right dark:border-emerald-500/15 dark:bg-slate-900/80 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="min-w-0 text-right">
                        <p className="truncate text-sm font-black text-text dark:text-slate-100">
                          پرداخت به {suggestion.receiverName}
                        </p>
                        <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">
                          مبلغ بدهی: {formatMoney(suggestion.amount_minor)}
                        </p>
                      </div>
                      <Button
                        onClick={() => void handleCreateManualSettlement(suggestion.receiver_user_id, suggestion.amount_minor)}
                        disabled={settlementSaving}
                        className="min-h-10 shrink-0 px-4 text-xs"
                      >
                        ثبت پرداخت
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="dashboard-panel-empty mb-4 rounded-[20px] border border-dashed border-emerald-200 bg-white/70 p-4 text-center text-xs font-bold text-muted dark:border-emerald-500/20 dark:bg-slate-900/70 dark:text-slate-400">
                  پرداختی برای ثبت نداری.
                </div>
              )}

              <div className="rounded-[20px] border border-emerald-200 bg-white/85 p-3 text-right dark:border-emerald-500/20 dark:bg-slate-900/80">
                <h4 className="mb-3 text-right text-xs font-black text-slate-600 dark:text-slate-300">پرداخت آزاد</h4>

                <div className="grid gap-3 sm:grid-cols-3">
                  <select
                    value={manualReceiverId}
                    onChange={(event) => {
                      setSelectedManualPlanItemId('');
                      setManualReceiverId(event.target.value);
                    }}
                    className={inputClass}
                  >
                    <option value="">دریافت‌کننده</option>
                    {members
                      .filter((member) => getMemberUserId(member) !== currentUserId)
                      .map((member) => {
                        const userId = getMemberUserId(member);
                        return (
                          <option key={userId} value={userId}>
                            {getMemberName(member)}
                          </option>
                        );
                      })}
                  </select>

                  <input
                    dir="rtl"
                    inputMode="numeric"
                    value={!selectedManualPlanItemId ? manualAmount : ''}
                    onChange={(event) => {
                      setSelectedManualPlanItemId('');
                      setManualAmount(event.target.value);
                    }}
                    placeholder="مبلغ"
                    className={inputClass}
                  />

                  <input
                    dir="rtl"
                    value={!selectedManualPlanItemId ? manualDescription : ''}
                    onChange={(event) => {
                      setSelectedManualPlanItemId('');
                      setManualDescription(event.target.value);
                    }}
                    placeholder="توضیح"
                    className={inputClass}
                  />
                </div>

                <div className="mt-3 flex justify-start">
                  <Button
                    onClick={() => void handleCreateManualSettlement()}
                    disabled={settlementSaving || Boolean(selectedManualPlanItemId)}
                    className="h-12 min-w-[136px] px-6 text-base"
                  >
                    ثبت
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <div className={cn(dashboardCard, 'flex max-h-[460px] flex-col overflow-hidden p-4 text-right')}>
            <SectionHeader title="همه تسویه‌ها" />

            <div className={cn(scrollAreaClass, 'flex-1')}>
              {settlementLoading ? (
                <div className="dashboard-panel-state flex items-center justify-center gap-2 rounded-[20px] border border-dashed border-emerald-200 bg-white/[0.65] p-6 text-sm font-bold text-muted dark:border-emerald-500/20 dark:bg-slate-900/70 dark:text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  در حال دریافت...
                </div>
              ) : allPlanItems.length === 0 ? (
                <EmptyState
                  title="پیشنهاد تسویه‌ای وجود ندارد"
                  description="اگر هزینه‌ای ثبت شده، دکمه محاسبه را بزنید."
                  icon={<Check className="h-6 w-6" />}
                />
              ) : (
                <div className="space-y-2">
                  {allPlanItems.map((item) => {
                    const isPayer = item.payer_user_id === currentUserId;
                    const isReceiver = item.receiver_user_id === currentUserId;

                    return (
                      <div key={item.id} className={cn(dashboardRow, 'p-4')}>
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                          <div className="text-right">
                            <p className="text-sm font-black text-text dark:text-slate-100">
                              {getPlanPartyName(item, 'payer', members)} ← {getPlanPartyName(item, 'receiver', members)}
                            </p>
                            <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">{getSettlementStatusLabel(item.status)}</p>
                          </div>

                          <div className="flex flex-wrap items-center justify-start gap-2">
                            <span className="rounded-[18px] border border-orange-200/80 bg-orange-50 px-3 py-2 text-sm font-black text-orange-700 dark:border-orange-500/30 dark:bg-orange-500/10 dark:text-orange-200">
                              {formatMoney(item.amount_minor)}
                            </span>

                            {isPayer && canReportPlanItem(item, settlementPlan) ? (
                              <>
                                <Button onClick={() => void handleWalletSettlementPayment(item)} disabled={settlementSaving || walletPaymentItemId === item.id} className="min-h-10 px-3 text-xs">
                                  {walletPaymentItemId === item.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <WalletCards className="h-4 w-4" />}
                                  پرداخت با کیف پول
                                </Button>
                                <Button tone="secondary" onClick={() => void handlePlanItemAction(item, 'paid')} disabled={settlementSaving || walletPaymentItemId === item.id} className="min-h-10 px-3 text-xs">
                                  دستی
                                </Button>
                              </>
                            ) : null}

                            {isReceiver && canReviewPlanItem(item) ? (
                              <>
                                <Button onClick={() => void handlePlanItemAction(item, 'confirm')} disabled={settlementSaving} className="min-h-10 px-3 text-xs">
                                  گرفتم
                                </Button>

                                <Button tone="danger" onClick={() => void handlePlanItemAction(item, 'reject')} disabled={settlementSaving} className="min-h-10 px-3 text-xs">
                                  نگرفتم
                                </Button>
                              </>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {settlements.length > 0 ? (
            <div className={cn(dashboardQuietCard, 'flex max-h-[360px] flex-col overflow-hidden p-4 text-right')}>
              <h3 className="mb-3 text-right text-sm font-black text-text dark:text-slate-100">پرداخت‌های ثبت‌شده</h3>

              <div className={cn(scrollAreaClass, 'flex-1 space-y-2')}>
                {settlements.slice(0, 20).map((settlement) => {
                  const isPayer = settlement.payer_user_id === currentUserId;
                  const isReceiver = settlement.receiver_user_id === currentUserId;

                  return (
                    <div key={settlement.id} className={cn(dashboardRow, 'p-4')}>
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="text-right">
                          <p className="text-sm font-black text-text dark:text-slate-100">
                            {getUserDisplayFromId(settlement.payer_user_id, members)} به {getUserDisplayFromId(settlement.receiver_user_id, members)}
                          </p>
                          <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">{getSettlementStatusLabel(settlement.status)}</p>
                        </div>

                        <div className="flex flex-wrap items-center justify-start gap-2">
                          <span className="rounded-[18px] border border-emerald-200 bg-white px-3 py-2 text-sm font-black text-slate-700 dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-200">
                            {formatMoney(settlement.amount_minor)}
                          </span>

                          {isReceiver && settlement.status === 'PENDING_CONFIRMATION' ? (
                            <>
                              <Button onClick={() => void handleSettlementAction(settlement, 'confirm')} className="min-h-9 px-3 text-xs">
                                گرفتم
                              </Button>

                              <Button tone="danger" onClick={() => void handleSettlementAction(settlement, 'reject')} className="min-h-9 px-3 text-xs">
                                نگرفتم
                              </Button>
                            </>
                          ) : null}

                          {isPayer && settlement.status === 'PENDING_CONFIRMATION' ? (
                            <Button tone="secondary" onClick={() => void handleSettlementAction(settlement, 'cancel')} className="min-h-9 px-3 text-xs">
                              لغو
                            </Button>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}
        </div>
      </Modal>

      <Modal
        open={Boolean(receiptPreview)}
        title={receiptPreview?.title || 'مشاهده رسید'}
        description="رسید هزینه را همین‌جا ببینید یا فایل آن را دانلود کنید."
        icon={<ReceiptText className="h-5 w-5" />}
        onClose={closeReceiptPreview}
        size="lg"
      >
        {receiptPreview ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-[20px] border border-slate-200 bg-slate-50/70 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-900/70">
              <div className="min-w-0 text-right">
                <p className="text-xs font-black text-slate-700 dark:text-slate-200">{receiptPreview.fileName || 'فایل رسید'}</p>
                <p className="mt-1 text-[11px] font-semibold text-muted dark:text-slate-400">
                  {receiptPreview.contentType || 'فایل پیوست‌شده به هزینه'}
                </p>
              </div>
              <Button tone="secondary" onClick={() => void handleDownloadReceiptPreview()} className="min-h-10 px-3 text-xs">
                <Download className="h-4 w-4" />
                دانلود رسید
              </Button>
            </div>

            <div className="overflow-hidden rounded-[24px] border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-900">
              {looksLikeImageReceipt(receiptPreview.contentType, receiptPreview.fileName || receiptPreview.sourceUrl) ? (
                <img
                  src={receiptPreview.sourceUrl}
                  alt={receiptPreview.title}
                  className="max-h-[68vh] w-full object-contain"
                />
              ) : looksLikePdfReceipt(receiptPreview.contentType, receiptPreview.fileName || receiptPreview.sourceUrl) ? (
                <iframe
                  src={receiptPreview.sourceUrl}
                  title={receiptPreview.title}
                  className="h-[68vh] w-full bg-white"
                />
              ) : (
                <div className="flex min-h-[260px] flex-col items-center justify-center gap-3 p-6 text-center">
                  <ReceiptText className="h-10 w-10 text-slate-400" />
                  <div>
                    <p className="text-sm font-black text-slate-700 dark:text-slate-200">پیش‌نمایش این نوع فایل داخل مرورگر ممکن نیست.</p>
                    <p className="mt-1 text-xs font-semibold leading-6 text-muted dark:text-slate-400">برای دیدن فایل، از دکمه دانلود استفاده کنید.</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal
        open={modal === 'settings'}
        onClose={() => setModal(null)}
        title="اطلاعات گروه"
        icon={<Settings className="h-5 w-5" />}
        size="lg"
      >
        <div className="space-y-4 text-right">
          <div className="dashboard-section-card dashboard-section-card--quiet rounded-[22px] border border-emerald-200 bg-emerald-50/55 p-4 text-right dark:border-emerald-500/20 dark:bg-slate-900/80">
            <h3 className="text-lg font-black text-text dark:text-slate-100">{group?.title || 'گروه'}</h3>
            <p className="mt-1 text-xs font-bold text-muted dark:text-slate-400">{toPersianNumber(members.length)} عضو</p>

            {group?.description ? (
              <p className="mt-3 rounded-[18px] border border-emerald-100 bg-white/80 px-3 py-3 text-sm font-semibold leading-7 text-slate-700 dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-300">
                {group.description}
              </p>
            ) : (
              <p className="mt-3 rounded-[18px] border border-dashed border-emerald-200 bg-white/70 px-3 py-3 text-sm font-semibold text-muted dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-400">
                توضیحی برای گروه ثبت نشده.
              </p>
            )}
          </div>

          <div className="dashboard-section-card dashboard-section-card--quiet rounded-[22px] border border-emerald-300/80 bg-white p-4 text-right shadow-[0_10px_24px_rgba(15,23,42,0.05)] dark:border-emerald-500/25 dark:bg-slate-900/80">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[18px] bg-emerald-600 text-white shadow-[0_10px_22px_rgba(16,185,129,0.22)] dark:bg-emerald-500">
                <UserPlus className="h-5 w-5" />
              </div>

              <div className="min-w-0 text-right">
                <h3 className="text-base font-black text-emerald-800 dark:text-emerald-200">افزودن عضو با دعوت داخل سایت</h3>
                <p className="mt-1 text-xs font-semibold leading-6 text-muted dark:text-slate-400">
                  نام کاربری را جستجو کن؛ دعوت در اعلان‌های همان کاربر نمایش داده می‌شود.
                </p>
              </div>
            </div>

            <div className="relative">
              <Search className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                value={directInviteSearch}
                onChange={(event) => setDirectInviteSearch(event.target.value)}
                disabled={!canManageGroup}
                placeholder={canManageGroup ? 'جستجو با نام کاربری...' : 'فقط مالک یا مدیر می‌تواند دعوت بفرستد'}
                className="h-12 w-full rounded-[18px] border border-emerald-200 bg-white px-4 pr-11 text-right text-sm font-semibold text-slate-700 outline-none transition focus:border-emerald-500/60 focus:ring-4 focus:ring-emerald-500/10 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400 dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-200 dark:disabled:bg-slate-900"
              />
            </div>

            {directInviteError ? (
              <p className="mt-3 rounded-[16px] border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-bold text-rose-600 dark:border-rose-500/25 dark:bg-rose-500/10 dark:text-rose-200">
                {directInviteError}
              </p>
            ) : null}

            {directInviteLoading ? (
              <div className="mt-3 flex items-center justify-center gap-2 rounded-[18px] border border-dashed border-emerald-200 bg-emerald-50/40 px-3 py-4 text-sm font-bold text-muted dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-slate-300">
                <Loader2 className="h-4 w-4 animate-spin" />
                در حال جستجو...
              </div>
            ) : directInviteSearch.trim().replace(/^@/, '').length >= 2 && directInviteResults.length === 0 && !directInviteError ? (
              <div className="mt-3 rounded-[18px] border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-center text-sm font-bold text-muted dark:border-slate-700 dark:bg-slate-950/70 dark:text-slate-400">
                کاربر قابل دعوتی پیدا نشد یا قبلاً عضو گروه است.
              </div>
            ) : directInviteResults.length > 0 ? (
              <div className="mt-3 max-h-64 space-y-2 overflow-y-auto overscroll-contain pr-1">
                {directInviteResults.map((user) => {
                  const sending = sendingDirectInviteId === user.user_id;

                  return (
                    <div
                      key={user.user_id}
                      className="flex items-center justify-between gap-3 rounded-[18px] border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-950"
                    >
                      <button
                        type="button"
                        onClick={() => void handleCreateDirectInvite(user)}
                        disabled={sending || Boolean(sendingDirectInviteId)}
                        className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-[16px] bg-emerald-600 px-3 text-xs font-black text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
                        دعوت
                      </button>

                      <div className="min-w-0 text-right">
                        <p className="truncate text-sm font-black text-text dark:text-slate-100">{user.art_name || 'کاربر'}</p>
                        <p className="mt-1 truncate text-xs font-semibold text-muted dark:text-slate-400">@{user.art_name || user.user_id}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : null}
          </div>

          <div className="dashboard-section-card dashboard-section-card--quiet rounded-[22px] border border-emerald-300/80 bg-gradient-to-l from-white via-emerald-50/70 to-emerald-50/60 p-4 text-right shadow-[inset_3px_0_0_#10B981,0_0_0_1px_rgba(16,185,129,0.10),0_10px_24px_rgba(15,23,42,0.06)] dark:border-emerald-500/25 dark:bg-slate-900/80">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[18px] bg-emerald-600 text-white shadow-[0_10px_22px_rgba(16,185,129,0.22)] dark:bg-emerald-500">
                <Link2 className="h-5 w-5" />
              </div>

              <div className="text-right">
                <h3 className="text-base font-black text-emerald-800 dark:text-emerald-200">دعوت عضو جدید</h3>
              </div>
            </div>

            {!invite ? (
              <Button onClick={handleCreateInvite} disabled={inviteLoading || !canManageGroup} className="w-full">
                <Link2 className="h-4 w-4" />
                {inviteLoading ? 'در حال ساخت...' : 'ساخت لینک دعوت'}
              </Button>
            ) : (
              <div className="space-y-3">
                <input
                  readOnly
                  dir="ltr"
                  value={inviteUrl || 'لینکی آماده نیست'}
                  className="h-11 w-full rounded-[18px] border border-emerald-200 bg-white px-3 text-right text-xs font-semibold text-slate-700 outline-none dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-200"
                />

                <div className="grid grid-cols-2 gap-2">
                  <Button tone="secondary" onClick={() => void handleCopyInvite()} disabled={!inviteUrl} className="h-10">
                    <Copy className="h-4 w-4" />
                    {copied ? 'لینک کپی شد' : 'کپی لینک'}
                  </Button>

                  <Button tone="danger" onClick={() => void handleRevokeInvite()} className="h-10">
                    <Trash2 className="h-4 w-4" />
                    لغو لینک
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className={cn(dashboardCard, 'flex max-h-[430px] flex-col overflow-hidden p-4 text-right')}>
            <SectionHeader title="اعضا" />

            <div className={cn(scrollAreaClass, 'flex-1')}>
              {membersLoading ? (
                <div className="dashboard-panel-state flex items-center justify-center gap-2 rounded-[20px] border border-dashed border-emerald-200 bg-white/[0.65] p-5 text-sm font-bold text-muted dark:border-emerald-500/20 dark:bg-slate-900/70 dark:text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  در حال دریافت اعضا...
                </div>
              ) : (
                <div className="space-y-2">
                  {members.map((member) => {
                    const memberId = getMemberId(member);
                    const userId = getMemberUserId(member);
                    const isSelf = userId === currentUserId;
                    const memberIsOwner = member.role === 'OWNER';
                    const canRemoveMember = canManageGroup && !isSelf && member.role !== 'OWNER';

                    return (
                      <div key={memberId || userId} className={cn(dashboardRow, 'p-3')}>
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex shrink-0 items-center gap-2">
                            <span
                              className={cn(
                                'inline-flex items-center gap-1 rounded-full border px-3 py-1.5 text-xs font-black',
                                memberIsOwner
                                  ? 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-500/30 dark:bg-orange-500/10 dark:text-orange-200'
                                  : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200',
                              )}
                            >
                              {getRoleLabel(member.role)}
                            </span>

                            {canRemoveMember ? (
                              <button
                                type="button"
                                onClick={() => void handleRemoveMember(member)}
                                className="flex h-9 w-9 items-center justify-center rounded-[18px] border border-rose-200 bg-rose-50 text-rose-600 hover:bg-rose-100 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200 dark:hover:bg-rose-500/15"
                                aria-label="حذف عضو"
                              >
                                <UserMinus className="h-4 w-4" />
                              </button>
                            ) : null}
                          </div>

                          <div className="flex min-w-0 items-center gap-3 text-right">
                            <div className="min-w-0 text-right">
                              <p className="truncate text-sm font-black text-text dark:text-slate-100">
                                {getMemberName(member)} {isSelf ? '(شما)' : ''}
                              </p>
                              <p className="mt-1 truncate text-xs font-semibold text-muted dark:text-slate-400">
                                {getMemberPhone(member) || 'بدون شماره'}
                              </p>
                            </div>

                            <MemberAvatar name={getMemberName(member)} owner={memberIsOwner} />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {balances.length > 0 ? (
            <div className={cn(dashboardQuietCard, 'flex max-h-[360px] flex-col overflow-hidden p-4 text-right')}>
              <SectionHeader title="حساب اعضا" />

              <div className={cn(scrollAreaClass, 'flex-1')}>
                <div className="space-y-2">
                  {balances.map((balance) => {
                    const amount = balance.net_balance_minor || 0;

                    return (
                      <div key={balance.user_id} className={cn(dashboardRow, 'flex items-center justify-between gap-3 px-3 py-3 text-sm font-bold')}>
                        <span className="truncate text-text dark:text-slate-100">{getBalanceDisplayName(balance, members)}</span>
                        <span
                          className={
                            amount < 0
                              ? 'text-rose-600 dark:text-rose-200'
                              : amount > 0
                                ? 'text-emerald-600 dark:text-emerald-200'
                                : 'text-slate-600 dark:text-slate-300'
                          }
                        >
                          {formatSignedMoney(amount)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : null}

          {canManageGroup ? (
            <div className={cn(dashboardQuietCard, 'max-h-[420px] overflow-y-auto space-y-4 p-4 text-right')}>
              <Field label="عنوان گروه">
                <input
                  dir="rtl"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  disabled={!canManageGroup}
                  className={inputClass}
                />
              </Field>

              <Field label="توضیحات">
                <textarea
                  dir="rtl"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  disabled={!canManageGroup}
                  className={textareaClass}
                />
              </Field>

              <div className="grid gap-2 sm:grid-cols-2">
                <Button onClick={handleSave} disabled={saving || !canManageGroup} className="h-12">
                  {saving ? (
                    <InlineLoader label="در حال ذخیره..." />
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      ذخیره
                    </>
                  )}
                </Button>

                {isArchived ? (
                  <Button tone="secondary" onClick={handleRestore} disabled={archiveLoading} className="h-12">
                    <RotateCcw className="h-4 w-4" />
                    فعال‌سازی
                  </Button>
                ) : (
                  <Button tone="secondary" onClick={handleArchive} disabled={archiveLoading || !canManageGroup} className="h-12">
                    <Archive className="h-4 w-4" />
                    آرشیو
                  </Button>
                )}
              </div>
            </div>
          ) : null}

          {!isOwner ? (
            <Button tone="danger" onClick={handleLeave} disabled={leaveLoading} className="h-12 w-full">
              <LogOut className="h-4 w-4" />
              {leaveLoading ? 'در حال خروج...' : 'خروج از گروه'}
            </Button>
          ) : null}
        </div>
      </Modal>

      {walletTopUpItem ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-[480px] rounded-[28px] border border-emerald-100 bg-white p-5 text-right shadow-[0_30px_90px_rgba(15,23,42,0.24)] dark:border-emerald-500/20 dark:bg-slate-950">
            <div className="flex items-start justify-between gap-3">
              <button
                type="button"
                onClick={() => setWalletTopUpItem(null)}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-500 transition hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                aria-label="بستن"
              >
                <X className="h-4 w-4" />
              </button>
              <div className="text-right">
                <h3 className="text-lg font-black text-text dark:text-slate-100">موجودی کیف پول کافی نیست</h3>
                <p className="mt-2 text-sm font-semibold leading-7 text-muted dark:text-slate-400">
                  برای پرداخت با کیف پول این بدهی، ابتدا کیف پول شارژ می‌شود و بعد همان آیتم تسویه از کیف پول پرداخت می‌شود.
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-[18px] border border-slate-100 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs font-black text-slate-500 dark:text-slate-400">موجودی فعلی</p>
                <p className="mt-2 text-base font-black text-text dark:text-slate-100">{formatMoney(walletAvailableMinor)}</p>
              </div>
              <div className="rounded-[18px] border border-emerald-100 bg-emerald-50 p-3 dark:border-emerald-500/20 dark:bg-emerald-500/10">
                <p className="text-xs font-black text-emerald-700 dark:text-emerald-200">مبلغ شارژ و پرداخت</p>
                <p className="mt-2 text-base font-black text-emerald-700 dark:text-emerald-200">{formatMoney(walletTopUpItem.amount_minor)}</p>
              </div>
            </div>

            <div className="mt-4">
              <label className="mb-2 block text-xs font-black text-slate-600 dark:text-slate-300">درگاه پرداخت</label>
              <select
                value={walletTopUpProvider}
                onChange={(event) => setWalletTopUpProvider(event.target.value as PaymentProvider)}
                className={inputClass}
              >
                <option value="FAKE">درگاه آزمایشی</option>
                <option value="ZARINPAL">زرین‌پال</option>
              </select>
            </div>

            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              <Button onClick={() => void handleTopUpAndPaySettlementItem()} disabled={walletTopUpLoading} className="h-12">
                {walletTopUpLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <WalletCards className="h-4 w-4" />}
                شارژ و پرداخت
              </Button>
              <Button tone="secondary" onClick={() => setWalletTopUpItem(null)} disabled={walletTopUpLoading} className="h-12">
                انصراف
              </Button>
            </div>

            <p className="mt-3 text-[11px] font-semibold leading-6 text-muted dark:text-slate-400">
              درگاه آزمایشی بدون خروج از سایت پرداخت را شبیه‌سازی می‌کند. زرین‌پال تو را به صفحه پرداخت منتقل می‌کند.
            </p>
          </div>
        </div>
      ) : null}

    </main>
  );
}
