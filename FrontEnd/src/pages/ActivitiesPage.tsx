import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import {
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Download,
  Eye,
  Loader2,
  MoreVertical,
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
  type BackendExpense,
  type ExpenseParticipant,
  type ExpenseSplitMethod,
} from '../lib/expenseApi';
import {
  getBackendGroupMemberName,
  getBackendGroupMemberUserId,
  getGroupMembers,
  getMyGroups,
  type BackendGroup,
  type BackendGroupMember,
} from '../lib/groupApi';
import { getCurrentUser } from '../lib/userApi';
import { downloadMediaFile, uploadReceipt } from '../lib/mediaApi';
import { MoneyWithWords } from '../lib/money';
import { humanizeMachineLabel } from '../lib/userMessages';

type ActivityFilter = 'all' | 'received' | 'paid' | 'settled';
type UiExpense = BackendExpense & {
  groupTitle?: string;
};

type ReceiptPreviewState = {
  expenseTitle: string;
  fileName?: string;
  url: string;
  contentType?: string;
  isObjectUrl: boolean;
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
  receiptFile: File | null;
  receiptFileId: string;
  receiptFileName: string;
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
  receiptFile: null,
  receiptFileId: '',
  receiptFileName: '',
  receiptUrl: '',
};

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
  return `تومان \u2066${toPersianNumber(Math.abs(amount).toLocaleString('en-US'))}\u2069`;
}

function formatSignedMoney(amount: number) {
  const sign = amount > 0 ? '+' : amount < 0 ? '-' : '';
  const digits = toPersianNumber(Math.abs(amount).toLocaleString('en-US'));
  return `تومان \u2066${sign}${digits}\u2069`;
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

function formatDateInputValue(date: Date) {
  const offsetMs = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 10);
}

function getRelativeDateInput(daysAgo: number) {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return formatDateInputValue(date);
}

function formatCompactDateLabel(value: string) {
  if (!value) return '';

  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString('fa-IR', {
    month: 'short',
    day: 'numeric',
  });
}

function getExpenseTotal(expense: BackendExpense) {
  return expense.total_amount_minor ?? expense.base_amount_minor ?? 0;
}

function getExpenseReceiptKey(expense: Pick<BackendExpense, 'receipt_file_id' | 'receipt_url'>) {
  return expense.receipt_file_id || expense.receipt_url || '';
}

function inferReceiptContentTypeFromUrl(url?: string) {
  if (!url) return '';
  const cleanUrl = url.split('?')[0].toLowerCase();
  if (/\.(png|apng)$/.test(cleanUrl)) return 'image/png';
  if (/\.(jpe?g|jfif)$/.test(cleanUrl)) return 'image/jpeg';
  if (/\.webp$/.test(cleanUrl)) return 'image/webp';
  if (/\.gif$/.test(cleanUrl)) return 'image/gif';
  if (/\.pdf$/.test(cleanUrl)) return 'application/pdf';
  return '';
}

function isImageReceipt(contentType?: string, url?: string) {
  return (contentType || inferReceiptContentTypeFromUrl(url)).toLowerCase().startsWith('image/');
}

function isPdfReceipt(contentType?: string, url?: string) {
  return (contentType || inferReceiptContentTypeFromUrl(url)).toLowerCase().includes('pdf');
}

function getFileNameFromUrl(url: string, fallback = 'receipt') {
  try {
    const { pathname } = new URL(url, window.location.origin);
    const fileName = decodeURIComponent(pathname.split('/').filter(Boolean).pop() || '');
    return fileName || fallback;
  } catch {
    return fallback;
  }
}

function canCurrentUserSeeExpenseReceipt(expense: BackendExpense, currentUserId?: string | null) {
  if (!currentUserId || !getExpenseReceiptKey(expense)) return false;

  if (String(expense.payer_user_id || '') === currentUserId || String(expense.created_by_user_id || '') === currentUserId) {
    return true;
  }

  const includedParticipants = (expense.participants || []).filter((participant) => participant.is_included !== false);

  // Some list responses do not hydrate participants. In that case, keep the
  // receipt accessible to the signed-in group member instead of hiding it by mistake.
  if (includedParticipants.length === 0) return true;

  return includedParticipants.some((participant) => String(participant.user_id || '') === currentUserId);
}

function getMemberName(member: BackendGroupMember) {
  return getBackendGroupMemberName(member);
}

function getMemberUserId(member: BackendGroupMember) {
  return getBackendGroupMemberUserId(member);
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
  return value
    .trim()
    .replace(/ي/g, 'ی')
    .replace(/ك/g, 'ک')
    .replace(/[\u064B-\u065F\u0670]/g, '')
    .replace(/\s+/g, ' ')
    .toLowerCase();
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

function getExpenseKind(expense: BackendExpense, currentUserId?: string | null) {
  if (!currentUserId) return 'paid';

  if (expense.payer_user_id === currentUserId) return 'paid';

  const isParticipant = expense.participants?.some(
    (participant) =>
      participant.user_id === currentUserId && participant.is_included !== false,
  );

  return isParticipant ? 'received' : 'paid';
}

function getActivityFilterLabel(value: ActivityFilter) {
  const labels: Record<ActivityFilter, string> = {
    all: 'همه فعالیت‌ها',
    received: 'طلب‌ها',
    paid: 'پرداختی‌ها',
    settled: 'تسویه‌شده‌ها',
  };

  return labels[value];
}

function isSettledExpense(expense: BackendExpense) {
  const status = (expense.status || '').toLowerCase();
  return status.includes('settled') || status.includes('closed');
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

function EmptyState({ onCreate, filtered, onClear }: { onCreate: () => void; filtered?: boolean; onClear?: () => void }) {
  return (
    <div className="rounded-[24px] border border-dashed border-emerald-200 bg-emerald-50/40 px-5 py-9 text-center sm:p-10">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-[22px] bg-white text-emerald-600 shadow-sm">
        <ClipboardList className="h-7 w-7" />
      </div>

      <h2 className="text-xl font-bold text-text">{filtered ? 'نتیجه‌ای پیدا نشد' : 'هنوز فعالیتی ثبت نشده'}</h2>

      {!filtered ? <p className="mx-auto mt-2 max-w-[440px] text-sm leading-7 text-muted">اولین هزینه گروهی را ثبت کن تا تاریخچه فعالیت‌ها اینجا نمایش داده شود.</p> : null}

      <button
        type="button"
        onClick={filtered ? onClear : onCreate}
        className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-[16px] bg-emerald-600 px-5 text-sm font-semibold text-white transition hover:bg-emerald-700 sm:w-auto"
      >
        {filtered ? <RefreshCw className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
        {filtered ? 'پاک کردن فیلترها' : 'ثبت هزینه جدید'}
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
    <div
      className={`fixed left-4 right-4 top-20 z-50 rounded-[22px] border p-4 shadow-[0_18px_50px_rgba(15,23,42,0.14)] sm:left-5 sm:right-auto sm:top-24 sm:w-[360px] ${toneClass}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="text-right">
          <div className="text-sm font-extrabold">{toast.title}</div>
          {toast.message ? (
            <p className="mt-2 text-xs leading-6 opacity-90">{toast.message}</p>
          ) : null}
        </div>

        <button
          type="button"
          onClick={onClose}
          className="rounded-full p-1 transition hover:bg-white/70"
        >
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
  const [dateFiltersOpen, setDateFiltersOpen] = useState(false);
  const [openActionMenuId, setOpenActionMenuId] = useState<string | null>(null);
  const [openingReceiptId, setOpeningReceiptId] = useState<string | null>(null);
  const [receiptPreview, setReceiptPreview] = useState<ReceiptPreviewState | null>(null);

  const [loadingGroups, setLoadingGroups] = useState(false);
  const [loadingExpenses, setLoadingExpenses] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<ExpenseFormState>(defaultFormState);
  const [modalMembers, setModalMembers] = useState<BackendGroupMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [advancedFormOpen, setAdvancedFormOpen] = useState(false);

  const [detailExpense, setDetailExpense] = useState<BackendExpense | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const detailRequestId = useRef(0);

  const [deleteTarget, setDeleteTarget] = useState<UiExpense | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);

  function showToast(nextToast: ToastState) {
    setToast(nextToast);
    window.setTimeout(() => {
      setToast(null);
    }, 20_000);
  }

  useEffect(() => {
    return () => {
      if (receiptPreview?.isObjectUrl) {
        window.URL.revokeObjectURL(receiptPreview.url);
      }
    };
  }, [receiptPreview]);

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
      setError('فعلاً نمی‌توانیم گروه‌هایت را نشان بدهیم. چند لحظه بعد دوباره امتحان کن.');
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
        .filter(
          (response): response is PromiseFulfilledResult<UiExpense[]> =>
            response.status === 'fulfilled',
        )
        .map((response) => response.value);

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
      setError('فعلاً نمی‌توانیم فعالیت‌ها را نشان بدهیم. چند لحظه بعد دوباره امتحان کن.');
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
        const currentUserMember = members.find(
          (member) => getMemberUserId(member) === currentUserId,
        );

        const defaultPayer =
          prev.payerUserId ||
          (currentUserMember ? getMemberUserId(currentUserMember) : '') ||
          (members[0] ? getMemberUserId(members[0]) : '');

        const defaultParticipants = prev.participantUserIds.length
          ? prev.participantUserIds
          : members.map(getMemberUserId).filter((userId): userId is string => Boolean(userId));

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
        title: 'اعضای گروه نمایش داده نشدند',
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
      const normalizedSearch = normalizeText(searchTerm);

      if (selectedType === 'paid' && kind !== 'paid') return false;
      if (selectedType === 'received' && kind !== 'received') return false;
      if (selectedType === 'settled' && !isSettledExpense(expense)) return false;

      if (!normalizedSearch) return true;

      return [expense.title, expense.description, expense.groupTitle]
        .filter(Boolean)
        .some((value) => normalizeText(String(value)).includes(normalizedSearch));
    });
  }, [currentUserId, expenses, searchTerm, selectedType]);

  const groupedExpenses = useMemo(
    () => groupExpensesByDate(filteredExpenses),
    [filteredExpenses],
  );

  const selectedGroup = useMemo(
    () => groups.find((group) => matchesGroupSelection(group, selectedGroupId)),
    [groups, selectedGroupId],
  );

  const expenseTypeCounts = useMemo(() => {
    return expenses.reduce<Record<ActivityFilter, number>>(
      (acc, expense) => {
        const kind = getExpenseKind(expense, currentUserId);

        acc.all += 1;
        acc[kind] += 1;

        if (isSettledExpense(expense)) {
          acc.settled += 1;
        }

        return acc;
      },
      { all: 0, received: 0, paid: 0, settled: 0 },
    );
  }, [currentUserId, expenses]);

  const activeFilters = useMemo(() => {
    const filters: Array<{ key: string; label: string; onRemove: () => void }> = [];

    if (searchTerm.trim()) {
      filters.push({
        key: 'search',
        label: `جستجو: ${searchTerm.trim()}`,
        onRemove: () => setSearchTerm(''),
      });
    }

    if (selectedGroupId !== 'all') {
      filters.push({
        key: 'group',
        label: `گروه: ${selectedGroup ? getGroupTitle(selectedGroup) : 'انتخاب‌شده'}`,
        onRemove: () => setSelectedGroupId('all'),
      });
    }

    if (selectedType !== 'all') {
      filters.push({
        key: 'type',
        label: `نوع: ${getActivityFilterLabel(selectedType)}`,
        onRemove: () => setSelectedType('all'),
      });
    }

    if (fromDate) {
      filters.push({
        key: 'fromDate',
        label: `از ${formatCompactDateLabel(fromDate)}`,
        onRemove: () => setFromDate(''),
      });
    }

    if (toDate) {
      filters.push({
        key: 'toDate',
        label: `تا ${formatCompactDateLabel(toDate)}`,
        onRemove: () => setToDate(''),
      });
    }

    return filters;
  }, [fromDate, searchTerm, selectedGroup, selectedGroupId, selectedType, toDate]);

  const quickDateRanges = [
    { label: 'همه زمان‌ها', from: '', to: '' },
    { label: 'امروز', from: getRelativeDateInput(0), to: getRelativeDateInput(0) },
    { label: '۷ روز اخیر', from: getRelativeDateInput(6), to: getRelativeDateInput(0) },
    { label: '۳۰ روز اخیر', from: getRelativeDateInput(29), to: getRelativeDateInput(0) },
  ];

  const activityTypeOptions: Array<{
    value: ActivityFilter;
    label: string;
    icon: typeof ClipboardList;
  }> = [
    { value: 'all', label: 'همه', icon: ClipboardList },
    { value: 'received', label: 'طلب‌ها', icon: TrendingUp },
    { value: 'paid', label: 'پرداختی‌ها', icon: TrendingDown },
    { value: 'settled', label: 'تسویه‌شده‌ها', icon: CheckCircle2 },
  ];

  function resetFilters() {
    setSelectedGroupId('all');
    setSelectedType('all');
    setFromDate('');
    setToDate('');
    setSearchTerm('');
    setDateFiltersOpen(false);
  }

  function openCreateModal() {
    const firstActiveGroupId = groups.find(isActiveGroup)?.id || groups[0]?.id || '';
    const selectedGroupItem = groups.find((group) =>
      matchesGroupSelection(group, selectedGroupId),
    );

    const initialGroupId =
      selectedGroupId === 'all'
        ? String(firstActiveGroupId)
        : String(selectedGroupItem?.id || selectedGroupId);

    setAdvancedFormOpen(false);
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

  async function openDetailModal(expense: UiExpense) {
    const requestId = detailRequestId.current + 1;
    detailRequestId.current = requestId;

    try {
      setDetailLoading(true);
      setDetailExpense(null);

      const detail = await getExpenseDetail(expense.id);
      if (detailRequestId.current === requestId) {
        setDetailExpense({ ...detail, groupTitle: expense.groupTitle } as UiExpense);
      }
    } catch (loadError) {
      console.error(loadError);
      if (detailRequestId.current === requestId) {
        showToast({ tone: 'error', title: 'جزئیات این مورد نمایش داده نشد' });
      }
    } finally {
      if (detailRequestId.current === requestId) setDetailLoading(false);
    }
  }

  function closeDetailModal() {
    detailRequestId.current += 1;
    setDetailLoading(false);
    setDetailExpense(null);
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

  function buildExpensePayload(receiptFileId?: string) {
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
      participants: form.splitMethod === 'CUSTOM_AMOUNT' ? participants : undefined,
      tax_type: taxAmountMinor > 0 ? 'FIXED' : 'NONE',
      tax_amount_minor: taxAmountMinor,
      service_fee_type: serviceFeeAmountMinor > 0 ? 'FIXED' : 'NONE',
      service_fee_amount_minor: serviceFeeAmountMinor,
      expense_date: dateInputToIso(form.expenseDate),
      receipt_file_id: receiptFileId || form.receiptFileId || undefined,
      receipt_url: form.receiptUrl || undefined,
    };
  }

  async function uploadSelectedReceipt() {
    if (!form.receiptFile) {
      return form.receiptFileId || undefined;
    }

    const uploadedReceipt = await uploadReceipt({
      groupId: form.groupId,
      file: form.receiptFile,
    });

    return uploadedReceipt.id;
  }

  async function handlePreviewReceipt(expense: BackendExpense) {
    const receiptKey = getExpenseReceiptKey(expense);
    if (!receiptKey || !canCurrentUserSeeExpenseReceipt(expense, currentUserId)) {
      showToast({ tone: 'info', title: 'برای این هزینه هنوز رسیدی ثبت نشده است' });
      return;
    }

    try {
      setOpeningReceiptId(receiptKey);

      if (expense.receipt_file_id) {
        const downloaded = await downloadMediaFile(expense.receipt_file_id);
        const objectUrl = window.URL.createObjectURL(downloaded.blob);
        setReceiptPreview({
          expenseTitle: expense.title || 'هزینه',
          fileName: downloaded.fileName,
          url: objectUrl,
          contentType: downloaded.contentType,
          isObjectUrl: true,
        });
        return;
      }

      if (expense.receipt_url) {
        setReceiptPreview({
          expenseTitle: expense.title || 'هزینه',
          fileName: getFileNameFromUrl(expense.receipt_url),
          url: expense.receipt_url,
          contentType: inferReceiptContentTypeFromUrl(expense.receipt_url),
          isObjectUrl: false,
        });
      }
    } catch (receiptError) {
      console.error(receiptError);
      showToast({
        tone: 'error',
        title: 'رسید باز نشد',
        message: 'دسترسی به فایل رسید ممکن نیست یا فایل پیدا نشد.',
      });
    } finally {
      setOpeningReceiptId(null);
    }
  }

  async function handleDownloadReceipt(expense: BackendExpense) {
    const receiptKey = getExpenseReceiptKey(expense);
    if (!receiptKey || !canCurrentUserSeeExpenseReceipt(expense, currentUserId)) {
      showToast({ tone: 'info', title: 'برای این هزینه هنوز رسیدی ثبت نشده است' });
      return;
    }

    try {
      setOpeningReceiptId(receiptKey);

      if (expense.receipt_file_id) {
        const downloaded = await downloadMediaFile(expense.receipt_file_id);
        const objectUrl = window.URL.createObjectURL(downloaded.blob);
        const anchor = document.createElement('a');
        anchor.href = objectUrl;
        anchor.download = downloaded.fileName;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 60_000);
        return;
      }

      if (expense.receipt_url) {
        const anchor = document.createElement('a');
        anchor.href = expense.receipt_url;
        anchor.download = getFileNameFromUrl(expense.receipt_url);
        anchor.target = '_blank';
        anchor.rel = 'noopener noreferrer';
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
      }
    } catch (receiptError) {
      console.error(receiptError);
      showToast({
        tone: 'error',
        title: 'رسید دانلود نشد',
        message: 'دسترسی به فایل رسید ممکن نیست یا فایل پیدا نشد.',
      });
    } finally {
      setOpeningReceiptId(null);
    }
  }

  async function handleSubmitExpense(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!form.groupId) {
      showToast({ tone: 'error', title: 'اول گروه را انتخاب کن' });
      return;
    }

    if (!form.title.trim()) {
      showToast({ tone: 'error', title: 'برای هزینه یک عنوان بنویس' });
      return;
    }

    if (parseAmount(form.baseAmountMinor) <= 0) {
      showToast({ tone: 'error', title: 'مبلغ هزینه را وارد کن' });
      return;
    }

    if (!form.payerUserId) {
      showToast({ tone: 'error', title: 'مشخص کن چه کسی این هزینه را پرداخت کرده است' });
      return;
    }

    if (form.participantUserIds.length === 0) {
      showToast({ tone: 'error', title: 'حداقل یک نفر را به‌عنوان شریک هزینه انتخاب کن' });
      return;
    }

    try {
      setSubmitting(true);

      const receiptFileId = await uploadSelectedReceipt();
      const payload = buildExpensePayload(receiptFileId);

      await createGroupExpense(form.groupId, payload);
      showToast({ tone: 'success', title: 'هزینه ثبت شد' });

      setModalOpen(false);
      await loadExpenses();
    } catch (submitError) {
      console.error(submitError);
      showToast({
        tone: 'error',
        title: 'هزینه ثبت نشد',
        message: form.receiptFile ? 'اگر رسید انتخاب کرده‌ای، مطمئن شو فایل jpg، png، webp یا pdf و کمتر از ۵ مگابایت است.' : 'چند لحظه بعد دوباره امتحان کن. اگر رسید انتخاب کرده‌ای، نوع و حجم فایل را هم بررسی کن.',
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
      showToast({ tone: 'error', title: 'هزینه حذف نشد' });
    }
  }

  return (
    <main className="app-page pb-24">
      {toast ? <Toast toast={toast} onClose={() => setToast(null)} /> : null}

      <div className="app-container app-container-dashboard space-y-6">
        <div className="flex items-center justify-between gap-3 text-right">
          <h1 className="text-lg font-extrabold text-text sm:text-xl">فعالیت‌ها</h1>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={openCreateModal}
              className="hidden h-11 items-center justify-center gap-2 rounded-[16px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-5 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(0,168,107,0.2)] transition hover:-translate-y-0.5 sm:inline-flex"
            >
              <Plus className="h-4.5 w-4.5" />
              ثبت هزینه جدید
            </button>

            <button
              type="button"
              onClick={() => {
                void loadGroups();
              }}
              disabled={loadingGroups || loadingExpenses}
              className="inline-flex h-11 w-11 items-center justify-center rounded-[15px] border border-border bg-white text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              aria-label="بروزرسانی فعالیت‌ها"
            >
              <RefreshCw
                className={[
                  'h-4.5 w-4.5',
                  loadingGroups || loadingExpenses ? 'animate-spin' : '',
                ].join(' ')}
              />
            </button>
          </div>
        </div>

        <section className="space-y-6">
          <div className="rounded-[22px] border border-slate-200 bg-white p-3 shadow-[0_10px_28px_rgba(15,23,42,0.05)] sm:p-4">

            <div className="grid grid-cols-[minmax(0,1.2fr)_minmax(120px,0.8fr)] gap-2 sm:gap-3">
              <div>
                <label className="mb-2 flex items-center gap-2 text-xs font-extrabold text-slate-700">
                  <Search className="h-4 w-4 text-emerald-600" />
                  جستجو
                </label>

                <div className="relative">
                  <input
                    type="search"
                    dir="rtl"
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder="مثلاً شام، تاکسی، سفر شمال..."
                    aria-label="جستجو در فعالیت‌ها"
                    className="h-12 w-full rounded-[18px] border border-slate-200 bg-slate-50/60 pr-4 pl-11 text-sm font-semibold text-text shadow-sm outline-none transition placeholder:font-medium placeholder:text-slate-400 focus:border-slate-300 focus:bg-white focus:ring-4 focus:ring-slate-500/10"
                  />

                  {searchTerm ? (
                    <button
                      type="button"
                      onClick={() => setSearchTerm('')}
                      className="absolute left-3 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full border border-slate-100 bg-slate-50 text-slate-500 shadow-sm transition hover:border-rose-100 hover:bg-rose-50 hover:text-rose-500"
                      aria-label="پاک کردن جستجو"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
              </div>

              <div>
                <label className="mb-2 flex items-center gap-2 text-xs font-extrabold text-slate-700">
                  <Users className="h-4 w-4 text-emerald-600" />
                  گروه
                </label>

                <div className="relative">
                  <ChevronDown className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />

                  <select
                    value={selectedGroupId}
                    onChange={(event) => setSelectedGroupId(event.target.value)}
                    className="h-12 w-full appearance-none rounded-[18px] border border-slate-200 bg-slate-50/60 px-4 pl-10 text-sm font-extrabold text-text shadow-sm outline-none transition focus:border-slate-300 focus:bg-white focus:ring-4 focus:ring-slate-500/10"
                  >
                    <option value="all">همه گروه‌ها</option>
                    {groups.map((group) => (
                      <option key={group.id} value={getSelectedGroupValue(group)}>
                        {group.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="mt-3 flex gap-2 overflow-x-auto pb-1" aria-label="نوع فعالیت">
              {activityTypeOptions.map(({ value, label, icon: Icon }) => {
                const isActive = selectedType === value;

                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setSelectedType(value)}
                    aria-pressed={isActive}
                    className={`inline-flex h-10 shrink-0 items-center gap-2 rounded-full border px-3 text-xs font-extrabold transition ${
                      isActive
                        ? 'border-emerald-600 bg-emerald-600 text-white shadow-[0_7px_18px_rgba(16,185,129,0.18)]'
                        : 'border-slate-200 bg-slate-50 text-slate-700 hover:border-emerald-200 hover:bg-emerald-50'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{label}</span>
                    <span className={`rounded-full px-1.5 py-0.5 text-[10px] ${isActive ? 'bg-white/20' : 'bg-white'}`}>{toPersianNumber(expenseTypeCounts[value])}</span>
                  </button>
                );
              })}
            </div>

            <div className="mt-3 flex items-center justify-between gap-3 border-t border-slate-100 pt-3">
              <button
                type="button"
                onClick={() => setDateFiltersOpen((previous) => !previous)}
                className={`inline-flex h-10 items-center gap-2 rounded-full border px-3 text-xs font-extrabold transition ${fromDate || toDate ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-white text-slate-700'}`}
                aria-expanded={dateFiltersOpen}
              >
                <CalendarDays className="h-4 w-4" />
                بازه زمانی
                {fromDate || toDate ? <span className="h-2 w-2 rounded-full bg-emerald-500" /> : null}
              </button>

              <span className="text-xs font-bold text-muted">{toPersianNumber(filteredExpenses.length)} نتیجه</span>
            </div>

            {dateFiltersOpen ? <div className="mt-3 rounded-[18px] border border-slate-200 bg-slate-50/60 p-3">
              <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <label className="flex items-center gap-2 text-xs font-extrabold text-slate-700">
                  <CalendarDays className="h-4 w-4 text-emerald-600" />
                  زمان فعالیت
                </label>

                <div className="flex flex-wrap gap-1.5 sm:justify-end">
                  {quickDateRanges.map((range) => {
                    const isActive = fromDate === range.from && toDate === range.to;

                    return (
                      <button
                        key={range.label}
                        type="button"
                        onClick={() => {
                          setFromDate(range.from);
                          setToDate(range.to);
                        }}
                        className={[
                          'rounded-full border px-3 py-1.5 text-[11px] font-extrabold shadow-sm transition hover:-translate-y-0.5',
                          isActive
                            ? 'border-emerald-600 bg-emerald-600 text-white shadow-[0_8px_18px_rgba(16,185,129,0.22)]'
                            : 'border-slate-200 bg-slate-50/60 text-slate-700 hover:border-slate-300 hover:bg-white',
                        ].join(' ')}
                      >
                        {range.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                <div className="relative">
                  <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[11px] font-extrabold text-slate-500">
                    از
                  </span>

                  <input
                    type="date"
                    value={fromDate}
                    max={toDate || undefined}
                    onChange={(event) => setFromDate(event.target.value)}
                    className="h-12 w-full rounded-[18px] border border-slate-200 bg-slate-50/60 pr-9 pl-3 text-sm font-semibold text-text shadow-sm outline-none transition focus:border-slate-300 focus:bg-white focus:ring-4 focus:ring-slate-500/10"
                    title="از تاریخ"
                  />
                </div>

                <div className="relative">
                  <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[11px] font-extrabold text-slate-500">
                    تا
                  </span>

                  <input
                    type="date"
                    value={toDate}
                    min={fromDate || undefined}
                    onChange={(event) => setToDate(event.target.value)}
                    className="h-12 w-full rounded-[18px] border border-slate-200 bg-slate-50/60 pr-9 pl-3 text-sm font-semibold text-text shadow-sm outline-none transition focus:border-slate-300 focus:bg-white focus:ring-4 focus:ring-slate-500/10"
                    title="تا تاریخ"
                  />
                </div>
              </div>
            </div> : null}

            {activeFilters.length > 0 ? (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {activeFilters.map((filter) => (
                  <button
                    key={filter.key}
                    type="button"
                    onClick={filter.onRemove}
                    className="inline-flex h-8 items-center gap-1.5 rounded-full border border-emerald-100 bg-white px-3 text-xs font-extrabold text-emerald-700 shadow-sm transition hover:border-rose-100 hover:bg-rose-50 hover:text-rose-600"
                    title="حذف این فیلتر"
                  >
                    {filter.label}
                    <X className="h-3.5 w-3.5" />
                  </button>
                ))}
                <button type="button" onClick={resetFilters} className="inline-flex h-8 items-center gap-1 rounded-full px-2 text-xs font-extrabold text-rose-600 transition hover:bg-rose-50">
                  <RefreshCw className="h-3.5 w-3.5" /> پاک کردن همه
                </button>
              </div>
            ) : null}
          </div>

          {error ? (
            <div className="rounded-[24px] border border-rose-100 bg-rose-50 p-6 text-center text-sm font-semibold text-rose-600">
              {error}
            </div>
          ) : null}

          {loadingGroups || loadingExpenses ? (
            <div className="flex min-h-[240px] items-center justify-center rounded-[24px] border border-border bg-white p-8 text-muted shadow-soft">
              <Loader2 className="ml-2 h-5 w-5 animate-spin" />
              در حال دریافت فعالیت‌ها...
            </div>
          ) : null}

          {!loadingGroups && !loadingExpenses && filteredExpenses.length === 0 ? (
            <EmptyState onCreate={openCreateModal} filtered={expenses.length > 0 || activeFilters.length > 0} onClear={resetFilters} />
          ) : null}

          {!loadingGroups && !loadingExpenses && filteredExpenses.length > 0 ? (
            <div className="space-y-5">
              {Object.entries(groupedExpenses).map(([dateLabel, dateExpenses]) => (
                <div key={dateLabel} className="space-y-3">
                  <h2 className="px-1 text-right text-base font-extrabold text-text sm:text-lg">
                    {dateLabel}
                  </h2>

                  <div className="rounded-[20px] border border-border bg-white shadow-soft">
                    {dateExpenses.map((expense, index) => {
                      const kind = getExpenseKind(expense, currentUserId);
                      const total = getExpenseTotal(expense);
                      const amount = kind === 'paid' ? -total : total;

                      const payerParticipant = expense.participants?.find(
                        (participant) => participant.user_id === expense.payer_user_id,
                      );

                      return (
                        <div
                          key={expense.id}
                          className={`relative flex items-center transition hover:bg-slate-50/70 ${index !== 0 ? 'border-t border-border' : ''}`}
                        >
                          <button
                            type="button"
                            onClick={() => {
                              setOpenActionMenuId(null);
                              void openDetailModal(expense);
                            }}
                            className="flex min-w-0 flex-1 items-center gap-3 px-3 py-3 text-right sm:px-4 sm:py-3.5"
                          >
                            <div
                              className={[
                                'flex h-11 w-11 shrink-0 items-center justify-center rounded-[15px]',
                                kind === 'paid'
                                  ? 'bg-rose-50 text-rose-500'
                                  : 'bg-emerald-50 text-emerald-600',
                              ].join(' ')}
                            >
                              {kind === 'paid' ? (
                                <TrendingDown className="h-5 w-5" />
                              ) : (
                                <TrendingUp className="h-5 w-5" />
                              )}
                            </div>

                            <div className="min-w-0 flex-1">
                              <div className="truncate text-sm font-extrabold text-text sm:text-base">
                                {expense.title}
                              </div>

                              <div className="mt-1 flex min-w-0 items-center gap-1.5 text-[11px] font-semibold text-muted sm:text-xs">
                                <span className="truncate">{expense.groupTitle || 'گروه'}</span>
                                <span aria-hidden="true">·</span>
                                <span className="hidden truncate sm:inline">{getParticipantName(payerParticipant)}</span>
                                <span className="hidden sm:inline" aria-hidden="true">·</span>
                                <span className="shrink-0">{formatTime(expense.expense_date || expense.created_at)}</span>
                              </div>
                            </div>

                            <div className="shrink-0 text-left">
                              <div className={`text-sm font-extrabold sm:text-base ${amount >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>{formatSignedMoney(amount)}</div>
                              <div className="mt-1 text-[10px] font-bold text-muted">{kind === 'paid' ? 'پرداختی' : 'طلب'}</div>
                            </div>
                          </button>

                          <div className="relative ml-2 shrink-0">
                            <button
                              type="button"
                              onClick={() => setOpenActionMenuId((current) => current === expense.id ? null : expense.id)}
                              className="flex h-10 w-10 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100"
                              aria-label={`گزینه‌های ${expense.title}`}
                              aria-expanded={openActionMenuId === expense.id}
                            >
                              <MoreVertical className="h-5 w-5" />
                            </button>

                            {openActionMenuId === expense.id ? (
                              <div className="absolute left-0 top-11 z-20 w-40 overflow-hidden rounded-[16px] border border-slate-200 bg-white p-1.5 text-right shadow-[0_16px_40px_rgba(15,23,42,0.16)]">
                                {canCurrentUserSeeExpenseReceipt(expense, currentUserId) ? (
                                  <>
                                    <button type="button" onClick={() => { setOpenActionMenuId(null); void handlePreviewReceipt(expense); }} className="flex h-10 w-full items-center gap-2 rounded-[11px] px-3 text-xs font-bold text-sky-700 hover:bg-sky-50">
                                      {openingReceiptId === getExpenseReceiptKey(expense) ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
                                      مشاهده رسید
                                    </button>
                                    <button type="button" onClick={() => { setOpenActionMenuId(null); void handleDownloadReceipt(expense); }} className="flex h-10 w-full items-center gap-2 rounded-[11px] px-3 text-xs font-bold text-slate-700 hover:bg-slate-50">
                                      <Download className="h-4 w-4" />
                                      دانلود رسید
                                    </button>
                                  </>
                                ) : null}
                                <button type="button" onClick={() => { setOpenActionMenuId(null); setDeleteTarget(expense); }} className="flex h-10 w-full items-center gap-2 rounded-[11px] px-3 text-xs font-bold text-rose-600 hover:bg-rose-50"><Trash2 className="h-4 w-4" />حذف</button>
                              </div>
                            ) : null}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </section>
      </div>

      <button
        type="button"
        onClick={openCreateModal}
        className="fixed bottom-5 left-4 z-30 inline-flex h-14 items-center gap-2 rounded-full bg-gradient-to-l from-[#00915F] to-[#00A86B] px-5 text-sm font-extrabold text-white shadow-[0_16px_36px_rgba(0,145,95,0.32)] sm:hidden"
      >
        <Plus className="h-5 w-5" />
        ثبت هزینه
      </button>

      {modalOpen ? (
        <div className="fixed inset-0 z-40 flex items-end justify-center overflow-y-auto bg-slate-900/40 p-0 backdrop-blur-sm sm:items-center sm:p-4">
          <div className="max-h-[92dvh] w-full max-w-[840px] overflow-y-auto rounded-t-[28px] border border-border bg-white p-4 shadow-[0_24px_80px_rgba(15,23,42,0.22)] sm:rounded-[28px] sm:p-6">
            <div className="mb-5 flex items-start justify-between gap-4 sm:mb-6">
              <div className="text-right">
                <h2 className="text-xl font-extrabold text-text">ثبت هزینه جدید</h2>
              </div>

              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[16px] bg-slate-50 text-slate-600 transition hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitExpense} className="space-y-4 sm:space-y-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">
                    گروه
                  </label>

                  <select
                    value={form.groupId}
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
                      <option key={group.id} value={getSelectedGroupValue(group)}>
                        {group.title}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">
                    پرداخت‌کننده
                  </label>

                  <select
                    value={form.payerUserId}
                    onChange={(event) =>
                      setForm((prev) => ({ ...prev, payerUserId: event.target.value }))
                    }
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  >
                    <option value="">انتخاب پرداخت‌کننده</option>
                    {modalMembers.map((member) => {
                      const userId = getMemberUserId(member);
                      if (!userId) return null;

                      return (
                        <option key={member.id || userId} value={userId}>
                          {getMemberName(member)}
                        </option>
                      );
                    })}
                  </select>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">
                    عنوان هزینه
                  </label>

                  <input
                    dir="rtl"
                    value={form.title}
                    onChange={(event) =>
                      setForm((prev) => ({ ...prev, title: event.target.value }))
                    }
                    placeholder="مثلاً شام گروهی"
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">
                    مبلغ هزینه
                  </label>

                  <input
                    dir="ltr"
                    inputMode="numeric"
                    value={form.baseAmountMinor}
                    onChange={(event) =>
                      setForm((prev) => ({ ...prev, baseAmountMinor: event.target.value }))
                    }
                    placeholder="مثلاً ۹۰۰٬۰۰۰"
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-left text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>
              </div>

              <div className="max-w-[320px]">
                <label className="mb-2 block text-sm font-semibold text-text">روش تقسیم</label>
                <select
                  value={form.splitMethod}
                  onChange={(event) => setForm((prev) => ({ ...prev, splitMethod: event.target.value as ExpenseSplitMethod }))}
                  className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                >
                  <option value="EQUAL">مساوی</option>
                  <option value="CUSTOM_AMOUNT">سفارشی</option>
                </select>
              </div>

              <button
                type="button"
                onClick={() => setAdvancedFormOpen((previous) => !previous)}
                className="flex h-11 w-full items-center justify-between rounded-[15px] border border-slate-200 bg-slate-50 px-4 text-sm font-bold text-slate-700 transition hover:border-emerald-200 hover:bg-emerald-50"
                aria-expanded={advancedFormOpen}
              >
                <span>جزئیات بیشتر <span className="font-semibold text-muted">(اختیاری)</span></span>
                <ChevronDown className={`h-4 w-4 transition ${advancedFormOpen ? 'rotate-180' : ''}`} />
              </button>

              <div className={advancedFormOpen ? '' : 'hidden'}>
                <label className="mb-2 block text-sm font-semibold text-text">
                  توضیحات
                </label>

                <textarea
                  dir="rtl"
                  value={form.description}
                  onChange={(event) =>
                    setForm((prev) => ({ ...prev, description: event.target.value }))
                  }
                  className="min-h-[96px] w-full resize-none rounded-2xl border border-border bg-white px-4 py-3 text-sm leading-7 text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className={advancedFormOpen ? '' : 'hidden'}>
                  <label className="mb-2 block text-sm font-semibold text-text">
                    مالیات
                  </label>

                  <input
                    dir="ltr"
                    inputMode="numeric"
                    value={form.taxAmountMinor}
                    onChange={(event) =>
                      setForm((prev) => ({ ...prev, taxAmountMinor: event.target.value }))
                    }
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-left text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>

                <div className={advancedFormOpen ? '' : 'hidden'}>
                  <label className="mb-2 block text-sm font-semibold text-text">
                    کارمزد سرویس
                  </label>

                  <input
                    dir="ltr"
                    inputMode="numeric"
                    value={form.serviceFeeAmountMinor}
                    onChange={(event) =>
                      setForm((prev) => ({
                        ...prev,
                        serviceFeeAmountMinor: event.target.value,
                      }))
                    }
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-left text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>

                <div className={advancedFormOpen ? '' : 'hidden'}>
                  <label className="mb-2 block text-sm font-semibold text-text">
                    تاریخ هزینه
                  </label>

                  <input
                    type="datetime-local"
                    value={form.expenseDate}
                    onChange={(event) =>
                      setForm((prev) => ({ ...prev, expenseDate: event.target.value }))
                    }
                    className="h-12 w-full rounded-2xl border border-border bg-white px-3 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>
              </div>

              <div>
                <div className="mb-3 flex items-center justify-between">
                  <label className="text-sm font-semibold text-text">شرکت‌کننده‌ها</label>

                  {membersLoading ? (
                    <span className="text-xs text-muted">در حال دریافت اعضا...</span>
                  ) : null}
                </div>

                <div className="max-h-[260px] space-y-2 overflow-y-auto rounded-[18px] border border-slate-100 p-2 sm:grid sm:grid-cols-2 sm:gap-2 sm:space-y-0">
                  {modalMembers.map((member) => {
                    const userId = getMemberUserId(member);
                    if (!userId) return null;

                    const checked = form.participantUserIds.includes(userId);

                    return (
                      <div
                        key={member.id || userId}
                        className={[
                          'rounded-2xl border p-3 transition',
                          checked
                            ? 'border-emerald-200 bg-emerald-50/60'
                            : 'border-border bg-white',
                        ].join(' ')}
                      >
                        <label className="flex cursor-pointer items-center gap-3 text-right">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleParticipant(userId)}
                            className="h-4 w-4 accent-emerald-600"
                          />

                          <span className="flex-1 text-sm font-semibold text-text">
                            {getMemberName(member)}
                          </span>
                        </label>

                        {form.splitMethod === 'CUSTOM_AMOUNT' && checked ? (
                          <input
                            dir="ltr"
                            inputMode="numeric"
                            value={form.customShares[userId] || ''}
                            onChange={(event) =>
                              setForm((prev) => ({
                                ...prev,
                                customShares: {
                                  ...prev.customShares,
                                  [userId]: event.target.value,
                                },
                              }))
                            }
                            placeholder="سهم این نفر"
                            className="mt-3 h-10 w-full rounded-xl border border-border bg-white px-3 text-left text-xs outline-none focus:border-emerald-500/50"
                          />
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className={advancedFormOpen ? '' : 'hidden'}>
                <label className="mb-2 block text-sm font-semibold text-text">
                  رسید هزینه
                </label>

                <div className="rounded-2xl border border-dashed border-emerald-200 bg-emerald-50/35 p-3">
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    onChange={(event) => {
                      const file = event.target.files?.[0] || null;

                      setForm((prev) => ({
                        ...prev,
                        receiptFile: file,
                        receiptFileName: file?.name || '',
                      }));
                    }}
                    className="block w-full cursor-pointer rounded-xl border border-emerald-100 bg-white text-sm text-slate-600 file:ml-4 file:cursor-pointer file:border-0 file:bg-emerald-600 file:px-4 file:py-3 file:text-sm file:font-bold file:text-white hover:file:bg-emerald-700"
                  />

                  <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
                    <span>
                      {form.receiptFileName
                        ? `فایل انتخاب‌شده: ${form.receiptFileName}`
                        : form.receiptFileId
                          ? 'رسید قبلی برای این هزینه ثبت شده است.'
                          : 'فرمت‌های مجاز: jpg، png، webp، pdf'}
                    </span>

                    {form.receiptFileId ? (
                      <button
                        type="button"
                        onClick={() => void handlePreviewReceipt({ id: 'receipt-form-preview', group_id: form.groupId, title: 'رسید فعلی', payer_user_id: currentUserId || '', base_amount_minor: 0, receipt_file_id: form.receiptFileId } as BackendExpense)}
                        className="rounded-xl bg-white px-3 py-1.5 font-bold text-emerald-700 shadow-sm transition hover:bg-emerald-50"
                      >
                        مشاهده رسید فعلی
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>

              <div className="sticky bottom-0 -mx-4 flex flex-col-reverse gap-2 border-t border-slate-100 bg-white/95 px-4 pt-3 pb-1 backdrop-blur sm:static sm:mx-0 sm:flex-row sm:justify-end sm:border-0 sm:bg-transparent sm:p-0">
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
                  {submitting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4" />
                  )}

                  ثبت هزینه
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {receiptPreview ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center overflow-y-auto bg-slate-900/40 p-0 backdrop-blur-sm sm:items-center sm:p-4">
          <div className="max-h-[92dvh] w-full max-w-[820px] overflow-y-auto rounded-t-[28px] border border-border bg-white p-4 text-right shadow-[0_24px_80px_rgba(15,23,42,0.22)] sm:rounded-[28px] sm:p-6">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-extrabold text-text">مشاهده رسید</h2>
                <p className="mt-1 text-xs font-semibold text-muted">رسید هزینه «{receiptPreview.expenseTitle}»</p>
              </div>

              <button
                type="button"
                onClick={() => setReceiptPreview(null)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[16px] bg-slate-50 text-slate-600 transition hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="overflow-hidden rounded-3xl border border-border bg-slate-50">
              {isImageReceipt(receiptPreview.contentType, receiptPreview.url) ? (
                <img src={receiptPreview.url} alt={`رسید هزینه ${receiptPreview.expenseTitle}`} className="max-h-[65vh] w-full object-contain" />
              ) : isPdfReceipt(receiptPreview.contentType, receiptPreview.url) ? (
                <iframe title={`رسید هزینه ${receiptPreview.expenseTitle}`} src={receiptPreview.url} className="h-[65vh] w-full bg-white" />
              ) : (
                <div className="flex min-h-[240px] flex-col items-center justify-center p-6 text-center">
                  <ClipboardList className="h-10 w-10 text-slate-400" />
                  <p className="mt-3 text-sm font-extrabold text-text">این نوع فایل پیش‌نمایش مستقیم ندارد.</p>
                  <p className="mt-2 text-xs leading-6 text-muted">برای مشاهده کامل، فایل را در تب جدید باز کنید یا دانلود کنید.</p>
                </div>
              )}
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <p title={receiptPreview.fileName} className="min-w-0 flex-1 truncate text-xs font-bold text-muted">{receiptPreview.fileName || 'receipt'}</p>
              <div className="flex flex-wrap gap-2">
                <a href={receiptPreview.url} target="_blank" rel="noopener noreferrer" className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-sky-600 px-4 text-xs font-bold text-white transition hover:bg-sky-700"><Eye className="h-4 w-4" />باز کردن در تب جدید</a>
                <a href={receiptPreview.url} download={receiptPreview.fileName || 'receipt'} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-border bg-white px-4 text-xs font-bold text-slate-700 transition hover:bg-slate-50"><Download className="h-4 w-4" />دانلود</a>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {detailExpense || detailLoading ? (
        <div className="fixed inset-0 z-40 flex items-end justify-center overflow-y-auto bg-slate-900/40 p-0 backdrop-blur-sm sm:items-center sm:p-4">
          <div className="max-h-[92dvh] w-full max-w-[620px] overflow-y-auto rounded-t-[28px] border border-border bg-white p-4 shadow-[0_24px_80px_rgba(15,23,42,0.22)] sm:rounded-[28px] sm:p-6">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="text-right">
                <h2 className="text-xl font-extrabold text-text">جزئیات هزینه</h2>
              </div>

              <button
                type="button"
                onClick={closeDetailModal}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[16px] bg-slate-50 text-slate-600 transition hover:bg-slate-100"
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
                <div className="rounded-[22px] bg-emerald-50 p-5">
                  <h3 className="text-xl font-extrabold text-text">
                    {detailExpense.title}
                  </h3>

                  <p className="mt-2 text-sm leading-7 text-muted">
                    {detailExpense.description || 'بدون توضیح'}
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-border p-4">
                    <span className="text-xs text-muted">مبلغ هزینه</span>
                    <div className="mt-2 font-extrabold text-text">
                      <MoneyWithWords amount={detailExpense.base_amount_minor} valueClassName="font-extrabold text-text" textClassName="mt-1 text-[10px] font-semibold text-slate-500" showText={true} />
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border p-4">
                    <span className="text-xs text-muted">مبلغ کل</span>
                    <div className="mt-2 font-extrabold text-emerald-600">
                      <MoneyWithWords amount={getExpenseTotal(detailExpense)} valueClassName="font-extrabold text-emerald-600" textClassName="mt-1 text-[10px] font-semibold text-slate-500" showText={true} />
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border p-4">
                    <span className="text-xs text-muted">روش تقسیم</span>
                    <div className="mt-2 font-extrabold text-text">
                      {humanizeMachineLabel(detailExpense.split_method, 'نامشخص')}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border p-4">
                    <span className="text-xs text-muted">وضعیت</span>
                    <div className="mt-2 font-extrabold text-text">
                      {humanizeMachineLabel(detailExpense.status, 'نامشخص')}
                    </div>
                  </div>
                </div>

                {canCurrentUserSeeExpenseReceipt(detailExpense, currentUserId) ? (
                  <div className="rounded-2xl border border-sky-100 bg-sky-50/70 p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <span className="text-xs font-bold text-sky-700">رسید هزینه</span>
                        <div className="mt-1 text-sm font-semibold text-text">برای این هزینه رسید ثبت شده است.</div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => void handlePreviewReceipt(detailExpense)}
                          disabled={openingReceiptId === getExpenseReceiptKey(detailExpense)}
                          className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-sky-600 px-4 text-xs font-bold text-white transition hover:bg-sky-700 disabled:opacity-60"
                        >
                          {openingReceiptId === getExpenseReceiptKey(detailExpense) ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
                          مشاهده
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDownloadReceipt(detailExpense)}
                          disabled={openingReceiptId === getExpenseReceiptKey(detailExpense)}
                          className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-sky-200 bg-white px-4 text-xs font-bold text-sky-700 transition hover:bg-sky-50 disabled:opacity-60"
                        >
                          <Download className="h-4 w-4" />
                          دانلود
                        </button>
                      </div>
                    </div>
                  </div>
                ) : null}

                <div>
                  <h4 className="mb-3 font-extrabold text-text">شرکت‌کننده‌ها</h4>

                  <div className="space-y-2">
                    {(detailExpense.participants || []).map((participant) => (
                      <div
                        key={participant.user_id}
                        className="flex items-center justify-between rounded-2xl border border-border px-4 py-3 text-sm"
                      >
                        <span className="font-semibold text-text">
                          {getParticipantName(participant)}
                        </span>

                        <span className="font-bold text-emerald-600">
                          <MoneyWithWords
                            amount={participant.total_share_minor || participant.base_share_minor || 0}
                            valueClassName="font-bold text-emerald-600"
                            textClassName="mt-1 text-[10px] font-semibold text-slate-500"
                            showText={true}
                          />
                        </span>
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
          <div className="w-full max-w-[420px] rounded-t-[28px] border border-rose-100 bg-white p-5 text-right shadow-[0_24px_80px_rgba(15,23,42,0.22)] sm:rounded-[28px] sm:p-6">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-[16px] bg-rose-50 text-rose-600">
              <Trash2 className="h-5 w-5" />
            </div>

            <h2 className="text-xl font-extrabold text-text">حذف هزینه</h2>

            <p className="mt-2 text-sm leading-7 text-muted">
              هزینه «{deleteTarget.title}» به صورت soft delete حذف می‌شود. ادامه می‌دهی؟
            </p>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="h-11 flex-1 rounded-2xl border border-border bg-white text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                انصراف
              </button>

              <button
                type="button"
                onClick={handleDeleteExpense}
                className="h-11 flex-1 rounded-2xl bg-rose-600 text-sm font-semibold text-white transition hover:bg-rose-700"
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
