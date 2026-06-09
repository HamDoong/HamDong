import { useEffect, useMemo, useState } from 'react';
import {
  Archive,
  ArrowLeft,
  Check,
  Copy,
  Crown,
  HandCoins,
  Link2,
  LockKeyhole,
  LogOut,
  Plus,
  ReceiptText,
  RefreshCw,
  RotateCcw,
  Save,
  Trash2,
  UserMinus,
  Users,
  X,
} from 'lucide-react';
import { InlineLoader, useFeedback } from '../components/feedback/FeedbackProvider';
import { isApiError } from '../lib/api';
import {
  createGroupExpense,
  deleteExpense,
  listGroupExpenses,
  type BackendExpense,
} from '../lib/expenseApi';
import {
  archiveGroup,
  createGroupInvite,
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
import { getCurrentUser, type CurrentUser } from '../lib/userApi';

interface GroupDetailPageProps {
  groupId: string;
  onBack: () => void;
  onGroupUpdated: (group: BackendGroup) => void;
  onGroupRemoved: (groupId: string) => void;
}

interface MemberMoneyStat {
  member: BackendGroupMember;
  userId: string;
  paidMinor: number;
  shareMinor: number;
  netMinor: number;
}

function getMemberId(member: BackendGroupMember) {
  return member.id || member.member_id || member.user_id || '';
}

function getMemberUserId(member: BackendGroupMember) {
  return member.user_id || member.id || member.member_id || '';
}

function getMemberName(member: BackendGroupMember) {
  return member.display_name || member.full_name || member.phone_number || member.phone || 'عضو گروه';
}

function getMemberPhone(member: BackendGroupMember) {
  return member.phone_number || member.phone || 'شماره ثبت نشده';
}

function getRoleLabel(role?: string) {
  if (role === 'OWNER') return 'مالک';
  if (role === 'ADMIN') return 'مدیر';
  if (role === 'MEMBER') return 'عضو';
  return role || 'عضو';
}

function getBackendMessage(error: unknown) {
  if (isApiError(error)) {
    if (typeof error.body === 'object' && error.body) {
      if ('detail' in error.body) return String((error.body as { detail?: unknown }).detail);
      if ('message' in error.body) return String((error.body as { message?: unknown }).message);
      return JSON.stringify(error.body);
    }

    if (error.bodyText) return error.bodyText;
  }

  return '';
}

function formatMoney(minor = 0) {
  const absValue = Math.abs(Math.round(minor));
  return `${absValue.toLocaleString('fa-IR')} تومان`;
}

function parseAmountToMinor(value: string) {
  const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
  const arabicDigits = '٠١٢٣٤٥٦٧٨٩';
  const normalized = value
    .replace(/[۰-۹]/g, (digit) => String(persianDigits.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String(arabicDigits.indexOf(digit)));
  const digits = normalized.replace(/[^0-9]/g, '');
  return Number(digits || 0);
}

function getExpenseTotal(expense: BackendExpense) {
  return (
    expense.total_amount_minor ??
    (expense.base_amount_minor || 0) +
      (expense.tax_amount_minor || 0) +
      (expense.service_fee_amount_minor || 0)
  );
}

function getParticipantShare(participant: NonNullable<BackendExpense['participants']>[number]) {
  return (
    participant.total_share_minor ??
    (participant.base_share_minor || 0) +
      (participant.tax_share_minor || 0) +
      (participant.service_fee_share_minor || 0)
  );
}

function toPersianDate(value?: string) {
  if (!value) return 'بدون تاریخ';

  try {
    return new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function getCurrentUserId(user: CurrentUser | null) {
  return user?.id ? String(user.id) : '';
}

function getUserDisplayFromId(userId: string, members: BackendGroupMember[]) {
  const member = members.find((item) => getMemberUserId(item) === userId);
  return member ? getMemberName(member) : 'عضو گروه';
}

function buildExpenseStats(expenses: BackendExpense[], members: BackendGroupMember[]) {
  const memberMap = new Map<string, MemberMoneyStat>();

  members.forEach((member) => {
    const userId = getMemberUserId(member);
    if (!userId) return;

    memberMap.set(userId, {
      member,
      userId,
      paidMinor: 0,
      shareMinor: 0,
      netMinor: 0,
    });
  });

  expenses
    .filter((expense) => expense.status !== 'DELETED' && expense.status !== 'CANCELLED')
    .forEach((expense) => {
      const total = getExpenseTotal(expense);
      const payerId = expense.payer_user_id;

      if (payerId && memberMap.has(payerId)) {
        memberMap.get(payerId)!.paidMinor += total;
      }

      if (expense.participants?.length) {
        expense.participants.forEach((participant) => {
          const stat = memberMap.get(participant.user_id);
          if (!stat) return;
          stat.shareMinor += getParticipantShare(participant);
        });
      } else if (members.length > 0) {
        const equalShare = Math.round(total / members.length);
        members.forEach((member) => {
          const stat = memberMap.get(getMemberUserId(member));
          if (stat) stat.shareMinor += equalShare;
        });
      }
    });

  return Array.from(memberMap.values()).map((stat) => ({
    ...stat,
    netMinor: stat.paidMinor - stat.shareMinor,
  }));
}

export function GroupDetailPage({
  groupId,
  onBack,
  onGroupUpdated,
  onGroupRemoved,
}: GroupDetailPageProps) {
  const { notify, confirm } = useFeedback();

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [group, setGroup] = useState<BackendGroup | null>(null);
  const [members, setMembers] = useState<BackendGroupMember[]>([]);
  const [expenses, setExpenses] = useState<BackendExpense[]>([]);
  const [invite, setInvite] = useState<CreatedInvite | null>(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [groupType, setGroupType] = useState<BackendGroupType>('GENERAL');

  const [expenseTitle, setExpenseTitle] = useState('');
  const [expenseAmount, setExpenseAmount] = useState('');
  const [expenseDescription, setExpenseDescription] = useState('');
  const [expensePayerId, setExpensePayerId] = useState('');
  const [expenseParticipantIds, setExpenseParticipantIds] = useState<string[]>([]);

  const [loading, setLoading] = useState(true);
  const [membersLoading, setMembersLoading] = useState(true);
  const [expensesLoading, setExpensesLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [expenseSaving, setExpenseSaving] = useState(false);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [leaveLoading, setLeaveLoading] = useState(false);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inviteUrl = useMemo(() => {
    return invite ? getInviteUrl(invite) : '';
  }, [invite]);

  const isArchived = group?.status === 'ARCHIVED';
  const isOwner = group?.my_role === 'OWNER';
  const currentUserId = getCurrentUserId(currentUser);

  const moneyStats = useMemo(() => buildExpenseStats(expenses, members), [expenses, members]);
  const activeExpenses = expenses.filter((expense) => expense.status !== 'DELETED' && expense.status !== 'CANCELLED');
  const totalExpenseMinor = activeExpenses.reduce((sum, expense) => sum + getExpenseTotal(expense), 0);

  async function loadGroup() {
    try {
      setLoading(true);
      setError(null);

      const backendGroup = await getGroupDetail(groupId);

      setGroup(backendGroup);
      setTitle(backendGroup.title || '');
      setDescription(backendGroup.description || '');
      setGroupType(backendGroup.group_type || 'GENERAL');
      onGroupUpdated(backendGroup);
    } catch (err) {
      console.error(err);
      setError('خطا در دریافت جزئیات گروه');
    } finally {
      setLoading(false);
    }
  }

  async function loadMembers() {
    try {
      setMembersLoading(true);
      const backendMembers = await getGroupMembers(groupId);
      setMembers(backendMembers);

      const ids = backendMembers.map(getMemberUserId).filter(Boolean);
      setExpenseParticipantIds(ids);

      const me = await getCurrentUser().catch(() => null);
      setCurrentUser(me);

      const defaultPayer = me?.id ? String(me.id) : ids[0] || '';
      setExpensePayerId(defaultPayer);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'دریافت اعضا ناموفق بود',
        description: getBackendMessage(err) || 'Network و Console را بررسی کن.',
      });
    } finally {
      setMembersLoading(false);
    }
  }

  async function loadExpenses() {
    try {
      setExpensesLoading(true);
      const backendExpenses = await listGroupExpenses(groupId, { page_size: 100 });
      setExpenses(backendExpenses);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'دریافت هزینه‌ها ناموفق بود',
        description: getBackendMessage(err) || 'Network و Console را بررسی کن.',
      });
    } finally {
      setExpensesLoading(false);
    }
  }

  useEffect(() => {
    loadGroup();
    loadMembers();
    loadExpenses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  async function handleSave() {
    try {
      setSaving(true);

      const updatedGroup = await updateGroup(groupId, {
        title: title.trim(),
        description: description.trim(),
        group_type: groupType,
      });

      setGroup(updatedGroup);
      onGroupUpdated(updatedGroup);
      notify({
        type: 'success',
        title: 'تغییرات ذخیره شد',
        description: 'اطلاعات گروه با موفقیت بروزرسانی شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'ویرایش گروه ناموفق بود',
        description: getBackendMessage(err) || 'Network و Console را بررسی کن.',
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleArchive() {
    if (isArchived) {
      notify({
        type: 'info',
        title: 'این گروه قبلاً آرشیو شده',
        description: 'برای فعال‌کردن دوباره از دکمه بازگردانی استفاده کن.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'آرشیو گروه؟',
      description: 'بعد از آرشیو، گروه از لیست گروه‌های فعال حذف می‌شود و فقط در بخش گروه‌های آرشیو شده نمایش داده می‌شود.',
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
        description: 'این گروه از لیست گروه‌های فعال خارج شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'آرشیو گروه ناموفق بود',
        description: getBackendMessage(err) || 'Network و Console را بررسی کن.',
      });
    } finally {
      setArchiveLoading(false);
    }
  }

  async function handleRestore() {
    if (!isArchived) {
      notify({
        type: 'info',
        title: 'این گروه فعال است',
        description: 'نیازی به بازگردانی نیست.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'بازگردانی گروه؟',
      description: 'اگر بک‌اند تغییر وضعیت گروه را پشتیبانی کند، این گروه دوباره در لیست گروه‌های فعال نمایش داده می‌شود.',
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
        description: 'این گروه حالا در لیست گروه‌های فعال نمایش داده می‌شود.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'بازگردانی گروه ناموفق بود',
        description: getBackendMessage(err) || 'احتمالاً بک‌اند هنوز endpoint یا فیلد status برای فعال‌سازی دوباره ندارد.',
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
        description: 'این محدودیت از سمت بک‌اند است. برای مالک، فعلاً آرشیو گروه یا انتقال مالکیت لازم است.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'خروج از گروه؟',
      description: 'بعد از خروج، این گروه از لیست تو حذف می‌شود.',
      confirmText: 'خارج شو',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      setLeaveLoading(true);
      await leaveGroup(groupId);
      notify({ type: 'success', title: 'از گروه خارج شدی', description: 'گروه از لیست تو حذف شد.' });
      onGroupRemoved(groupId);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'خروج از گروه ناموفق بود',
        description: getBackendMessage(err) || 'اگر مالک گروه هستی، بک‌اند اجازه خروج مالک را نمی‌دهد.',
      });
    } finally {
      setLeaveLoading(false);
    }
  }

  async function handleRemoveMember(member: BackendGroupMember) {
    const memberId = getMemberId(member);

    if (!memberId) {
      notify({ type: 'error', title: 'شناسه عضو پیدا نشد', description: 'پاسخ بک‌اند برای member id کافی نیست.' });
      return;
    }

    const confirmed = await confirm({
      title: 'حذف عضو؟',
      description: `${getMemberName(member)} از گروه حذف شود؟`,
      confirmText: 'حذف کن',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      await removeGroupMember(groupId, memberId);
      setMembers((prev) => prev.filter((item) => getMemberId(item) !== memberId));
      notify({ type: 'success', title: 'عضو حذف شد', description: 'این عضو دیگر در گروه فعال نیست.' });
    } catch (err) {
      console.error(err);
      notify({ type: 'error', title: 'حذف عضو ناموفق بود', description: getBackendMessage(err) || 'Network و Console را بررسی کن.' });
    }
  }

  function toggleExpenseParticipant(userId: string) {
    setExpenseParticipantIds((prev) =>
      prev.includes(userId) ? prev.filter((item) => item !== userId) : [...prev, userId],
    );
  }

  async function handleCreateExpense() {
    const amountMinor = parseAmountToMinor(expenseAmount);

    if (!expenseTitle.trim()) {
      notify({ type: 'error', title: 'عنوان هزینه لازم است', description: 'برای هزینه یک عنوان وارد کن.' });
      return;
    }

    if (!amountMinor || amountMinor <= 0) {
      notify({ type: 'error', title: 'مبلغ معتبر نیست', description: 'مبلغ هزینه را به عدد وارد کن.' });
      return;
    }

    if (!expensePayerId) {
      notify({ type: 'error', title: 'پرداخت‌کننده مشخص نیست', description: 'یک عضو را به عنوان پرداخت‌کننده انتخاب کن.' });
      return;
    }

    if (expenseParticipantIds.length === 0) {
      notify({ type: 'error', title: 'اعضای تقسیم مشخص نیستند', description: 'حداقل یک عضو را برای تقسیم هزینه انتخاب کن.' });
      return;
    }

    try {
      setExpenseSaving(true);

      await createGroupExpense(groupId, {
        title: expenseTitle,
        description: expenseDescription,
        payer_user_id: expensePayerId,
        base_amount_minor: amountMinor,
        currency: 'IRR',
        split_method: 'EQUAL',
        participant_user_ids: expenseParticipantIds,
      });

      setExpenseTitle('');
      setExpenseAmount('');
      setExpenseDescription('');
      await loadExpenses();
      notify({
        type: 'success',
        title: 'هزینه ثبت شد',
        description: 'مبلغ بین اعضای انتخاب‌شده تقسیم شد و در گزارش گروه نمایش داده می‌شود.',
      });
    } catch (err) {
      console.error(err);
      notify({ type: 'error', title: 'ثبت هزینه ناموفق بود', description: getBackendMessage(err) || 'Network و Console را بررسی کن.' });
    } finally {
      setExpenseSaving(false);
    }
  }

  async function handleDeleteExpense(expense: BackendExpense) {
    const confirmed = await confirm({
      title: 'حذف هزینه؟',
      description: `هزینه «${expense.title}» حذف شود؟`,
      confirmText: 'حذف کن',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      await deleteExpense(expense.id);
      await loadExpenses();
      notify({ type: 'success', title: 'هزینه حذف شد', description: 'هزینه از گزارش گروه حذف شد.' });
    } catch (err) {
      console.error(err);
      notify({ type: 'error', title: 'حذف هزینه ناموفق بود', description: getBackendMessage(err) || 'Network و Console را بررسی کن.' });
    }
  }

  function handlePayClick(stat: MemberMoneyStat) {
    notify({
      type: 'info',
      title: 'پرداخت هنوز وصل نشده',
      description: `${formatMoney(Math.abs(stat.netMinor))} بدهی برای پرداخت آماده است. بعد از آماده شدن بک‌اند پرداخت، همین دکمه را وصل می‌کنیم.`,
    });
  }

  async function handleCreateInvite() {
    try {
      setInviteLoading(true);
      const createdInvite = await createGroupInvite(groupId, { expires_in_hours: 72, max_uses: 10 });
      setInvite(createdInvite);
      notify({ type: 'success', title: 'لینک دعوت ساخته شد', description: 'لینک را کپی کن و برای کاربر دیگر بفرست.' });
    } catch (err) {
      console.error(err);
      notify({ type: 'error', title: 'ساخت لینک دعوت ناموفق بود', description: getBackendMessage(err) || 'Network و Console را بررسی کن.' });
    } finally {
      setInviteLoading(false);
    }
  }

  async function handleCopyInvite() {
    if (!inviteUrl) {
      notify({ type: 'error', title: 'لینک دعوت موجود نیست', description: 'پاسخ بک‌اند token یا invite_url نداشت.' });
      return;
    }

    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
      notify({ type: 'success', title: 'لینک کپی شد', description: 'حالا می‌تونی لینک را برای کاربر دیگر بفرستی.' });
    } catch {
      setCopied(false);
      notify({ type: 'error', title: 'کپی لینک ناموفق بود', description: 'دسترسی clipboard مرورگر فعال نیست.' });
    }
  }

  async function handleRevokeInvite() {
    if (!invite) return;
    const inviteId = getInviteId(invite);

    if (!inviteId) {
      notify({ type: 'error', title: 'شناسه دعوت در پاسخ بک‌اند نیست', description: 'برای لغو دعوت، بک‌اند باید id یا invite_id برگرداند.' });
      return;
    }

    const confirmed = await confirm({
      title: 'لغو لینک دعوت؟',
      description: 'بعد از لغو، این لینک دیگر برای عضویت قابل استفاده نیست.',
      confirmText: 'لغو کن',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      await revokeGroupInvite(groupId, inviteId);
      setInvite(null);
      notify({ type: 'success', title: 'لینک دعوت لغو شد', description: 'این دعوت دیگر قابل استفاده نیست.' });
    } catch (err) {
      console.error(err);
      notify({ type: 'error', title: 'لغو دعوت ناموفق بود', description: getBackendMessage(err) || 'Network و Console را بررسی کن.' });
    }
  }

  return (
    <main className="px-4 py-6 sm:px-6 xl:px-8">
      <div className="mx-auto max-w-[1180px] space-y-6">
        <div className="flex flex-col gap-4 rounded-3xl border border-border bg-white p-6 shadow-soft lg:flex-row lg:items-center lg:justify-between">
          <div className="text-right">
            <button type="button" onClick={onBack} className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-slate-600 transition hover:text-text">
              <ArrowLeft className="h-4.5 w-4.5" />
              بازگشت به گروه‌ها
            </button>
            <h1 className="text-[30px] font-extrabold tracking-[-0.03em] text-text">{loading ? 'در حال دریافت گروه...' : group?.title || 'جزئیات گروه'}</h1>
            <p className="mt-2 text-sm leading-7 text-muted">مدیریت اطلاعات گروه، اعضا، دعوت‌ها و تقسیم هزینه‌ها</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={() => { loadGroup(); loadMembers(); loadExpenses(); }} className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
              <RefreshCw className="h-4 w-4" /> بروزرسانی
            </button>

            {isArchived ? (
              <button type="button" onClick={handleRestore} disabled={archiveLoading} className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100 disabled:opacity-60">
                {archiveLoading ? <InlineLoader label="در حال فعال‌سازی..." /> : <><RotateCcw className="h-4 w-4" /> بازگردانی</>}
              </button>
            ) : (
              <button type="button" onClick={handleArchive} disabled={archiveLoading} className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-amber-100 bg-amber-50 px-4 text-sm font-semibold text-amber-700 transition hover:bg-amber-100 disabled:opacity-60">
                {archiveLoading ? <InlineLoader label="در حال آرشیو..." /> : <><Archive className="h-4 w-4" /> آرشیو</>}
              </button>
            )}

            <button type="button" onClick={handleLeave} disabled={leaveLoading || isOwner} title={isOwner ? 'مالک گروه نمی‌تواند از گروه خارج شود' : undefined} className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-rose-100 bg-rose-50 px-4 text-sm font-semibold text-rose-600 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-55">
              {isOwner ? <LockKeyhole className="h-4 w-4" /> : <LogOut className="h-4 w-4" />}
              {leaveLoading ? 'در حال خروج...' : 'خروج'}
            </button>
          </div>
        </div>

        {error ? <div className="rounded-3xl border border-rose-100 bg-rose-50 p-5 text-center text-sm font-semibold text-rose-600">{error}</div> : null}

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <section className="space-y-6">
            <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
              <div className="mb-6 flex items-center justify-between">
                <div className="text-right"><h2 className="text-2xl font-bold text-text">ثبت هزینه و تقسیم مبلغ</h2><p className="mt-1 text-sm text-muted">هزینه را ثبت کن تا سهم هر عضو و بدهکاری/طلبکاری در همین صفحه محاسبه شود.</p></div>
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600"><ReceiptText className="h-5 w-5" /></div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div><label className="mb-2 block text-sm font-semibold text-text">عنوان هزینه</label><input dir="rtl" value={expenseTitle} onChange={(event) => setExpenseTitle(event.target.value)} placeholder="مثلاً شام، تاکسی، خرید..." className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10" /></div>
                <div><label className="mb-2 block text-sm font-semibold text-text">مبلغ</label><input dir="rtl" value={expenseAmount} onChange={(event) => setExpenseAmount(event.target.value)} placeholder="مثلاً 250000" className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10" /></div>
                <div><label className="mb-2 block text-sm font-semibold text-text">پرداخت‌کننده</label><select value={expensePayerId} onChange={(event) => setExpensePayerId(event.target.value)} className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10">{members.map((member) => { const userId = getMemberUserId(member); return <option key={userId} value={userId}>{getMemberName(member)}</option>; })}</select></div>
                <div><label className="mb-2 block text-sm font-semibold text-text">روش تقسیم</label><div className="flex h-12 w-full items-center justify-between rounded-2xl border border-emerald-100 bg-emerald-50 px-4 text-sm font-semibold text-emerald-700"><span>تقسیم مساوی</span><span className="text-xs font-medium text-emerald-600">بین اعضای انتخاب‌شده</span></div></div>
              </div>
              <div className="mt-4"><label className="mb-2 block text-sm font-semibold text-text">توضیح هزینه</label><textarea dir="rtl" value={expenseDescription} onChange={(event) => setExpenseDescription(event.target.value)} placeholder="توضیح اختیاری..." className="min-h-[84px] w-full resize-none rounded-2xl border border-border bg-white px-4 py-3 text-sm leading-7 text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10" /></div>
              <div className="mt-4 rounded-2xl border border-border bg-slate-50 p-4"><div className="mb-3 text-right text-sm font-semibold text-text">این هزینه بین چه کسانی تقسیم شود؟</div><div className="grid gap-2 sm:grid-cols-2">{members.map((member) => { const userId = getMemberUserId(member); const selected = expenseParticipantIds.includes(userId); return <button key={userId} type="button" onClick={() => toggleExpenseParticipant(userId)} className={["flex items-center justify-between rounded-2xl border px-3 py-3 text-right text-sm transition", selected ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-border bg-white text-slate-600 hover:bg-slate-50'].join(' ')}><span className="font-semibold">{getMemberName(member)}</span><span className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-emerald-600">{selected ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}</span></button>; })}</div></div>
              <div className="mt-5 flex justify-end"><button type="button" onClick={handleCreateExpense} disabled={expenseSaving || members.length === 0} className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60">{expenseSaving ? <InlineLoader label="در حال ثبت..." /> : <><Plus className="h-4.5 w-4.5" /> ثبت و تقسیم هزینه</>}</button></div>
            </div>

            <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
              <div className="mb-6 flex items-center justify-between">
                <div className="text-right">
                  <h2 className="text-2xl font-bold text-text">وضعیت اعضا</h2>
                  <p className="mt-1 text-sm text-muted">خلاصه ساده خرج، سهم و بدهی هر عضو.</p>
                </div>
                <div className="rounded-2xl bg-emerald-50 px-3 py-2 text-sm font-bold text-emerald-700">
                  {formatMoney(totalExpenseMinor)} هزینه کل
                </div>
              </div>
              {expensesLoading || membersLoading ? (
                <div className="rounded-2xl border border-border bg-slate-50 p-5 text-center text-sm text-muted">در حال محاسبه سهم اعضا...</div>
              ) : null}
              {!expensesLoading && moneyStats.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted">
                  هنوز هزینه‌ای ثبت نشده است. بعد از ثبت هزینه، وضعیت هر عضو اینجا نمایش داده می‌شود.
                </div>
              ) : null}
              <div className="overflow-hidden rounded-2xl border border-border">
                {moneyStats.map((stat, index) => {
                  const isCurrentUser = stat.userId === currentUserId;
                  const owes = stat.netMinor < 0;
                  const receives = stat.netMinor > 0;
                  const statusText = owes
                    ? `بدهکار ${formatMoney(Math.abs(stat.netMinor))}`
                    : receives
                      ? `طلبکار ${formatMoney(stat.netMinor)}`
                      : 'تسویه';

                  return (
                    <div
                      key={stat.userId}
                      className={[
                        'flex flex-col gap-4 bg-white px-4 py-4 lg:flex-row lg:items-center lg:justify-between',
                        index !== moneyStats.length - 1 ? 'border-b border-border/80' : '',
                      ].join(' ')}
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-300 to-teal-600 text-sm font-bold text-white">
                          {getMemberName(stat.member).slice(0, 1)}
                        </div>
                        <div className="min-w-0 text-right">
                          <div className="truncate text-base font-bold text-text">
                            {getMemberName(stat.member)} {isCurrentUser ? '(شما)' : ''}
                          </div>
                          <div className="mt-1 text-sm text-muted">{getMemberPhone(stat.member)}</div>
                        </div>
                      </div>

                      <div className="grid gap-3 text-right sm:grid-cols-3 lg:min-w-[430px]">
                        <div>
                          <div className="text-xs text-muted">خرج کرده</div>
                          <div className="mt-1 font-bold text-emerald-600">{formatMoney(stat.paidMinor)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted">سهم</div>
                          <div className="mt-1 font-bold text-text">{formatMoney(stat.shareMinor)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted">وضعیت</div>
                          <div className={["mt-1 font-bold", owes ? 'text-rose-600' : receives ? 'text-emerald-600' : 'text-slate-700'].join(' ')}>{statusText}</div>
                        </div>
                      </div>

                      {isCurrentUser && owes ? (
                        <button
                          type="button"
                          onClick={() => handlePayClick(stat)}
                          className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-2xl bg-emerald-600 px-4 text-sm font-semibold text-white transition hover:bg-emerald-700"
                        >
                          <HandCoins className="h-4 w-4" />
                          پرداخت بدهی
                        </button>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
              <div className="mb-6 flex items-center justify-between"><div className="text-right"><h2 className="text-2xl font-bold text-text">هزینه‌های ثبت‌شده</h2><p className="mt-1 text-sm text-muted">جزئیات خرج‌های گروه و حذف هزینه‌های اشتباه.</p></div><div className="rounded-2xl bg-emerald-50 px-3 py-2 text-sm font-bold text-emerald-700">{activeExpenses.length.toLocaleString('fa-IR')} هزینه</div></div>
              {expensesLoading ? <div className="rounded-2xl border border-border bg-slate-50 p-5 text-center text-sm text-muted">در حال دریافت هزینه‌ها...</div> : null}
              {!expensesLoading && activeExpenses.length === 0 ? <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted">هنوز هزینه‌ای در این گروه ثبت نشده است.</div> : null}
              <div className="overflow-hidden rounded-2xl border border-border">{activeExpenses.map((expense, index, list) => <div key={expense.id} className={["flex flex-col gap-4 bg-white px-4 py-4 sm:flex-row sm:items-center sm:justify-between", index !== list.length - 1 ? 'border-b border-border/80' : ''].join(' ')}><div className="flex min-w-0 items-center gap-3"><div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600"><ReceiptText className="h-5 w-5" /></div><div className="min-w-0 text-right"><div className="truncate text-base font-bold text-text">{expense.title}</div><div className="mt-1 text-sm text-muted">پرداخت‌کننده: {getUserDisplayFromId(expense.payer_user_id, members)} • {toPersianDate(expense.expense_date || expense.created_at)}</div></div></div><div className="flex items-center justify-between gap-3 sm:justify-end"><div className="text-left"><div className="text-lg font-extrabold text-emerald-600">{formatMoney(getExpenseTotal(expense))}</div><div className="mt-1 text-xs text-muted">تقسیم مساوی</div></div><button type="button" onClick={() => handleDeleteExpense(expense)} className="inline-flex h-10 items-center justify-center gap-1.5 rounded-xl bg-rose-50 px-3 text-xs font-semibold text-rose-600 transition hover:bg-rose-100"><X className="h-4 w-4" />حذف</button></div></div>)}</div>
            </div>

            <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
              <div className="mb-6 flex items-center justify-between"><div className="text-right"><h2 className="text-2xl font-bold text-text">اعضای گروه</h2><p className="mt-1 text-sm text-muted">اعضای فعلی گروه را مشاهده و مدیریت کن.</p></div><div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600"><Users className="h-5 w-5" /></div></div>
              {membersLoading ? <div className="rounded-2xl border border-border bg-slate-50 p-5 text-center text-sm text-muted">در حال دریافت اعضا...</div> : null}
              {!membersLoading && members.length === 0 ? <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted">هنوز عضوی برای نمایش وجود ندارد.</div> : null}
              <div className="space-y-3">{members.map((member) => { const memberId = getMemberId(member); return <div key={memberId} className="flex flex-col gap-4 rounded-2xl border border-border bg-white px-4 py-4 sm:flex-row sm:items-center sm:justify-between"><div className="flex min-w-0 items-center gap-3"><div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-300 to-teal-600 text-sm font-bold text-white">{getMemberName(member).slice(0, 1)}</div><div className="min-w-0 text-right"><div className="truncate text-base font-bold text-text">{getMemberName(member)}</div><div className="mt-1 text-sm text-muted">{getMemberPhone(member)}</div></div></div><div className="flex items-center justify-between gap-3 sm:justify-end"><span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700"><Crown className="h-3.5 w-3.5" />{getRoleLabel(member.role)}</span><button type="button" onClick={() => handleRemoveMember(member)} className="inline-flex h-9 items-center justify-center gap-1.5 rounded-xl bg-rose-50 px-3 text-xs font-semibold text-rose-600 transition hover:bg-rose-100"><UserMinus className="h-3.5 w-3.5" />حذف</button></div></div>; })}</div>
            </div>
          </section>

          <aside className="space-y-6">
              <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
                <div className="mb-6 flex items-center justify-between">
                  <div className="text-right"><h2 className="text-2xl font-bold text-text">تنظیمات گروه</h2><p className="mt-1 text-sm text-muted">عنوان، توضیح و نوع گروه را ویرایش کن.</p></div>
                  <div className={["rounded-2xl px-3 py-2 text-sm font-bold", isArchived ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'].join(' ')}>{isArchived ? 'آرشیو شده' : 'فعال'}</div>
                </div>
                <div className="grid gap-5 md:grid-cols-2">
                  <div><label className="mb-2 block text-sm font-semibold text-text">عنوان گروه</label><input dir="rtl" value={title} onChange={(event) => setTitle(event.target.value)} className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10" /></div>
                  <div><label className="mb-2 block text-sm font-semibold text-text">نوع گروه</label><select value={groupType} onChange={(event) => setGroupType(event.target.value as BackendGroupType)} className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"><option value="GENERAL">عمومی</option><option value="EVENT">رویداد</option></select></div>
                </div>
                <div className="mt-5"><label className="mb-2 block text-sm font-semibold text-text">توضیحات</label><textarea dir="rtl" value={description} onChange={(event) => setDescription(event.target.value)} className="min-h-[120px] w-full resize-none rounded-2xl border border-border bg-white px-4 py-3 text-sm leading-7 text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10" /></div>
                <div className="mt-5 flex justify-end"><button type="button" onClick={handleSave} disabled={saving} className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60">{saving ? <InlineLoader label="در حال ذخیره..." /> : <><Save className="h-4.5 w-4.5" /> ذخیره تغییرات</>}</button></div>
              </div>


            <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
              <div className="mb-5 text-right"><h2 className="text-xl font-bold text-text">دعوت اعضا</h2><p className="mt-1 text-sm leading-7 text-muted">لینک دعوت بساز و برای اعضای جدید بفرست.</p></div>
              {!invite ? <button type="button" onClick={handleCreateInvite} disabled={inviteLoading} className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-5 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(0,168,107,0.18)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"><Link2 className="h-4.5 w-4.5" />{inviteLoading ? 'در حال ساخت...' : 'ساخت لینک دعوت'}</button> : <div className="space-y-3"><div className="relative"><Link2 className="pointer-events-none absolute right-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" /><input readOnly dir="ltr" value={inviteUrl || 'لینک در پاسخ بک‌اند وجود ندارد'} className="h-12 w-full rounded-2xl border border-border bg-slate-50 pr-11 pl-4 text-left text-sm text-slate-700 outline-none" /></div><div className="grid grid-cols-2 gap-3"><button type="button" onClick={handleCopyInvite} disabled={!inviteUrl} className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"><Copy className="h-4 w-4" />{copied ? 'کپی شد' : 'کپی'}</button><button type="button" onClick={handleRevokeInvite} className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-rose-100 bg-rose-50 px-4 text-sm font-semibold text-rose-600 transition hover:bg-rose-100"><Trash2 className="h-4 w-4" />لغو</button></div>{invite.expires_at ? <p className="text-center text-xs text-muted">اعتبار تا: {invite.expires_at}</p> : null}</div>}
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
