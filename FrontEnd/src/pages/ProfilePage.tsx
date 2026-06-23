import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  AlertCircle,
  Bell,
  Calendar,
  Camera,
  Check,
  CheckCircle2,
  Clock3,
  CreditCard,
  Database,
  Download,
  Eye,
  EyeOff,
  Loader2,
  FileText,
  Laptop,
  Lock,
  Mail,
  MapPin,
  Monitor,
  Phone,
  Plus,
  Save,
  Shield,
  Smartphone,
  Trash2,
  User,
  UserPlus,
  Users,
  WalletCards,
  type LucideIcon,
} from 'lucide-react';
import { isApiError } from '../lib/api';
import {
  changePassword,
  getCurrentUser,
  setPassword,
  updateCurrentUserProfile,
  checkArtNameAvailability,
  type CurrentUser,
} from '../lib/userApi';

type ProfileTab = 'personal' | 'security' | 'notifications' | 'privacy';
type MessageTone = 'neutral' | 'success' | 'error';

interface BankCardField {
  id: number;
  number: string;
}

interface NotificationSettings {
  paymentConfirmed: boolean;
  memberPayments: boolean;
  settlementCompleted: boolean;
  groupInvites: boolean;
  newExpenses: boolean;
  receiptUploads: boolean;
  inApp: boolean;
  email: boolean;
  browser: boolean;
  quietHours: boolean;
  quietStart: string;
  quietEnd: string;
  debtReminder: boolean;
  firstReminder: string;
  repeatReminder: string;
}

interface PrivacySettings {
  phoneVisibility: 'self' | 'members';
  emailVisibility: 'self' | 'members';
  avatarVisibility: 'self' | 'members';
  searchableByPhone: boolean;
  directInvites: boolean;
  confirmBeforeJoin: boolean;
  receiptsVisibleToMembers: boolean;
  receiptsVisibleToParticipantsOnly: boolean;
}

const profileTabs: Array<{ id: ProfileTab; label: string }> = [
  { id: 'personal', label: 'اطلاعات شخصی' },
  { id: 'security', label: 'امنیت' },
  { id: 'notifications', label: 'تنظیمات اعلان‌ها' },
  { id: 'privacy', label: 'حریم خصوصی' },
];

const defaultNotificationSettings: NotificationSettings = {
  paymentConfirmed: true,
  memberPayments: true,
  settlementCompleted: true,
  groupInvites: true,
  newExpenses: true,
  receiptUploads: true,
  inApp: true,
  email: true,
  browser: false,
  quietHours: true,
  quietStart: '22:00',
  quietEnd: '08:00',
  debtReminder: true,
  firstReminder: '24',
  repeatReminder: '48',
};

const defaultPrivacySettings: PrivacySettings = {
  phoneVisibility: 'self',
  emailVisibility: 'self',
  avatarVisibility: 'self',
  searchableByPhone: false,
  directInvites: true,
  confirmBeforeJoin: true,
  receiptsVisibleToMembers: true,
  receiptsVisibleToParticipantsOnly: true,
};

const bankPrefixes: Record<string, string> = {
  '603799': 'بانک ملی ایران',
  '589210': 'بانک سپه',
  '603770': 'بانک کشاورزی',
  '628023': 'بانک مسکن',
  '627760': 'پست بانک ایران',
  '622106': 'بانک پارسیان',
  '627884': 'بانک پارسیان',
  '639194': 'بانک پارسیان',
  '502229': 'بانک پاسارگاد',
  '639347': 'بانک پاسارگاد',
  '621986': 'بانک سامان',
  '502806': 'بانک شهر',
  '504706': 'بانک شهر',
  '502938': 'بانک دی',
  '603769': 'بانک صادرات ایران',
  '610433': 'بانک ملت',
  '991975': 'بانک ملت',
  '589463': 'بانک رفاه کارگران',
  '627353': 'بانک تجارت',
  '585983': 'بانک تجارت',
  '636214': 'بانک آینده',
  '505416': 'بانک گردشگری',
  '505785': 'بانک ایران زمین',
  '606373': 'بانک قرض‌الحسنه مهر ایران',
  '504172': 'بانک قرض‌الحسنه رسالت',
};

function safeReadStorage<T>(key: string, fallback: T): T {
  try {
    const value = localStorage.getItem(key);
    if (!value) return fallback;

    const parsed = JSON.parse(value);

    if (Array.isArray(fallback)) {
      return (Array.isArray(parsed) ? parsed : fallback) as T;
    }

    if (
      fallback &&
      typeof fallback === 'object' &&
      parsed &&
      typeof parsed === 'object' &&
      !Array.isArray(parsed)
    ) {
      return { ...fallback, ...parsed } as T;
    }

    return parsed as T;
  } catch {
    return fallback;
  }
}

function useStoredState<T>(key: string, fallback: T) {
  const [value, setValue] = useState<T>(() => safeReadStorage(key, fallback));

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue] as const;
}

function getApiErrorCode(error: unknown) {
  if (!isApiError(error)) return '';
  const body = error.body as { error?: { code?: unknown } } | undefined;
  return typeof body?.error?.code === 'string' ? body.error.code : '';
}

function getDisplayName(user: CurrentUser | null) {
  if (!user) return 'کاربر همدنگ';

  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
  return user.display_name || fullName || user.art_name || user.email || 'کاربر همدنگ';
}

function getUsername(user: CurrentUser | null) {
  return user?.art_name || user?.username || '';
}

function getEmail(user: CurrentUser | null) {
  return user?.email || (user?.username?.includes('@') ? user.username : '') || '';
}

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.slice(0, 1))
    .join('');
}

function formatDate(value?: string | null) {
  if (!value) return 'ثبت نشده';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'ثبت نشده';

  return date.toLocaleDateString('fa-IR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function toEnglishDigits(value: string) {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)));
}

function normalizeCardDigits(value: string) {
  return toEnglishDigits(value).replace(/\D/g, '').slice(0, 16);
}

function formatCardNumber(value: string) {
  return normalizeCardDigits(value).replace(/(.{4})/g, '$1 ').trim();
}

function getBankName(value: string) {
  const digits = normalizeCardDigits(value);
  if (digits.length < 6) return '';
  return bankPrefixes[digits.slice(0, 6)] || '';
}

function getPasswordStrength(value: string) {
  let score = 0;
  if (value.length >= 8) score += 1;
  if (/[A-Z]/.test(value)) score += 1;
  if (/[a-z]/.test(value)) score += 1;
  if (/\d/.test(value)) score += 1;
  if (/[^A-Za-z0-9]/.test(value)) score += 1;

  if (score >= 4) return { label: 'قوی', className: 'bg-emerald-50 text-emerald-700' };
  if (score >= 3) return { label: 'متوسط', className: 'bg-amber-50 text-amber-700' };
  return { label: 'ضعیف', className: 'bg-rose-50 text-rose-600' };
}

const artNamePattern = /^[\w\-\u0600-\u06FF]{3,32}$/u;

type ArtNameStatus = 'idle' | 'checking' | 'available' | 'taken' | 'invalid' | 'error';

function normalizeArtName(value: string) {
  return value.trim();
}

function getArtNameValidationMessage(value: string) {
  const normalized = normalizeArtName(value);

  if (!normalized) {
    return 'نام کاربری نمی‌تواند خالی باشد.';
  }

  if (!artNamePattern.test(normalized)) {
    return 'نام کاربری باید بین ۳ تا ۳۲ کاراکتر و بدون فاصله باشد.';
  }

  return '';
}

function getArtNameFeedback(status: ArtNameStatus, fallback = '') {
  if (status === 'checking') {
    return {
      tone: 'neutral' as const,
      message: 'در حال بررسی نام کاربری...',
    };
  }

  if (status === 'available') {
    return {
      tone: 'success' as const,
      message: fallback || 'این نام کاربری قابل استفاده است.',
    };
  }

  if (status === 'taken') {
    return {
      tone: 'error' as const,
      message: fallback || 'این نام کاربری قبلاً ثبت شده است.',
    };
  }

  if (status === 'invalid') {
    return {
      tone: 'warning' as const,
      message: fallback || 'نام کاربری باید بین ۳ تا ۳۲ کاراکتر و بدون فاصله باشد.',
    };
  }

  if (status === 'error') {
    return {
      tone: 'warning' as const,
      message: fallback || 'بررسی نام کاربری انجام نشد. هنگام ذخیره دوباره بررسی می‌شود.',
    };
  }

  return {
    tone: 'neutral' as const,
    message: fallback,
  };
}

function FieldShell({
  label,
  icon: Icon,
  children,
  helper,
}: {
  label: string;
  icon: LucideIcon;
  children: ReactNode;
  helper?: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-right text-sm font-black text-slate-700">{label}</span>
      <div className="flex min-h-12 w-full items-center gap-3 rounded-2xl border border-border bg-white px-4 text-slate-700 shadow-sm transition focus-within:border-emerald-500/50 focus-within:ring-4 focus-within:ring-emerald-500/10">
        <Icon className="h-4.5 w-4.5 shrink-0 text-slate-500" />
        {children}
      </div>
      {helper ? <p className="mt-2 text-right text-xs font-bold leading-6 text-slate-500">{helper}</p> : null}
    </label>
  );
}

function TextInput({
  label,
  value,
  icon,
  onChange,
  dir = 'rtl',
  type = 'text',
  placeholder = '',
  helper,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  onChange: (value: string) => void;
  dir?: 'rtl' | 'ltr';
  type?: string;
  placeholder?: string;
  helper?: string;
}) {
  return (
    <FieldShell label={label} icon={icon} helper={helper}>
      <input
        dir={dir}
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className="h-12 min-w-0 flex-1 border-0 bg-transparent text-sm font-semibold text-slate-700 outline-none placeholder:text-slate-300"
      />
    </FieldShell>
  );
}

function ArtNameInput({
  value,
  onChange,
  status,
  message,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  status: ArtNameStatus;
  message: string;
  disabled?: boolean;
}) {
  const feedback = getArtNameFeedback(status, message);
  const feedbackClassName =
    feedback.tone === 'success'
      ? 'text-emerald-600'
      : feedback.tone === 'error'
        ? 'text-rose-600'
        : feedback.tone === 'warning'
          ? 'text-amber-600'
          : 'text-slate-500';

  return (
    <label className="block">
      <span className="mb-2 block text-right text-sm font-black text-slate-700">نام کاربری</span>
      <div className="flex min-h-12 w-full items-center gap-3 rounded-2xl border border-border bg-white px-4 text-slate-700 shadow-sm transition focus-within:border-emerald-500/50 focus-within:ring-4 focus-within:ring-emerald-500/10">
        <CheckCircle2 className="h-4.5 w-4.5 shrink-0 text-slate-500" />
        <input
          dir="ltr"
          type="text"
          value={value}
          disabled={disabled}
          placeholder="username"
          onChange={(event) => onChange(event.target.value)}
          className="h-12 min-w-0 flex-1 border-0 bg-transparent text-sm font-semibold text-slate-700 outline-none placeholder:text-slate-300"
        />
        {status === 'checking' ? (
          <Loader2 className="h-4.5 w-4.5 shrink-0 animate-spin text-slate-400" />
        ) : status === 'available' ? (
          <CheckCircle2 className="h-4.5 w-4.5 shrink-0 text-emerald-600" />
        ) : status === 'taken' || status === 'invalid' || status === 'error' ? (
          <AlertCircle className="h-4.5 w-4.5 shrink-0 text-amber-600" />
        ) : null}
      </div>
      {feedback.message ? (
        <p className={`mt-2 text-right text-xs font-bold leading-6 ${feedbackClassName}`}>{feedback.message}</p>
      ) : null}
    </label>
  );
}

function TextArea({
  label,
  value,
  icon,
  onChange,
  maxLength,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  onChange: (value: string) => void;
  maxLength?: number;
}) {
  const Icon = icon;

  return (
    <label className="block md:col-span-2">
      <span className="mb-2 block text-right text-sm font-black text-slate-700">{label}</span>
      <div className="flex min-h-[104px] w-full items-start gap-3 rounded-2xl border border-border bg-white px-4 py-3 text-slate-700 shadow-sm transition focus-within:border-emerald-500/50 focus-within:ring-4 focus-within:ring-emerald-500/10">
        <Icon className="mt-1 h-4.5 w-4.5 shrink-0 text-slate-500" />
        <textarea
          dir="rtl"
          value={value}
          maxLength={maxLength}
          onChange={(event) => onChange(event.target.value)}
          className="min-h-[76px] min-w-0 flex-1 resize-none border-0 bg-transparent text-right text-sm font-semibold leading-7 text-slate-700 outline-none"
        />
      </div>
      {maxLength ? (
        <p className="mt-2 text-left text-xs font-bold text-slate-500">
          {value.length.toLocaleString('fa-IR')}/{maxLength.toLocaleString('fa-IR')}
        </p>
      ) : null}
    </label>
  );
}

function ReadOnlyField({
  label,
  value,
  icon,
  dir = 'rtl',
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  dir?: 'rtl' | 'ltr';
}) {
  return (
    <FieldShell label={label} icon={icon}>
      <div dir={dir} className="min-w-0 flex-1 py-3 text-right text-sm font-semibold leading-6 text-slate-600">
        {value || 'ثبت نشده'}
      </div>
    </FieldShell>
  );
}

function ToggleSwitch({
  enabled,
  onChange,
  label,
}: {
  enabled: boolean;
  onChange?: (value: boolean) => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange?.(!enabled)}
      className="inline-flex items-center gap-3"
      aria-label={label}
    >
      <span
        className={[
          'inline-flex h-7 w-12 items-center rounded-full p-1 transition',
          enabled ? 'bg-emerald-600' : 'bg-slate-300',
        ].join(' ')}
      >
        <span
          className={[
            'h-5 w-5 rounded-full bg-white shadow-sm transition',
            enabled ? 'translate-x-0' : '-translate-x-5',
          ].join(' ')}
        />
      </span>
    </button>
  );
}

function Panel({
  title,
  icon: Icon,
  children,
  className = '',
}: {
  title: string;
  icon: LucideIcon;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-3xl border border-border bg-white p-6 shadow-soft ${className}`}>
      <div dir="rtl" className="mb-5 flex items-center justify-start gap-3 text-right">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
          <Icon className="h-6 w-6" />
        </span>
        <h2 className="min-w-0 text-right text-xl font-black text-text">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function ProfileHero({
  user,
  loading,
  onAvatarClick,
}: {
  user: CurrentUser | null;
  loading: boolean;
  onAvatarClick: () => void;
}) {
  const displayName = getDisplayName(user);
  const email = getEmail(user);
  const phone = user?.phone_number || user?.phone || '';

  return (
    <section dir="rtl" className="rounded-3xl border border-border bg-white p-6 shadow-soft sm:p-7">
      <div className="flex flex-col items-center gap-8 text-center sm:flex-row sm:items-center sm:gap-12 sm:text-right">
        <div className="relative h-28 w-28 shrink-0 sm:h-32 sm:w-32">
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt=""
              className="h-full w-full rounded-full object-cover shadow-inner ring-8 ring-emerald-50"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-emerald-100 via-teal-50 to-slate-100 text-4xl font-black text-emerald-800 shadow-inner ring-8 ring-emerald-50">
              {loading ? '...' : getInitials(displayName)}
            </div>
          )}
          <button
            type="button"
            onClick={onAvatarClick}
            className="absolute bottom-1 left-1 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-600 text-white shadow-[0_10px_24px_rgba(0,145,95,0.28)] transition hover:bg-emerald-700"
            aria-label="تغییر تصویر پروفایل"
          >
            <Camera className="h-5 w-5" />
          </button>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-center gap-3 sm:justify-start">
            <h1 className="text-2xl font-black text-text sm:text-3xl">{displayName}</h1>
            {user?.is_email_verified ? (
              <span className="inline-flex h-8 items-center gap-1 rounded-2xl bg-emerald-50 px-3 text-xs font-black text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
                ایمیل تایید شده
              </span>
            ) : null}
          </div>
          <div dir="ltr" className="mt-2 text-center text-sm font-bold text-emerald-700 sm:text-right">
            {getUsername(user) ? `@${getUsername(user)}` : 'نام کاربری ثبت نشده'}
          </div>

          <div className="mt-6 flex flex-wrap justify-center gap-x-7 gap-y-3 text-sm font-semibold text-slate-600 sm:justify-start">
            <span className="inline-flex items-center gap-2">
              <Calendar className="h-4.5 w-4.5 text-slate-500" />
              عضو از {formatDate(user?.created_at)}
            </span>
            <span dir="ltr" className="inline-flex items-center gap-2">
              {email || 'ایمیل ثبت نشده'}
              <Mail className="h-4.5 w-4.5 text-slate-500" />
            </span>
            <span className="inline-flex items-center gap-2">
              <Phone className="h-4.5 w-4.5 text-slate-500" />
              {phone || 'شماره ثبت نشده'}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

function ProfileTabs({ activeTab, onChange }: { activeTab: ProfileTab; onChange: (tab: ProfileTab) => void }) {
  return (
    <div className="border-b border-border">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {profileTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={[
              'relative h-14 text-sm font-black transition',
              activeTab === tab.id ? 'text-emerald-700' : 'text-slate-600 hover:text-slate-900',
            ].join(' ')}
          >
            {tab.label}
            {activeTab === tab.id ? (
              <span className="absolute inset-x-4 bottom-[-1px] h-0.5 rounded-full bg-emerald-600" />
            ) : null}
          </button>
        ))}
      </div>
    </div>
  );
}

function BankCardInput({
  card,
  onChange,
  onRemove,
}: {
  card: BankCardField;
  onChange: (id: number, value: string) => void;
  onRemove: (id: number) => void;
}) {
  const digits = normalizeCardDigits(card.number);
  const bankName = getBankName(card.number);
  const status =
    digits.length < 6
      ? 'شش رقم اول کارت را وارد کنید'
      : bankName || 'بانک ایرانی شناسایی نشد';
  const validLength = digits.length === 16;

  return (
    <div className="rounded-2xl border border-border bg-slate-50/50 p-4">
      <div dir="rtl" className="grid gap-3 lg:grid-cols-[auto_minmax(0,1fr)_auto] lg:items-center">
        <div className="text-right">
          <div className="mb-2 text-sm font-black text-slate-700">شماره کارت</div>
          <span
            className={[
              'inline-flex min-h-8 items-center rounded-2xl px-3 text-xs font-black',
              validLength ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-50 text-slate-500',
            ].join(' ')}
          >
            {status}
          </span>
        </div>
        <div className="flex h-12 items-center gap-3 rounded-2xl border border-border bg-white px-4 shadow-sm transition focus-within:border-emerald-500/50 focus-within:ring-4 focus-within:ring-emerald-500/10">
          <CreditCard className="h-5 w-5 shrink-0 text-slate-500" />
          <input
            dir="ltr"
            inputMode="numeric"
            value={card.number}
            onChange={(event) => onChange(card.id, event.target.value)}
            placeholder="0000 0000 0000 0000"
            className="h-full min-w-0 flex-1 border-0 bg-transparent text-left text-sm font-bold tracking-[0.08em] text-slate-700 outline-none placeholder:text-slate-300"
          />
        </div>
        <button
          type="button"
          onClick={() => onRemove(card.id)}
          className="flex h-11 w-11 items-center justify-center rounded-2xl border border-red-100 bg-white text-red-500 transition hover:bg-red-50"
          aria-label="حذف شماره کارت"
        >
          <Trash2 className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

function PersonalInfoPanel({
  user,
  onUserUpdated,
  onAvatarMessage,
}: {
  user: CurrentUser | null;
  onUserUpdated: (user: CurrentUser) => void;
  onAvatarMessage: (message: string, tone: MessageTone) => void;
}) {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [artName, setArtName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [city, setCity] = useState('');
  const [bio, setBio] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [messageTone, setMessageTone] = useState<MessageTone>('neutral');
  const [bankCards, setBankCards] = useStoredState<BankCardField[]>('hamdong.profile.bankCards', []);
  const [artNameStatus, setArtNameStatus] = useState<ArtNameStatus>('idle');
  const [artNameMessage, setArtNameMessage] = useState('');
  const [artNameTouched, setArtNameTouched] = useState(false);
  const currentArtName = normalizeArtName(user?.art_name || user?.username || '');

  useEffect(() => {
    setFirstName(user?.first_name || '');
    setLastName(user?.last_name || '');
    setArtName(user?.art_name || user?.username || '');
    setPhoneNumber(user?.phone_number || user?.phone || '');
    setDateOfBirth(user?.date_of_birth || '');
    setCity(user?.city || '');
    setBio(user?.bio || '');
    setAvatarUrl(user?.avatar_url || '');
    setMessage('');
    setArtNameTouched(false);
    setArtNameStatus('idle');
    setArtNameMessage('');
  }, [user]);

  useEffect(() => {
    const normalizedArtName = normalizeArtName(artName);

    if (!artNameTouched) {
      setArtNameStatus('idle');
      setArtNameMessage('');
      return;
    }

    if (!normalizedArtName) {
      setArtNameStatus('invalid');
      setArtNameMessage('نام کاربری را وارد کنید.');
      return;
    }

    if (normalizedArtName === currentArtName) {
      setArtNameStatus('idle');
      setArtNameMessage('');
      return;
    }

    const validationMessage = getArtNameValidationMessage(normalizedArtName);

    if (validationMessage) {
      setArtNameStatus('invalid');
      setArtNameMessage(validationMessage);
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        setArtNameStatus('checking');
        setArtNameMessage('در حال بررسی نام کاربری...');

        const result = await checkArtNameAvailability(normalizedArtName, {
          currentArtName,
          signal: controller.signal,
        });

        if (result.unsupported) {
          setArtNameStatus('idle');
          setArtNameMessage('');
          return;
        }

        if (result.available) {
          setArtNameStatus('available');
          setArtNameMessage('این نام کاربری آزاد است.');
          return;
        }

        setArtNameStatus('taken');
        setArtNameMessage(result.message || 'این نام کاربری قبلاً ثبت شده است.');
      } catch (error) {
        if (controller.signal.aborted) return;

        const code = getApiErrorCode(error);

        if (code === 'ART_NAME_ALREADY_EXISTS') {
          setArtNameStatus('taken');
          setArtNameMessage('این نام کاربری قبلاً ثبت شده است.');
          return;
        }

        if (code === 'INVALID_ART_NAME') {
          setArtNameStatus('invalid');
          setArtNameMessage('نام کاربری باید بین ۳ تا ۳۲ کاراکتر و بدون فاصله باشد.');
          return;
        }

        setArtNameStatus('error');
        setArtNameMessage('اتصال برای بررسی نام کاربری برقرار نشد. هنگام ذخیره دوباره بررسی می‌کنیم.');
      }
    }, 300);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [artName, artNameTouched, currentArtName]);

  async function handleSaveProfile() {
    const normalizedArtName = normalizeArtName(artName);
    const artNameValidationMessage = getArtNameValidationMessage(normalizedArtName);

    if (artNameValidationMessage) {
      setMessage(artNameValidationMessage);
      setMessageTone('error');
      setArtNameTouched(true);
      setArtNameStatus('invalid');
      setArtNameMessage(artNameValidationMessage);
      return;
    }

    if (artNameStatus === 'checking') {
      setMessage('چند لحظه صبر کنید تا تکراری بودن نام کاربری بررسی شود.');
      setMessageTone('error');
      return;
    }

    if (artNameStatus === 'taken') {
      setMessage(artNameMessage || 'این نام کاربری قبلاً ثبت شده است.');
      setMessageTone('error');
      return;
    }

    try {
      setSaving(true);
      setMessage('در حال ذخیره اطلاعات پروفایل...');
      setMessageTone('neutral');

      const updatedUser = await updateCurrentUserProfile({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        art_name: normalizedArtName,
        phone_number: phoneNumber.trim() || null,
        date_of_birth: dateOfBirth || null,
        city: city.trim() || null,
        bio: bio.trim() || null,
        avatar_url: avatarUrl.trim() || null,
      });

      onUserUpdated(updatedUser);
      setMessage('اطلاعات پروفایل ذخیره شد.');
      setMessageTone('success');
      onAvatarMessage('پروفایل به‌روزرسانی شد.', 'success');
    } catch (error) {
      const code = getApiErrorCode(error);

      const messageMap: Record<string, string> = {
        ART_NAME_ALREADY_EXISTS: 'این نام کاربری قبلا ثبت شده است.',
        PHONE_NUMBER_ALREADY_EXISTS: 'این شماره موبایل قبلا استفاده شده است.',
        INVALID_ART_NAME: 'فرمت نام کاربری معتبر نیست.',
        INVALID_PHONE_NUMBER: 'شماره موبایل معتبر نیست.',
        INVALID_DATE_OF_BIRTH: 'تاریخ تولد معتبر نیست.',
        INVALID_CITY: 'شهر معتبر نیست.',
        INVALID_BIO: 'متن درباره من معتبر نیست.',
      };

      setMessage(messageMap[code] || 'ذخیره تغییرات ناموفق بود.');
      setMessageTone('error');
    } finally {
      setSaving(false);
    }
  }

  function handleAddBankCard() {
    setBankCards((cards) => [
      ...cards,
      {
        id: Date.now() + cards.length,
        number: '',
      },
    ]);
  }

  function handleUpdateBankCard(id: number, value: string) {
    setBankCards((cards) =>
      cards.map((card) =>
        card.id === id
          ? {
              ...card,
              number: formatCardNumber(value),
            }
          : card,
      ),
    );
  }

  function handleRemoveBankCard(id: number) {
    setBankCards((cards) => cards.filter((card) => card.id !== id));
  }

  const email = getEmail(user);

  return (
    <section className="rounded-3xl border border-border bg-white p-6 shadow-soft sm:p-7">
      <div className="grid gap-5 md:grid-cols-2">
        <TextInput label="نام" value={firstName} icon={User} onChange={setFirstName} />
        <TextInput label="نام خانوادگی" value={lastName} icon={User} onChange={setLastName} />
        <ArtNameInput
          value={artName}
          onChange={(value) => {
            setArtName(value);
            setArtNameTouched(true);
            setMessage('');
          }}
          status={artNameStatus}
          message={artNameMessage}
          disabled={saving}
        />
        <TextInput label="شماره موبایل" value={phoneNumber} icon={Phone} onChange={setPhoneNumber} dir="ltr" />
        <TextInput label="تاریخ تولد" value={dateOfBirth} icon={Calendar} onChange={setDateOfBirth} type="date" dir="ltr" />
        <TextInput label="شهر / محل سکونت" value={city} icon={MapPin} onChange={setCity} />
        <TextInput
          label="لینک تصویر پروفایل"
          value={avatarUrl}
          icon={Camera}
          onChange={setAvatarUrl}
          dir="ltr"
          placeholder="https://..."
        />
        <ReadOnlyField label="ایمیل" value={email} icon={Mail} dir="ltr" />
        <ReadOnlyField label="نقش حساب" value={user?.role || 'USER'} icon={Shield} />
        <ReadOnlyField label="تاریخ عضویت" value={formatDate(user?.created_at)} icon={Calendar} />
        <ReadOnlyField label="آخرین به‌روزرسانی" value={formatDate(user?.updated_at)} icon={Clock3} />
        <TextArea label="درباره من" value={bio} icon={FileText} onChange={setBio} maxLength={500} />
      </div>

      <div className="mt-6 rounded-3xl border border-emerald-100 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="button"
            onClick={handleAddBankCard}
            className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-emerald-500 bg-emerald-50 px-5 text-sm font-black text-emerald-700 transition hover:bg-emerald-100"
          >
            <Plus className="h-5 w-5" />
            افزودن شماره کارت
          </button>

          <div className="text-right">
            <h3 className="text-lg font-black text-text">کارت‌های بانکی</h3>
            <p className="mt-1 text-xs font-semibold leading-6 text-muted">
              این کارت‌ها فقط روی همین دستگاه ذخیره می‌شوند.
            </p>
          </div>
        </div>

        {bankCards.length ? (
          <div className="mt-5 space-y-3">
            {bankCards.map((card) => (
              <BankCardInput
                key={card.id}
                card={card}
                onChange={handleUpdateBankCard}
                onRemove={handleRemoveBankCard}
              />
            ))}
          </div>
        ) : (
          <div className="mt-5 rounded-2xl border border-dashed border-border p-5 text-center text-sm text-muted">
            هنوز کارتی اضافه نشده است.
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={handleSaveProfile}
        disabled={saving}
        className="mt-5 inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-black text-white shadow-[0_12px_28px_rgba(0,168,107,0.2)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Save className="h-4.5 w-4.5" />
        {saving ? 'در حال ذخیره...' : 'ذخیره تغییرات'}
      </button>
      {message ? (
        <p
          className={[
            'mt-3 text-right text-sm font-bold leading-7',
            messageTone === 'success' ? 'text-emerald-600' : '',
            messageTone === 'error' ? 'text-rose-600' : '',
            messageTone === 'neutral' ? 'text-slate-500' : '',
          ].join(' ')}
        >
          {message}
        </p>
      ) : null}
    </section>
  );
}

function QuickAccessCard({
  onSecurityClick,
  onExportClick,
}: {
  onSecurityClick: () => void;
  onExportClick: () => void;
}) {
  return (
    <aside className="rounded-3xl border border-border bg-white p-6 shadow-soft">
      <h2 className="mb-7 text-right text-xl font-black text-text">دسترسی‌های سریع</h2>

      <div className="space-y-4">
        <button
          type="button"
          onClick={onSecurityClick}
          className="flex w-full items-center justify-between gap-4 text-right transition hover:text-emerald-700"
        >
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
            <Lock className="h-5 w-5" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-black text-text">تغییر رمز عبور</span>
            <span className="mt-1 block text-xs font-semibold leading-6 text-muted">رمز عبور و امنیت حساب</span>
          </span>
        </button>

        <button
          type="button"
          onClick={onExportClick}
          className="flex w-full items-center justify-between gap-4 text-right transition hover:text-emerald-700"
        >
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
            <Download className="h-5 w-5" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-black text-text">خروجی اطلاعات</span>
            <span className="mt-1 block text-xs font-semibold leading-6 text-muted">دانلود داده‌های قابل نمایش صفحه</span>
          </span>
        </button>
      </div>
    </aside>
  );
}

function PasswordPanel() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [messageTone, setMessageTone] = useState<MessageTone>('neutral');
  const strength = getPasswordStrength(newPassword);
  const PasswordIcon = showPassword ? EyeOff : Eye;

  async function handleSubmit() {
    if (!newPassword || !confirmPassword) {
      setMessage('رمز جدید و تکرار آن را وارد کنید.');
      setMessageTone('error');
      return;
    }

    if (newPassword !== confirmPassword) {
      setMessage('تکرار رمز عبور با رمز جدید یکسان نیست.');
      setMessageTone('error');
      return;
    }

    try {
      setSaving(true);
      setMessage(currentPassword ? 'در حال تغییر رمز عبور...' : 'در حال تنظیم رمز عبور...');
      setMessageTone('neutral');

      if (currentPassword) {
        await changePassword({
          current_password: currentPassword,
          new_password: newPassword,
          new_password_confirm: confirmPassword,
        });
      } else {
        await setPassword({
          new_password: newPassword,
          new_password_confirm: confirmPassword,
        });
      }

      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setMessage(currentPassword ? 'رمز عبور با موفقیت تغییر کرد.' : 'رمز عبور با موفقیت تنظیم شد.');
      setMessageTone('success');
    } catch (error) {
      const code = getApiErrorCode(error);
      const map: Record<string, string> = {
        PASSWORD_ALREADY_SET: 'برای تغییر رمز، رمز فعلی را هم وارد کنید.',
        PASSWORD_CONFIRMATION_MISMATCH: 'تکرار رمز عبور با رمز جدید یکسان نیست.',
        INVALID_CURRENT_PASSWORD: 'رمز عبور فعلی اشتباه است.',
        PASSWORD_REUSE_NOT_ALLOWED: 'رمز جدید باید با رمز فعلی متفاوت باشد.',
        WEAK_PASSWORD: 'رمز عبور جدید به اندازه کافی قوی نیست.',
      };

      setMessage(map[code] || 'عملیات رمز عبور ناموفق بود.');
      setMessageTone('error');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Panel title="رمز عبور" icon={Lock}>
      <div className="space-y-3">
        <TextInput
          label="رمز عبور فعلی"
          value={currentPassword}
          icon={Lock}
          onChange={setCurrentPassword}
          type={showPassword ? 'text' : 'password'}
          helper="اگر هنوز رمز عبور ندارید، این فیلد را خالی بگذارید."
        />
        <TextInput
          label="رمز عبور جدید"
          value={newPassword}
          icon={PasswordIcon}
          onChange={setNewPassword}
          type={showPassword ? 'text' : 'password'}
        />
        <TextInput
          label="تکرار رمز عبور جدید"
          value={confirmPassword}
          icon={PasswordIcon}
          onChange={setConfirmPassword}
          type={showPassword ? 'text' : 'password'}
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => setShowPassword((value) => !value)}
          className="inline-flex h-10 items-center gap-2 rounded-2xl border border-border bg-white px-4 text-xs font-black text-slate-700 transition hover:bg-slate-50"
        >
          <PasswordIcon className="h-4 w-4" />
          {showPassword ? 'مخفی کردن رمز' : 'نمایش رمز'}
        </button>
        <span className={`inline-flex h-10 items-center rounded-2xl px-4 text-xs font-black ${strength.className}`}>
          قدرت رمز: {strength.label}
        </span>
      </div>

      <button
        type="button"
        onClick={handleSubmit}
        disabled={saving}
        className="mt-5 inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-emerald-600 px-5 text-sm font-black text-white shadow-[0_10px_24px_rgba(0,145,95,0.2)] transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Save className="h-4.5 w-4.5" />
        {saving ? 'در حال ذخیره...' : currentPassword ? 'تغییر رمز' : 'تنظیم رمز'}
      </button>

      {message ? (
        <p
          className={[
            'mt-3 text-right text-sm font-bold leading-7',
            messageTone === 'success' ? 'text-emerald-600' : '',
            messageTone === 'error' ? 'text-rose-600' : '',
            messageTone === 'neutral' ? 'text-slate-500' : '',
          ].join(' ')}
        >
          {message}
        </p>
      ) : null}
    </Panel>
  );
}

function SecurityPanel({ user }: { user: CurrentUser | null }) {
  const browserName = navigator.userAgent.includes('Firefox')
    ? 'Firefox'
    : navigator.userAgent.includes('Edg')
      ? 'Edge'
      : navigator.userAgent.includes('Chrome')
        ? 'Chrome'
        : 'مرورگر فعلی';

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <Panel title="وضعیت امنیت حساب" icon={Shield}>
        <div dir="rtl" className="space-y-4 text-right">
          <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
            <span className="text-sm font-black text-slate-700">ایمیل</span>
            <span className={['text-sm font-black', user?.is_email_verified ? 'text-emerald-600' : 'text-amber-600'].join(' ')}>
              {user?.is_email_verified ? 'تایید شده' : 'در انتظار تایید'}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
            <span className="text-sm font-black text-slate-700">نقش</span>
            <span className="text-sm font-black text-slate-700">{user?.role || 'USER'}</span>
          </div>
          <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
            <span className="text-sm font-black text-slate-700">آخرین به‌روزرسانی پروفایل</span>
            <span className="text-sm font-black text-slate-700">{formatDate(user?.updated_at)}</span>
          </div>
        </div>
      </Panel>

      <PasswordPanel />

      <Panel title="دستگاه فعلی" icon={Laptop}>
        <div className="flex items-center justify-between gap-4 rounded-2xl border border-border bg-slate-50 px-4 py-4">
          <Monitor className="h-6 w-6 text-slate-700" />
          <div className="min-w-0 text-right">
            <div className="text-sm font-black text-text">{browserName}</div>
            <div className="mt-1 text-xs font-semibold leading-6 text-muted">
              جزئیات دستگاه فعلی از مرورگر شما خوانده می‌شود.
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
}

function SettingRow({
  label,
  enabled,
  onChange,
  icon: Icon,
}: {
  label: string;
  enabled: boolean;
  onChange: (value: boolean) => void;
  icon?: LucideIcon;
}) {
  return (
    <div className="flex min-h-12 items-center justify-between gap-4 border-b border-border py-2 last:border-b-0">
      <ToggleSwitch enabled={enabled} onChange={onChange} label={label} />
      <span className="flex items-center gap-3 text-right text-sm font-black text-slate-700">
        {label}
        {Icon ? <Icon className="h-5 w-5 text-slate-600" /> : null}
      </span>
    </div>
  );
}

function NotificationSettingsPanel() {
  const [settings, setSettings] = useStoredState<NotificationSettings>(
    'hamdong.profile.notifications',
    defaultNotificationSettings,
  );
  const [saved, setSaved] = useState(false);

  function update<K extends keyof NotificationSettings>(key: K, value: NotificationSettings[K]) {
    setSettings((current) => ({ ...current, [key]: value }));
    setSaved(false);
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-5 xl:grid-cols-3">
        <Panel title="اعلان‌های پرداخت و تسویه" icon={WalletCards}>
          <SettingRow label="تایید پرداخت من" enabled={settings.paymentConfirmed} onChange={(value) => update('paymentConfirmed', value)} />
          <SettingRow label="پرداخت اعضای گروه" enabled={settings.memberPayments} onChange={(value) => update('memberPayments', value)} />
          <SettingRow label="تکمیل تسویه" enabled={settings.settlementCompleted} onChange={(value) => update('settlementCompleted', value)} />
        </Panel>

        <Panel title="اعلان‌های گروه‌ها" icon={Users}>
          <SettingRow label="دعوت به گروه جدید" enabled={settings.groupInvites} onChange={(value) => update('groupInvites', value)} icon={UserPlus} />
          <SettingRow label="ثبت هزینه جدید" enabled={settings.newExpenses} onChange={(value) => update('newExpenses', value)} icon={Plus} />
          <SettingRow label="افزودن رسید یا فاکتور" enabled={settings.receiptUploads} onChange={(value) => update('receiptUploads', value)} icon={FileText} />
        </Panel>

        <Panel title="روش‌های دریافت اعلان" icon={Bell}>
          <SettingRow label="اعلان داخل سایت" enabled={settings.inApp} onChange={(value) => update('inApp', value)} />
          <SettingRow label="ایمیل" enabled={settings.email} onChange={(value) => update('email', value)} icon={Mail} />
          <SettingRow label="اعلان مرورگر" enabled={settings.browser} onChange={(value) => update('browser', value)} />
          <p className="mt-4 text-right text-xs font-semibold leading-6 text-muted">
            این تنظیمات روی همین دستگاه ذخیره می‌شوند.
          </p>
        </Panel>

        <Panel title="ساعات سکوت" icon={Clock3}>
          <SettingRow label="فعال‌سازی ساعات سکوت" enabled={settings.quietHours} onChange={(value) => update('quietHours', value)} />
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <TextInput label="شروع" value={settings.quietStart} icon={Clock3} onChange={(value) => update('quietStart', value)} type="time" dir="ltr" />
            <TextInput label="پایان" value={settings.quietEnd} icon={Clock3} onChange={(value) => update('quietEnd', value)} type="time" dir="ltr" />
          </div>
        </Panel>

        <Panel title="یادآوری بدهی‌ها" icon={Bell} className="xl:col-span-2">
          <SettingRow label="دریافت یادآوری بدهی‌ها" enabled={settings.debtReminder} onChange={(value) => update('debtReminder', value)} />
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <TextInput label="اولین یادآوری بعد از چند ساعت" value={settings.firstReminder} icon={Clock3} onChange={(value) => update('firstReminder', value)} dir="ltr" />
            <TextInput label="تکرار هر چند ساعت" value={settings.repeatReminder} icon={Clock3} onChange={(value) => update('repeatReminder', value)} dir="ltr" />
          </div>
        </Panel>
      </div>

      <button
        type="button"
        onClick={() => setSaved(true)}
        className="inline-flex h-[52px] items-center justify-center gap-3 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-8 text-base font-black text-white shadow-[0_14px_30px_rgba(0,145,95,0.22)] transition hover:-translate-y-0.5"
      >
        <Check className="h-5 w-5" />
        {saved ? 'تنظیمات اعلان ذخیره شد' : 'ذخیره تنظیمات اعلان'}
      </button>
    </div>
  );
}

function VisibilityControl({
  label,
  description,
  icon,
  value,
  onChange,
}: {
  label: string;
  description: string;
  icon: LucideIcon;
  value: 'self' | 'members';
  onChange: (value: 'self' | 'members') => void;
}) {
  const Icon = icon;

  return (
    <div className="rounded-2xl border border-border bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm">
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0 text-right">
          <div className="text-sm font-black text-text">{label}</div>
          <p className="mt-1 text-xs font-semibold leading-6 text-muted">{description}</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 rounded-2xl bg-slate-50 p-1">
        <button
          type="button"
          onClick={() => onChange('members')}
          className={[
            'h-10 rounded-xl border px-4 text-xs font-black transition',
            value === 'members'
              ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
              : 'border-border bg-white text-slate-600',
          ].join(' ')}
        >
          اعضای مشترک
        </button>
        <button
          type="button"
          onClick={() => onChange('self')}
          className={[
            'h-10 rounded-xl border px-4 text-xs font-black transition',
            value === 'self'
              ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
              : 'border-border bg-white text-slate-600',
          ].join(' ')}
        >
          فقط خودم
        </button>
      </div>
    </div>
  );
}

function PrivacyPanel({
  user,
  notificationSettings,
  bankCards,
}: {
  user: CurrentUser | null;
  notificationSettings: NotificationSettings;
  bankCards: BankCardField[];
}) {
  const [settings, setSettings] = useStoredState<PrivacySettings>(
    'hamdong.profile.privacy',
    defaultPrivacySettings,
  );
  const [message, setMessage] = useState('');

  function update<K extends keyof PrivacySettings>(key: K, value: PrivacySettings[K]) {
    setSettings((current) => ({ ...current, [key]: value }));
    setMessage('');
  }

  function exportProfileData() {
    const payload = {
      exported_at: new Date().toISOString(),
      profile: user,
      local_notification_settings: notificationSettings,
      local_privacy_settings: settings,
      local_bank_cards: bankCards.map((card) => ({
        ...card,
        bank_name: getBankName(card.number),
      })),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'hamdong-profile-data.json';
    link.click();
    URL.revokeObjectURL(url);
    setMessage('خروجی اطلاعات پروفایل آماده شد.');
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-5 xl:grid-cols-3">
        <Panel title="نمایش اطلاعات پروفایل" icon={Lock}>
          <div className="space-y-3">
            <VisibilityControl
              label="شماره موبایل"
              description="سطح نمایش شماره موبایل در محیط گروه‌ها."
              icon={Phone}
              value={settings.phoneVisibility}
              onChange={(value) => update('phoneVisibility', value)}
            />
            <VisibilityControl
              label="ایمیل"
              description="سطح نمایش ایمیل حساب شما."
              icon={Mail}
              value={settings.emailVisibility}
              onChange={(value) => update('emailVisibility', value)}
            />
            <VisibilityControl
              label="تصویر پروفایل"
              description="سطح نمایش تصویر پروفایل."
              icon={Camera}
              value={settings.avatarVisibility}
              onChange={(value) => update('avatarVisibility', value)}
            />
          </div>
        </Panel>

        <Panel title="دعوت و پیدا شدن" icon={UserPlus}>
          <SettingRow label="دیگران با شماره موبایل من را پیدا کنند" enabled={settings.searchableByPhone} onChange={(value) => update('searchableByPhone', value)} />
          <SettingRow label="اجازه دعوت مستقیم به گروه‌ها" enabled={settings.directInvites} onChange={(value) => update('directInvites', value)} />
          <SettingRow label="قبل از عضویت در گروه جدید تایید من لازم است" enabled={settings.confirmBeforeJoin} onChange={(value) => update('confirmBeforeJoin', value)} />
        </Panel>

        <Panel title="دسترسی به رسیدها و فاکتورها" icon={FileText}>
          <SettingRow label="اعضای گروه بتوانند تصویر رسید را ببینند" enabled={settings.receiptsVisibleToMembers} onChange={(value) => update('receiptsVisibleToMembers', value)} />
          <SettingRow label="فقط افراد مرتبط با هزینه" enabled={settings.receiptsVisibleToParticipantsOnly} onChange={(value) => update('receiptsVisibleToParticipantsOnly', value)} />
        </Panel>

        <Panel title="مدیریت داده‌ها" icon={Database} className="min-h-[236px] xl:col-span-3">
          <p className="mb-5 text-right text-sm font-semibold leading-7 text-muted">
            خروجی گرفتن از داده‌های قابل نمایش همین صفحه در مرورگر انجام می‌شود. حذف حساب در این نسخه فعال نیست.
          </p>
          <div className="grid gap-4 lg:grid-cols-3">
            <button
              type="button"
              onClick={exportProfileData}
              className="flex min-h-[76px] w-full items-center justify-between gap-4 rounded-2xl border border-border bg-white px-5 py-4 text-sm font-black text-slate-700 transition hover:bg-slate-50"
            >
              <Download className="h-5 w-5" />
              دانلود اطلاعات حساب
            </button>
            <button
              type="button"
              onClick={() => setMessage('سیاست حریم خصوصی در این نسخه به صورت جداگانه ارائه نشده است.')}
              className="flex min-h-[76px] w-full items-center justify-between gap-4 rounded-2xl border border-border bg-white px-5 py-4 text-sm font-black text-slate-700 transition hover:bg-slate-50"
            >
              <Shield className="h-5 w-5" />
              مشاهده سیاست حریم خصوصی
            </button>
            <button
              type="button"
              onClick={() => setMessage('حذف حساب در این نسخه فعال نیست.')}
              className="flex min-h-[76px] w-full items-center justify-between gap-4 rounded-2xl border border-rose-100 bg-rose-50 px-5 py-4 text-sm font-black text-rose-700 transition hover:bg-rose-100"
            >
              <Trash2 className="h-5 w-5" />
              حذف حساب کاربری
            </button>
          </div>
        </Panel>
      </div>

      <button
        type="button"
        onClick={() => setMessage('تنظیمات حریم خصوصی در مرورگر ذخیره شد.')}
        className="inline-flex h-[52px] items-center justify-center gap-3 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-8 text-base font-black text-white shadow-[0_14px_30px_rgba(0,145,95,0.22)] transition hover:-translate-y-0.5"
      >
        <Lock className="h-5 w-5" />
        ذخیره تنظیمات حریم خصوصی
      </button>

      {message ? <p className="text-right text-sm font-bold text-emerald-600">{message}</p> : null}
    </div>
  );
}

export function ProfilePage() {
  const [activeTab, setActiveTab] = useState<ProfileTab>('personal');
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pageMessage, setPageMessage] = useState('');
  const [pageMessageTone, setPageMessageTone] = useState<MessageTone>('neutral');
  const [notificationSettings] = useStoredState<NotificationSettings>(
    'hamdong.profile.notifications',
    defaultNotificationSettings,
  );
  const [bankCards] = useStoredState<BankCardField[]>('hamdong.profile.bankCards', []);

  async function loadProfile() {
    try {
      setLoading(true);
      setLoadError(null);
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    } catch (error) {
      console.warn('Could not load current user for profile page.', error);
      setLoadError('اطلاعات پروفایل دریافت نشد.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProfile();
  }, []);

  function handleExport() {
    const payload = {
      exported_at: new Date().toISOString(),
      profile: user,
      local_notification_settings: notificationSettings,
      local_bank_cards: bankCards,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'hamdong-profile-data.json';
    link.click();
    URL.revokeObjectURL(url);
    setPageMessage('خروجی اطلاعات حساب آماده شد.');
    setPageMessageTone('success');
  }

  const activePanel = useMemo(() => {
    if (activeTab === 'personal') {
      return (
        <PersonalInfoPanel
          user={user}
          onUserUpdated={setUser}
          onAvatarMessage={(message, tone) => {
            setPageMessage(message);
            setPageMessageTone(tone);
          }}
        />
      );
    }
    if (activeTab === 'security') return <SecurityPanel user={user} />;
    if (activeTab === 'notifications') return <NotificationSettingsPanel />;
    return <PrivacyPanel user={user} notificationSettings={notificationSettings} bankCards={bankCards} />;
  }, [activeTab, bankCards, notificationSettings, user]);

  return (
    <main className="px-6 py-6 sm:px-8 sm:py-8 lg:px-10 xl:px-14 2xl:px-16">
      <div className="mx-auto max-w-[1240px] space-y-7">
        <ProfileHero
          user={user}
          loading={loading}
          onAvatarClick={() => {
            setActiveTab('personal');
            setPageMessage('برای تغییر تصویر پروفایل، لینک تصویر را در بخش اطلاعات شخصی وارد و ذخیره کنید.');
            setPageMessageTone('neutral');
          }}
        />

        {loadError ? (
          <div className="rounded-3xl border border-rose-100 bg-rose-50 p-5 text-center text-sm font-bold text-rose-600">
            {loadError}
          </div>
        ) : null}

        {pageMessage ? (
          <div
            className={[
              'rounded-3xl border p-5 text-center text-sm font-bold',
              pageMessageTone === 'success' ? 'border-emerald-100 bg-emerald-50 text-emerald-700' : '',
              pageMessageTone === 'error' ? 'border-rose-100 bg-rose-50 text-rose-600' : '',
              pageMessageTone === 'neutral' ? 'border-slate-100 bg-slate-50 text-slate-600' : '',
            ].join(' ')}
          >
            {pageMessage}
          </div>
        ) : null}

        <ProfileTabs activeTab={activeTab} onChange={setActiveTab} />

        {activeTab === 'personal' ? (
          <div dir="ltr" className="grid gap-6 xl:grid-cols-[306px_minmax(0,1fr)]">
            <QuickAccessCard
              onSecurityClick={() => setActiveTab('security')}
              onExportClick={handleExport}
            />
            <div dir="rtl">{activePanel}</div>
          </div>
        ) : (
          <div>{activePanel}</div>
        )}
      </div>
    </main>
  );
}
