import { useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Edit3,
  Eye,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  TrendingDown,
  TrendingUp,
  Users,
  X,
} from 'lucide-react';
import {
  createGroupExpense,
  deleteExpense,
  getExpenseDetail,
  listGroupExpenses,
  updateExpense,
  type BackendExpense,
  type ExpenseParticipant,
  type ExpenseSplitMethod,
} from '../lib/expenseApi';
import {
  getGroupMembers,
  getMyGroups,
  type BackendGroup,
  type BackendGroupMember,
} from '../lib/groupApi';
import { getCurrentUser } from '../lib/userApi';

type ActivityFilter = 'all' | 'received' | 'paid' | 'settled';
type ModalMode = 'create' | 'edit';

type UiExpense = BackendExpense & {
  groupTitle?: string;
};

interface ExpenseFormState {
  groupId: string;
  title: string;
  description: string;
  payerUserId: string;
  baseAmountMinor: string;
  currency: string;
  splitMethod: ExpenseSplitMethod;
  participantUserIds: string[];
  customShares: Record<string, string>;
  taxAmountMinor: string;
  serviceFeeAmountMinor: string;
  expenseDate: string;
  receiptUrl: string;
}

interface ToastState {
  tone: 'success' | 'error' | 'info';
  title: string;
  message?: string;
}

const defaultFormState: ExpenseFormState = {
  groupId: '',
  title: '',
  description: '',
  payerUserId: '',
  baseAmountMinor: '',
  currency: 'IRR',
  splitMethod: 'EQUAL',
  participantUserIds: [],
  customShares: {},
  taxAmountMinor: '0',
  serviceFeeAmountMinor: '0',
  expenseDate: '',
  receiptUrl: '',
};

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function toPersianNumber(value: string | number) {
  return String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);
}

function toEnglishDigits(value: string) {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)));
}

function parseAmount(value: string) {
  const normalized = toEnglishDigits(value).replace(/[,\s]/g, '');
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? Math.max(0, Math.round(parsed)) : 0;
}

function formatMoney(amount = 0) {
  return `${toPersianNumber(Math.abs(amount).toLocaleString('en-US'))} تومان`;
}

function formatSignedMoney(amount: number) {
  const sign = amount >= 0 ? '+' : '-';
  return `${sign}${formatMoney(amount)}`;
}

function formatTime(value?: string) {
  if (!value) return '—';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return '—';

  return toPersianNumber(
    date.toLocaleTimeString('fa-IR', {
      hour: '2-digit',
      minute: '2-digit',
    }),
  );
}

function formatDate(value?: string) {
  if (!value) return 'بدون تاریخ';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return 'بدون تاریخ';

  return date.toLocaleDateString('fa-IR', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function getExpenseTotal(expense: BackendExpense) {
  return expense.total_amount_minor ?? expense.base_amount_minor ?? 0;
}

function getMemberName(member: BackendGroupMember) {
  return (
    member.art_name ||
    member.username ||
    member.display_name ||
    member.full_name ||
    member.phone_number ||
    member.phone ||
    'عضو گروه'
  );
}

function getMemberUserId(member: BackendGroupMember) {
  return member.user_id || member.id || member.member_id || '';
}

function getParticipantName(participant?: ExpenseParticipant) {
  return participant?.display_name_snapshot || participant?.phone_number || 'عضو گروه';
}

function getGroupTitle(group?: BackendGroup) {
  return group?.title || 'گروه بدون عنوان';
}

function isActiveGroup(group: BackendGroup) {
  return String(group.status || 'ACTIVE').toUpperCase() !== 'ARCHIVED';
}

function normalizeText(value: string) {
  return value.trim().replace(/\s+/g, ' ');
}

function matchesGroupSelection(group: BackendGroup, selection: string) {
  if (selection === 'all') return true;

  const normalizedSelection = normalizeText(selection);

  return (
    String(group.id) === selection ||
    normalizeText(group.title || '') === normalizedSelection
  );
}

function getSelectedGroupValue(group: BackendGroup) {
  return String(group.id);
}

function getApiErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return 'Unknown API error';
}

function getExpenseKind(expense: BackendExpense, currentUserId?: string | null) {
  if (!currentUserId) return 'paid';

  if (expense.payer_user_id === currentUserId) return 'paid';

  const isParticipant = expense.participants?.some(
    (participant) => participant.user_id === currentUserId && participant.is_included !== false,
  );

  return isParticipant ? 'received' : 'paid';
}

function getExpenseKindLabel(kind: ReturnType<typeof getExpenseKind>) {
  return kind === 'paid' ? 'پرداخت من' : 'سهم من';
}

function getSplitMethodLabel(method?: string) {
  if (method === 'CUSTOM') return 'تقسیم سفارشی';
  if (method === 'EQUAL') return 'تقسیم مساوی';
  return 'روش تقسیم نامشخص';
}

function getExpenseStatusLabel(status?: string) {
  const normalizedStatus = String(status || 'ACTIVE').toUpperCase();

  if (normalizedStatus.includes('SETTLED') || normalizedStatus.includes('CLOSED')) return 'تسویه‌شده';
  if (normalizedStatus.includes('CANCELLED')) return 'لغوشده';
  if (normalizedStatus.includes('DELETED')) return 'حذف‌شده';
  return 'فعال';
}

function getExpenseStatusClassName(status?: string) {
  const normalizedStatus = String(status || 'ACTIVE').toUpperCase();

  if (normalizedStatus.includes('SETTLED') || normalizedStatus.includes('CLOSED')) {
    return 'border-emerald-100 bg-emerald-50 text-emerald-700';
  }

  if (normalizedStatus.includes('CANCELLED') || normalizedStatus.includes('DELETED')) {
    return 'border-rose-100 bg-rose-50 text-rose-600';
  }

  return 'border-slate-200 bg-slate-50 text-slate-600';
}

function getParticipantCountLabel(expense: BackendExpense) {
  const count = expense.participants?.filter((participant) => participant.is_included !== false).length || 0;

  if (count === 0) return 'بدون شرکت‌کننده';
  return `${toPersianNumber(count)} نفر`;
}

function groupExpensesByDate(expenses: UiExpense[]) {
  return expenses.reduce<Record<string, UiExpense[]>>((acc, expense) => {
    const key = formatDate(expense.expense_date || expense.created_at);
    acc[key] = acc[key] || [];
    acc[key].push(expense);
    return acc;
  }, {});
}

function dateInputToIso(value: string) {
  if (!value) return undefined;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
}

function isoToDateTimeLocal(value?: string) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const offsetMs = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function makeShareInputs(participants?: ExpenseParticipant[]) {
  return (participants || []).reduce<Record<string, string>>((acc, participant) => {
    acc[participant.user_id] = String(participant.base_share_minor ?? participant.total_share_minor ?? 0);
    return acc;
  }, {});
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="rounded-[24px] border border-dashed border-emerald-200 bg-emerald-50/40 p-8 text-center sm:p-10">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-[18px] bg-white text-emerald-600 shadow-sm">
        <ClipboardList className="h-7 w-7" />
      </div>
      <h2 className="text-xl font-bold text-text">هنوز فعالیتی ثبت نشده</h2>
      <p className="mt-2 text-sm leading-7 text-muted">
        بعد از ثبت اولین هزینه گروهی، تاریخچه فعالیت‌ها اینجا نمایش داده می‌شود.
      </p>
      <button
        type="button"
        onClick={onCreate}
        className="mt-5 inline-flex h-11 items-center justify-center gap-2 rounded-[16px] bg-emerald-600 px-5 text-sm font-semibold text-white transition hover:bg-emerald-700"
      >
        <Plus className="h-4 w-4" />
        ثبت هزینه جدید
      </button>
    </div>
  );
}

function FilterEmptyState({ onReset }: { onReset: () => void }) {
  return (
    <div className="rounded-[24px] border border-dashed border-border bg-white p-8 text-center shadow-soft sm:p-10">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-[18px] bg-slate-50 text-slate-500">
        <Search className="h-6 w-6" />
      </div>
      <h2 className="text-xl font-bold text-text">نتیجه‌ای با این فیلترها پیدا نشد</h2>
      <p className="mt-2 text-sm leading-7 text-muted">
        عبارت جستجو، گروه یا بازه تاریخ را تغییر بدهید تا فعالیت‌های بیشتری دیده شود.
      </p>
      <button
        type="button"
        onClick={onReset}
        className="mt-5 inline-flex h-11 items-center justify-center gap-2 rounded-[16px] border border-border bg-white px-5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
      >
        <RefreshCw className="h-4 w-4" />
        پاک کردن فیلترها
      </button>
    </div>
  );
}

function Toast({ toast, onClose }: { toast: ToastState; onClose: () => void }) {
  const toneClass =
    toast.tone === 'success'
      ? 'border-emerald-100 bg-emerald-50 text-emerald-700'
      : toast.tone === 'error'
        ? 'border-rose-100 bg-rose-50 text-rose-600'
        : 'border-sky-100 bg-sky-50 text-sky-700';

  return (
    <div className={`fixed inset-x-4 top-20 z-50 rounded-[20px] border p-4 shadow-[0_18px_50px_rgba(15,23,42,0.14)] sm:left-5 sm:right-auto sm:w-[320px] ${toneClass}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="text-right">
          <div className="text-sm font-extrabold">{toast.title}</div>
          {toast.message ? <p className="mt-2 text-xs leading-6 opacity-90">{toast.message}</p> : null}
        </div>
        <button type="button" onClick={onClose} className="rounded-full p-1 transition hover:bg-white/70">
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

export function ActivitiesPage() {
  const [groups, setGroups] = useState<BackendGroup[]>([]);
  const [expenses, setExpenses] = useState<UiExpense[]>([]);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  const [selectedGroupId, setSelectedGroupId] = useState('all');
  const [selectedType, setSelectedType] = useState<ActivityFilter>('all');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const [loadingGroups, setLoadingGroups] = useState(false);
  const [loadingExpenses, setLoadingExpenses] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<ModalMode>('create');
  const [editingExpenseId, setEditingExpenseId] = useState<string | null>(null);
  const [form, setForm] = useState<ExpenseFormState>(defaultFormState);
  const [modalMembers, setModalMembers] = useState<BackendGroupMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [detailExpense, setDetailExpense] = useState<BackendExpense | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<UiExpense | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);

  function showToast(nextToast: ToastState) {
    setToast(nextToast);
    window.setTimeout(() => {
      setToast(null);
    }, 3200);
  }

  async function loadGroups() {
    try {
      setLoadingGroups(true);
      const [backendGroups, currentUser] = await Promise.all([
        getMyGroups(),
        getCurrentUser().catch(() => null),
      ]);

      setGroups(backendGroups);
      setCurrentUserId(currentUser?.id ? String(currentUser.id) : null);
    } catch (loadError) {
      console.error(loadError);
      setError('دریافت گروه‌ها ناموفق بود. دوباره تلاش کنید.');
    } finally {
      setLoadingGroups(false);
    }
  }

  async function loadExpenses() {
    if (groups.length === 0) {
      setExpenses([]);
      setError(null);
      return;
    }

    try {
      setLoadingExpenses(true);
      setError(null);

      const activeGroups = groups.filter(isActiveGroup);
      const targetGroups =
        selectedGroupId === 'all'
          ? activeGroups
          : groups.filter((group) => matchesGroupSelection(group, selectedGroupId));

      if (targetGroups.length === 0) {
        setExpenses([]);
        setError(null);
        return;
      }

      const responses = await Promise.allSettled(
        targetGroups.map(async (group) => {
          const groupExpenses = await listGroupExpenses(group.id, {
            from_date: dateInputToIso(fromDate),
            to_date: dateInputToIso(toDate),
          });

          return groupExpenses.map<UiExpense>((expense) => ({
            ...expense,
            groupTitle: group.title,
          }));
        }),
      );

      const successfulResponses = responses
        .filter((response): response is PromiseFulfilledResult<UiExpense[]> => response.status === 'fulfilled')
        .map((response) => response.value);

      const failedResponses = responses.filter(
        (response): response is PromiseRejectedResult => response.status === 'rejected',
      );

      if (failedResponses.length > 0) {
        console.warn(
          'Some group expense requests failed and were skipped:',
          failedResponses.map((response) => getApiErrorMessage(response.reason)),
        );
      }

      if (successfulResponses.length === 0 && failedResponses.length > 0) {
        // Some group expense endpoints can return 400/403 depending on membership or archived state.
        // Do not break the page; show an empty state instead of a red blocking error.
        setExpenses([]);
        setError(null);
        return;
      }

      setExpenses(
        successfulResponses
          .flat()
          .sort((a, b) => {
            const dateA = new Date(a.expense_date || a.created_at || 0).getTime();
            const dateB = new Date(b.expense_date || b.created_at || 0).getTime();
            return dateB - dateA;
          }),
      );
    } catch (loadError) {
      console.error(loadError);
      setError('دریافت فعالیت‌ها ناموفق بود. دوباره تلاش کنید.');
    } finally {
      setLoadingExpenses(false);
    }
  }

  async function loadMembersForGroup(groupId: string) {
    if (!groupId) {
      setModalMembers([]);
      return;
    }

    try {
      setMembersLoading(true);
      const members = await getGroupMembers(groupId);
      setModalMembers(members);

      setForm((prev) => {
        const currentUserMember = members.find((member) => getMemberUserId(member) === currentUserId);
        const defaultPayer = prev.payerUserId || (currentUserMember ? getMemberUserId(currentUserMember) : '') || (members[0] ? getMemberUserId(members[0]) : '');
        const defaultParticipants = prev.participantUserIds.length
          ? prev.participantUserIds
          : members
              .map(getMemberUserId)
              .filter((userId): userId is string => Boolean(userId));

        return {
          ...prev,
          payerUserId: defaultPayer,
          participantUserIds: defaultParticipants,
        };
      });
    } catch (loadError) {
      console.error(loadError);
      showToast({
        tone: 'error',
        title: 'دریافت اعضا ناموفق بود',
        message: 'برای ثبت هزینه باید اعضای گروه دریافت شوند.',
      });
    } finally {
      setMembersLoading(false);
    }
  }

  useEffect(() => {
    loadGroups();
  }, []);

  useEffect(() => {
    loadExpenses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groups, selectedGroupId, fromDate, toDate]);

  const filteredExpenses = useMemo(() => {
    return expenses.filter((expense) => {
      const kind = getExpenseKind(expense, currentUserId);
      const normalizedSearch = searchTerm.trim().toLowerCase();

      if (selectedType === 'paid' && kind !== 'paid') return false;
      if (selectedType === 'received' && kind !== 'received') return false;
      if (selectedType === 'settled') {
        const status = (expense.status || '').toLowerCase();
        if (!status.includes('settled') && !status.includes('closed')) return false;
      }

      if (!normalizedSearch) return true;

      return [expense.title, expense.description, expense.groupTitle]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalizedSearch));
    });
  }, [currentUserId, expenses, searchTerm, selectedType]);

  const groupedExpenses = useMemo(() => groupExpensesByDate(filteredExpenses), [filteredExpenses]);
  const hasActiveFilters = Boolean(
    selectedGroupId !== 'all' ||
    selectedType !== 'all' ||
    fromDate ||
    toDate ||
    searchTerm.trim(),
  );
  const totalVisibleAmount = useMemo(
    () => filteredExpenses.reduce((sum, expense) => sum + getExpenseTotal(expense), 0),
    [filteredExpenses],
  );
  const paidVisibleCount = useMemo(
    () => filteredExpenses.filter((expense) => getExpenseKind(expense, currentUserId) === 'paid').length,
    [currentUserId, filteredExpenses],
  );
  const receivedVisibleCount = Math.max(filteredExpenses.length - paidVisibleCount, 0);

  function resetFilters() {
    setSelectedGroupId('all');
    setSelectedType('all');
    setFromDate('');
    setToDate('');
    setSearchTerm('');
  }

  function openCreateModal() {
    const firstActiveGroupId = groups.find(isActiveGroup)?.id || groups[0]?.id || '';
    const selectedGroup = groups.find((group) => matchesGroupSelection(group, selectedGroupId));
    const initialGroupId = selectedGroupId === 'all' ? String(firstActiveGroupId) : String(selectedGroup?.id || selectedGroupId);

    setModalMode('create');
    setEditingExpenseId(null);
    setForm({
      ...defaultFormState,
      groupId: initialGroupId,
      expenseDate: isoToDateTimeLocal(new Date().toISOString()),
    });
    setModalOpen(true);

    if (initialGroupId) {
      loadMembersForGroup(initialGroupId);
    }
  }

  async function openEditModal(expense: UiExpense) {
    try {
      setModalMode('edit');
      setEditingExpenseId(expense.id);
      setModalOpen(true);
      setMembersLoading(true);

      const detail = await getExpenseDetail(expense.id);
      const members = await getGroupMembers(detail.group_id);
      const participantIds = (detail.participants || [])
        .filter((participant) => participant.is_included !== false)
        .map((participant) => participant.user_id);

      setModalMembers(members);
      setForm({
        groupId: detail.group_id,
        title: detail.title || '',
        description: detail.description || '',
        payerUserId: detail.payer_user_id || '',
        baseAmountMinor: String(detail.base_amount_minor ?? 0),
        currency: detail.currency || 'IRR',
        splitMethod: detail.split_method === 'CUSTOM' ? 'CUSTOM' : 'EQUAL',
        participantUserIds: participantIds,
        customShares: makeShareInputs(detail.participants),
        taxAmountMinor: String(detail.tax_amount_minor ?? 0),
        serviceFeeAmountMinor: String(detail.service_fee_amount_minor ?? 0),
        expenseDate: isoToDateTimeLocal(detail.expense_date || detail.created_at),
        receiptUrl: detail.receipt_url || '',
      });
    } catch (loadError) {
      console.error(loadError);
      showToast({ tone: 'error', title: 'ویرایش هزینه ناموفق بود', message: 'جزئیات هزینه دریافت نشد.' });
      setModalOpen(false);
    } finally {
      setMembersLoading(false);
    }
  }

  async function openDetailModal(expense: UiExpense) {
    try {
      setDetailLoading(true);
      setDetailExpense(null);
      const detail = await getExpenseDetail(expense.id);
      setDetailExpense({ ...detail, groupTitle: expense.groupTitle } as UiExpense);
    } catch (loadError) {
      console.error(loadError);
      showToast({ tone: 'error', title: 'دریافت جزئیات ناموفق بود' });
    } finally {
      setDetailLoading(false);
    }
  }

  function toggleParticipant(userId: string) {
    setForm((prev) => {
      const exists = prev.participantUserIds.includes(userId);
      return {
        ...prev,
        participantUserIds: exists
          ? prev.participantUserIds.filter((id) => id !== userId)
          : [...prev.participantUserIds, userId],
      };
    });
  }

  function buildExpensePayload() {
    const baseAmountMinor = parseAmount(form.baseAmountMinor);
    const taxAmountMinor = parseAmount(form.taxAmountMinor);
    const serviceFeeAmountMinor = parseAmount(form.serviceFeeAmountMinor);
    const participants = form.participantUserIds.map((userId) => ({
      user_id: userId,
      base_share_minor: parseAmount(form.customShares[userId] || '0'),
    }));

    return {
      title: form.title,
      description: form.description,
      payer_user_id: form.payerUserId,
      base_amount_minor: baseAmountMinor,
      currency: form.currency || 'IRR',
      split_method: form.splitMethod,
      participant_user_ids: form.splitMethod === 'EQUAL' ? form.participantUserIds : undefined,
      participants: form.splitMethod === 'CUSTOM' ? participants : undefined,
      tax_type: taxAmountMinor > 0 ? 'AMOUNT' : 'NONE',
      tax_amount_minor: taxAmountMinor,
      service_fee_type: serviceFeeAmountMinor > 0 ? 'AMOUNT' : 'NONE',
      service_fee_amount_minor: serviceFeeAmountMinor,
      expense_date: dateInputToIso(form.expenseDate),
      receipt_url: form.receiptUrl || undefined,
    };
  }

  async function handleSubmitExpense(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!form.groupId) {
      showToast({ tone: 'error', title: 'گروه را انتخاب کنید' });
      return;
    }

    if (!form.title.trim()) {
      showToast({ tone: 'error', title: 'عنوان هزینه را وارد کنید' });
      return;
    }

    if (!form.payerUserId) {
      showToast({ tone: 'error', title: 'پرداخت‌کننده را انتخاب کنید' });
      return;
    }

    if (form.participantUserIds.length === 0) {
      showToast({ tone: 'error', title: 'حداقل یک شرکت‌کننده انتخاب کنید' });
      return;
    }

    try {
      setSubmitting(true);
      const payload = buildExpensePayload();

      if (modalMode === 'edit' && editingExpenseId) {
        await updateExpense(editingExpenseId, payload);
        showToast({ tone: 'success', title: 'هزینه ویرایش شد' });
      } else {
        await createGroupExpense(form.groupId, payload);
        showToast({ tone: 'success', title: 'هزینه جدید ثبت شد' });
      }

      setModalOpen(false);
      await loadExpenses();
    } catch (submitError) {
      console.error(submitError);
      showToast({
        tone: 'error',
        title: 'ثبت هزینه ناموفق بود',
        message: 'اطلاعات فرم یا اتصال را بررسی کنید و دوباره تلاش کنید.',
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteExpense() {
    if (!deleteTarget) return;

    try {
      await deleteExpense(deleteTarget.id);
      setExpenses((prev) => prev.filter((expense) => expense.id !== deleteTarget.id));
      setDeleteTarget(null);
      showToast({ tone: 'success', title: 'هزینه حذف شد' });
    } catch (deleteError) {
      console.error(deleteError);
      showToast({ tone: 'error', title: 'حذف هزینه ناموفق بود' });
    }
  }

  return (
    <main className="px-4 py-5 sm:px-6 sm:py-7 xl:px-8">
      {toast ? <Toast toast={toast} onClose={() => setToast(null)} /> : null}

      <div className="mx-auto max-w-[1240px] space-y-6">
        <div className="flex flex-col gap-4 text-right lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-[30px] font-extrabold leading-tight text-text sm:text-[32px]">فعالیت‌ها</h1>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-muted sm:text-base">
              هزینه‌های گروهی، سهم اعضا و وضعیت پرداخت‌ها را در یک نمای قابل جستجو دنبال کنید.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={openCreateModal}
              className="inline-flex h-12 items-center justify-center gap-2 rounded-[16px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-5 text-sm font-bold text-white shadow-[0_12px_28px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5"
            >
              <Plus className="h-4.5 w-4.5" />
              ثبت هزینه جدید
            </button>

            <button
              type="button"
              onClick={() => {
                loadGroups();
                loadExpenses();
              }}
              disabled={loadingGroups || loadingExpenses}
              className="inline-flex h-12 items-center justify-center gap-2 rounded-[16px] border border-border bg-white px-5 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={cn('h-4.5 w-4.5', (loadingGroups || loadingExpenses) && 'animate-spin')} />
              به‌روزرسانی
            </button>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-[20px] border border-border bg-white p-4 shadow-panel">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-slate-50 text-slate-600">
                <ClipboardList className="h-5 w-5" />
              </div>
              <span className="text-xs font-bold text-muted">نتایج نمایش‌داده‌شده</span>
            </div>
            <div className="text-2xl font-black text-text">{toPersianNumber(filteredExpenses.length)}</div>
            <p className="mt-1 text-xs leading-6 text-muted">فعالیت مطابق فیلترهای فعلی</p>
          </div>

          <div className="rounded-[20px] border border-border bg-white p-4 shadow-panel">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-emerald-50 text-emerald-600">
                <TrendingDown className="h-5 w-5" />
              </div>
              <span className="text-xs font-bold text-muted">سهم‌های من</span>
            </div>
            <div className="text-2xl font-black text-emerald-600">{toPersianNumber(receivedVisibleCount)}</div>
            <p className="mt-1 text-xs leading-6 text-muted">فعالیت‌هایی که شما در آن‌ها شریک هستید</p>
          </div>

          <div className="rounded-[20px] border border-border bg-white p-4 shadow-panel">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-orange-50 text-orange-600">
                <TrendingUp className="h-5 w-5" />
              </div>
              <span className="text-xs font-bold text-muted">گردش هزینه‌ها</span>
            </div>
            <div className="text-xl font-black text-text sm:text-2xl">{formatMoney(totalVisibleAmount)}</div>
            <p className="mt-1 text-xs leading-6 text-muted">{toPersianNumber(paidVisibleCount)} پرداخت ثبت‌شده در این نما</p>
          </div>
        </div>

        <div className="space-y-6">
          <section className="space-y-6">
            <div className="rounded-[24px] border border-border bg-white p-4 shadow-soft sm:p-5">
              <div className="mb-5 flex flex-col gap-3 text-right lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 className="text-lg font-extrabold text-text sm:text-xl">فیلترها</h2>
                  <p className="mt-1 text-sm leading-6 text-muted">
                    فعالیت‌ها را بر اساس گروه، بازه زمانی و نوع نمایش محدود کنید.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={resetFilters}
                  disabled={!hasActiveFilters}
                  className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-[16px] border border-border bg-white px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <RefreshCw className="h-4 w-4" />
                  پاک کردن فیلترها
                </button>
              </div>

              <div className="grid gap-3 lg:grid-cols-[minmax(0,1.35fr)_minmax(180px,0.9fr)_160px_160px]">
                <div>
                  <label className="mb-2 block text-xs font-bold text-muted">جستجو</label>
                  <div className="relative">
                    <Search className="pointer-events-none absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                    <input
                      dir="rtl"
                      value={searchTerm}
                      onChange={(event) => setSearchTerm(event.target.value)}
                      placeholder="عنوان، توضیح یا نام گروه"
                      className="h-12 w-full rounded-[16px] border border-border bg-white pr-12 pl-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-2 block text-xs font-bold text-muted">گروه</label>
                  <div className="relative">
                    <Users className="pointer-events-none absolute right-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" />
                    <ChevronDown className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" />
                    <select
                      value={selectedGroupId}
                      onChange={(event) => setSelectedGroupId(event.target.value)}
                      className="h-12 w-full appearance-none rounded-[16px] border border-border bg-white px-11 text-sm font-semibold text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                    >
                      <option value="all">همه گروه‌ها</option>
                      {groups.map((group) => (
                        <option key={group.id} value={getSelectedGroupValue(group)}>{group.title}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="mb-2 block text-xs font-bold text-muted">از تاریخ</label>
                  <input
                    type="date"
                    value={fromDate}
                    onChange={(event) => setFromDate(event.target.value)}
                    className="h-12 w-full rounded-[16px] border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-xs font-bold text-muted">تا تاریخ</label>
                  <input
                    type="date"
                    value={toDate}
                    onChange={(event) => setToDate(event.target.value)}
                    className="h-12 w-full rounded-[16px] border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {[
                  ['all', 'همه'],
                  ['received', 'سهم من'],
                  ['paid', 'پرداخت من'],
                  ['settled', 'تسویه‌شده'],
                ].map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setSelectedType(value as ActivityFilter)}
                    className={[
                      'h-10 rounded-[16px] px-4 text-sm font-bold transition',
                      selectedType === value
                        ? 'bg-emerald-600 text-white shadow-[0_10px_24px_rgba(16,185,129,0.2)]'
                        : 'border border-border bg-white text-slate-600 hover:bg-slate-50',
                    ].join(' ')}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {error ? (
              <div className="rounded-[20px] border border-rose-100 bg-rose-50 p-5 text-center text-sm font-bold text-rose-600">
                {error}
              </div>
            ) : null}

            {loadingGroups || loadingExpenses ? (
              <div className="flex min-h-[220px] items-center justify-center rounded-[24px] border border-border bg-white p-8 text-muted shadow-soft">
                <Loader2 className="ml-2 h-5 w-5 animate-spin" />
                در حال دریافت فعالیت‌ها...
              </div>
            ) : null}

            {!loadingGroups && !loadingExpenses && filteredExpenses.length === 0 && !hasActiveFilters ? (
              <EmptyState onCreate={openCreateModal} />
            ) : null}

            {!loadingGroups && !loadingExpenses && filteredExpenses.length === 0 && hasActiveFilters ? (
              <FilterEmptyState onReset={resetFilters} />
            ) : null}

            {!loadingGroups && !loadingExpenses && filteredExpenses.length > 0 ? (
              <div className="space-y-6">
                {Object.entries(groupedExpenses).map(([dateLabel, dateExpenses]) => (
                  <div key={dateLabel} className="space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
                        {toPersianNumber(dateExpenses.length)} مورد
                      </span>
                      <h2 className="text-right text-base font-extrabold text-text sm:text-lg">{dateLabel}</h2>
                    </div>

                    <div className="grid gap-3">
                      {dateExpenses.map((expense) => {
                        const kind = getExpenseKind(expense, currentUserId);
                        const total = getExpenseTotal(expense);
                        const amount = kind === 'paid' ? -total : total;
                        const payerParticipant = expense.participants?.find(
                          (participant) => participant.user_id === expense.payer_user_id,
                        );

                        return (
                          <article
                            key={expense.id}
                            className="rounded-[22px] border border-border bg-white p-4 shadow-panel transition hover:border-emerald-200 hover:shadow-soft sm:p-5"
                          >
                            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_190px] lg:items-start">
                              <div className="flex min-w-0 items-start gap-3 text-right">
                                <div
                                  className={cn(
                                    'flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px]',
                                    kind === 'paid' ? 'bg-rose-50 text-rose-500' : 'bg-emerald-50 text-emerald-600',
                                  )}
                                >
                                  {kind === 'paid' ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
                                </div>

                                <div className="min-w-0 flex-1">
                                  <div className="flex flex-wrap items-start justify-between gap-2">
                                    <h3 className="min-w-0 break-words text-base font-extrabold leading-7 text-text">
                                      {expense.title || 'هزینه بدون عنوان'}
                                    </h3>
                                    <span className={cn('shrink-0 rounded-full border px-3 py-1 text-xs font-bold', getExpenseStatusClassName(expense.status))}>
                                      {getExpenseStatusLabel(expense.status)}
                                    </span>
                                  </div>

                                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs leading-6 text-muted">
                                    <span>{expense.groupTitle || 'گروه'}</span>
                                    <span>پرداخت‌کننده: {getParticipantName(payerParticipant)}</span>
                                    <span>{formatTime(expense.expense_date || expense.created_at)}</span>
                                  </div>

                                  <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold">
                                    <span className="rounded-full bg-slate-50 px-3 py-1 text-slate-600">
                                      {getSplitMethodLabel(expense.split_method)}
                                    </span>
                                    <span className="rounded-full bg-slate-50 px-3 py-1 text-slate-600">
                                      {getParticipantCountLabel(expense)}
                                    </span>
                                  </div>
                                </div>
                              </div>

                              <div className="flex items-center justify-between gap-3 rounded-[16px] bg-slate-50 px-4 py-3 lg:flex-col lg:items-end lg:justify-center lg:bg-transparent lg:p-0">
                                <span
                                  className={cn(
                                    'text-lg font-black sm:text-xl',
                                    amount >= 0 ? 'text-emerald-600' : 'text-rose-500',
                                  )}
                                >
                                  {formatSignedMoney(amount)}
                                </span>
                                <span className="rounded-full border border-border bg-white px-3 py-1 text-xs font-bold text-slate-600">
                                  {getExpenseKindLabel(kind)}
                                </span>
                              </div>
                            </div>

                            <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-3 sm:justify-end">
                              <button
                                type="button"
                                onClick={() => openDetailModal(expense)}
                                className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-[12px] bg-slate-50 px-3 text-xs font-bold text-slate-600 transition hover:bg-slate-100 sm:flex-none"
                              >
                                <Eye className="h-3.5 w-3.5" />
                                جزئیات
                              </button>

                              <button
                                type="button"
                                onClick={() => openEditModal(expense)}
                                className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-[12px] bg-emerald-50 px-3 text-xs font-bold text-emerald-700 transition hover:bg-emerald-100 sm:flex-none"
                              >
                                <Edit3 className="h-3.5 w-3.5" />
                                ویرایش
                              </button>

                              <button
                                type="button"
                                onClick={() => setDeleteTarget(expense)}
                                className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-[12px] bg-rose-50 px-3 text-xs font-bold text-rose-600 transition hover:bg-rose-100 sm:flex-none"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                                حذف
                              </button>
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </section>

        </div>
      </div>

      {modalOpen ? (
        <div className="fixed inset-0 z-40 flex items-end justify-center bg-slate-900/40 p-0 backdrop-blur-sm sm:items-center sm:p-4">
          <div className="max-h-[94vh] w-full max-w-[840px] overflow-y-auto rounded-t-[24px] border border-border bg-white p-4 shadow-[0_24px_80px_rgba(15,23,42,0.22)] sm:rounded-[24px] sm:p-6">
            <div className="mb-6 flex items-start justify-between gap-4">
              <div className="text-right">
                <h2 className="text-2xl font-extrabold text-text">
                  {modalMode === 'create' ? 'ثبت هزینه جدید' : 'ویرایش هزینه'}
                </h2>
                <p className="mt-2 text-sm leading-6 text-muted">گروه، پرداخت‌کننده، مبلغ و اعضای شریک در هزینه را مشخص کنید.</p>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] bg-slate-50 text-slate-600 transition hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitExpense} className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">گروه</label>
                  <select
                    value={form.groupId}
                    disabled={modalMode === 'edit'}
                    onChange={(event) => {
                      const groupId = event.target.value;
                      setForm((prev) => ({
                        ...prev,
                        groupId,
                        payerUserId: '',
                        participantUserIds: [],
                        customShares: {},
                      }));
                      loadMembersForGroup(groupId);
                    }}
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 disabled:bg-slate-50"
                  >
                    <option value="">انتخاب گروه</option>
                    {groups.map((group) => (
                      <option key={group.id} value={getSelectedGroupValue(group)}>{group.title}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">پرداخت‌کننده</label>
                  <select
                    value={form.payerUserId}
                    onChange={(event) => setForm((prev) => ({ ...prev, payerUserId: event.target.value }))}
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  >
                    <option value="">انتخاب پرداخت‌کننده</option>
                    {modalMembers.map((member) => {
                      const userId = getMemberUserId(member);
                      if (!userId) return null;

                      return <option key={member.id || userId} value={userId}>{getMemberName(member)}</option>;
                    })}
                  </select>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">عنوان هزینه</label>
                  <input
                    dir="rtl"
                    value={form.title}
                    onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
                    placeholder="مثلاً شام گروهی"
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">مبلغ هزینه</label>
                  <input
                    dir="ltr"
                    inputMode="numeric"
                    value={form.baseAmountMinor}
                    onChange={(event) => setForm((prev) => ({ ...prev, baseAmountMinor: event.target.value }))}
                    placeholder="۹۰۰۰۰۰"
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-left text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-text">توضیحات</label>
                <textarea
                  dir="rtl"
                  value={form.description}
                  onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
                  className="min-h-[96px] w-full resize-none rounded-2xl border border-border bg-white px-4 py-3 text-sm leading-7 text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                />
              </div>

              <div className="grid gap-4 md:grid-cols-4">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">روش تقسیم</label>
                  <select
                    value={form.splitMethod}
                    onChange={(event) => setForm((prev) => ({ ...prev, splitMethod: event.target.value as ExpenseSplitMethod }))}
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  >
                    <option value="EQUAL">مساوی</option>
                    <option value="CUSTOM">سفارشی</option>
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">مالیات</label>
                  <input
                    dir="ltr"
                    inputMode="numeric"
                    value={form.taxAmountMinor}
                    onChange={(event) => setForm((prev) => ({ ...prev, taxAmountMinor: event.target.value }))}
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-left text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">کارمزد سرویس</label>
                  <input
                    dir="ltr"
                    inputMode="numeric"
                    value={form.serviceFeeAmountMinor}
                    onChange={(event) => setForm((prev) => ({ ...prev, serviceFeeAmountMinor: event.target.value }))}
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-left text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">تاریخ هزینه</label>
                  <input
                    type="datetime-local"
                    value={form.expenseDate}
                    onChange={(event) => setForm((prev) => ({ ...prev, expenseDate: event.target.value }))}
                    className="h-12 w-full rounded-2xl border border-border bg-white px-3 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>
              </div>

              <div>
                <div className="mb-3 flex items-center justify-between">
                  <label className="text-sm font-semibold text-text">شرکت‌کننده‌ها</label>
                  {membersLoading ? <span className="text-xs text-muted">در حال دریافت اعضا...</span> : null}
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  {modalMembers.map((member) => {
                    const userId = getMemberUserId(member);
                    if (!userId) return null;

                    const checked = form.participantUserIds.includes(userId);

                    return (
                      <div
                        key={member.id}
                        className={[
                          'rounded-2xl border p-3 transition',
                          checked ? 'border-emerald-200 bg-emerald-50/60' : 'border-border bg-white',
                        ].join(' ')}
                      >
                        <label className="flex cursor-pointer items-center gap-3 text-right">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleParticipant(userId)}
                            className="h-4 w-4 accent-emerald-600"
                          />
                          <span className="flex-1 text-sm font-semibold text-text">{getMemberName(member)}</span>
                        </label>

                        {form.splitMethod === 'CUSTOM' && checked ? (
                          <input
                            dir="ltr"
                            inputMode="numeric"
                            value={form.customShares[userId] || ''}
                            onChange={(event) => setForm((prev) => ({
                              ...prev,
                              customShares: {
                                ...prev.customShares,
                                [userId]: event.target.value,
                              },
                            }))}
                            placeholder="سهم پایه"
                            className="mt-3 h-10 w-full rounded-xl border border-border bg-white px-3 text-left text-xs outline-none focus:border-emerald-500/50"
                          />
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-text">لینک رسید</label>
                <input
                  dir="ltr"
                  value={form.receiptUrl}
                  onChange={(event) => setForm((prev) => ({ ...prev, receiptUrl: event.target.value }))}
                  placeholder="https://..."
                  className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-left text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                />
              </div>

              <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="h-12 rounded-2xl border border-border bg-white px-5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  انصراف
                </button>

                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(0,168,107,0.18)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                  {modalMode === 'create' ? 'ثبت هزینه' : 'ذخیره تغییرات'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {detailExpense || detailLoading ? (
        <div className="fixed inset-0 z-40 flex items-end justify-center bg-slate-900/40 p-0 backdrop-blur-sm sm:items-center sm:p-4">
          <div className="max-h-[94vh] w-full max-w-[620px] overflow-y-auto rounded-t-[24px] border border-border bg-white p-4 shadow-[0_24px_80px_rgba(15,23,42,0.22)] sm:rounded-[24px] sm:p-6">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="text-right">
                <h2 className="text-2xl font-extrabold text-text">جزئیات هزینه</h2>
                <p className="mt-2 text-sm leading-6 text-muted">جزئیات مبلغ، وضعیت و سهم هر شرکت‌کننده.</p>
              </div>
              <button
                type="button"
                onClick={() => setDetailExpense(null)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] bg-slate-50 text-slate-600 transition hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {detailLoading ? (
              <div className="flex h-32 items-center justify-center text-muted">
                <Loader2 className="ml-2 h-5 w-5 animate-spin" />
                در حال دریافت جزئیات...
              </div>
            ) : null}

            {detailExpense ? (
              <div className="space-y-4 text-right">
                <div className="rounded-[20px] bg-emerald-50 p-5">
                  <h3 className="text-xl font-extrabold text-text">{detailExpense.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-muted">{detailExpense.description || 'بدون توضیح'}</p>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-[16px] border border-border p-4">
                    <span className="text-xs text-muted">مبلغ هزینه</span>
                    <div className="mt-2 font-extrabold text-text">{formatMoney(detailExpense.base_amount_minor)}</div>
                  </div>
                  <div className="rounded-[16px] border border-border p-4">
                    <span className="text-xs text-muted">مبلغ کل</span>
                    <div className="mt-2 font-extrabold text-emerald-600">{formatMoney(getExpenseTotal(detailExpense))}</div>
                  </div>
                  <div className="rounded-[16px] border border-border p-4">
                    <span className="text-xs text-muted">روش تقسیم</span>
                    <div className="mt-2 font-extrabold text-text">{getSplitMethodLabel(detailExpense.split_method)}</div>
                  </div>
                  <div className="rounded-[16px] border border-border p-4">
                    <span className="text-xs text-muted">وضعیت</span>
                    <div className="mt-2 font-extrabold text-text">{getExpenseStatusLabel(detailExpense.status)}</div>
                  </div>
                </div>

                <div>
                  <h4 className="mb-3 font-extrabold text-text">شرکت‌کننده‌ها</h4>
                  <div className="space-y-2">
                    {(detailExpense.participants || []).map((participant) => (
                      <div key={participant.user_id} className="flex flex-wrap items-center justify-between gap-2 rounded-[16px] border border-border px-4 py-3 text-sm">
                        <span className="font-semibold text-text">{getParticipantName(participant)}</span>
                        <span className="font-bold text-emerald-600">{formatMoney(participant.total_share_minor || participant.base_share_minor || 0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {deleteTarget ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-0 backdrop-blur-sm sm:items-center sm:p-4">
          <div className="w-full max-w-[420px] rounded-t-[24px] border border-rose-100 bg-white p-5 text-right shadow-[0_24px_80px_rgba(15,23,42,0.22)] sm:rounded-[24px] sm:p-6">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-[16px] bg-rose-50 text-rose-600">
              <Trash2 className="h-5 w-5" />
            </div>
            <h2 className="text-xl font-extrabold text-text">حذف هزینه</h2>
            <p className="mt-2 text-sm leading-7 text-muted">
              هزینه «{deleteTarget.title}» از فهرست فعالیت‌ها حذف می‌شود. این کار را انجام می‌دهید؟
            </p>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="h-11 flex-1 rounded-[16px] border border-border bg-white text-sm font-bold text-slate-700 transition hover:bg-slate-50"
              >
                انصراف
              </button>
              <button
                type="button"
                onClick={handleDeleteExpense}
                className="h-11 flex-1 rounded-[16px] bg-rose-600 text-sm font-bold text-white transition hover:bg-rose-700"
              >
                حذف شود
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
