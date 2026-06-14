import { useEffect, useMemo, useState } from 'react';
import {
  Bell,
  Check,
  Calendar,
  Camera,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  Clock3,
  Database,
  Download,
  Eye,
  FileText,
  Laptop,
  CreditCard,
  Edit3,
  Lock,
  Mail,
  MapPin,
  Monitor,
  Phone,
  Plus,
  Moon,
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
import { getCurrentUser, updateCurrentUserProfile, type CurrentUser } from '../lib/userApi';

type ProfileTab = 'personal' | 'security' | 'notifications' | 'privacy';

interface ProfileFieldProps {
  label: string;
  value: string;
  icon: LucideIcon;
  multiline?: boolean;
  counter?: string;
}

interface ProfileInputProps {
  label: string;
  value: string;
  icon: LucideIcon;
  onChange: (value: string) => void;
  dir?: 'rtl' | 'ltr';
  helperText?: string;
  tone?: 'neutral' | 'success' | 'error';
}

interface QuickAccessItem {
  id: number;
  title: string;
  description: string;
  icon: LucideIcon;
}

const profileTabs: Array<{ id: ProfileTab; label: string }> = [
  { id: 'personal', label: 'اطلاعات شخصی' },
  { id: 'security', label: 'امنیت' },
  { id: 'notifications', label: 'تنظیمات اعلان‌ها' },
  { id: 'privacy', label: 'حریم خصوصی' },
];

const quickAccessItems: QuickAccessItem[] = [
  {
    id: 1,
    title: 'تغییر رمز عبور',
    description: 'رمز عبور حساب خود را تغییر دهید',
    icon: Lock,
  },
];

function getFullName(user: CurrentUser | null) {
  if (!user) return 'علی احمدی';

  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();

  return (
    user.display_name ||
    fullName ||
    'کاربر همدنگ'
  );
}

function getUsername(user: CurrentUser | null) {
  return user?.art_name || 'ali_ahmadi';
}

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.slice(0, 1))
    .join('');
}

function ProfileAvatar({ name }: { name: string }) {
  return (
    <div className="relative h-28 w-28 shrink-0 sm:h-32 sm:w-32">
      <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-emerald-100 via-teal-50 to-slate-100 text-4xl font-black text-emerald-800 shadow-inner ring-8 ring-emerald-50">
        {getInitials(name)}
      </div>
      <button
        type="button"
        className="absolute bottom-1 left-1 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-600 text-white shadow-[0_10px_24px_rgba(0,145,95,0.28)] transition hover:bg-emerald-700"
        aria-label="تغییر تصویر پروفایل"
      >
        <Camera className="h-5 w-5" />
      </button>
    </div>
  );
}

function ProfileHero({ user }: { user: CurrentUser | null }) {
  const displayName = getFullName(user);
  const username = getUsername(user);
  const email = user?.username?.includes('@') ? user.username : 'ali.ahmadi@example.com';
  const phone = user?.phone_number || user?.phone || '۰۹۱۲ ۳۴۵ ۶۷۸۱';

  return (
    <section dir="rtl" className="rounded-3xl border border-border bg-white p-6 shadow-soft sm:p-7">
      <div className="flex flex-col items-center gap-8 text-center sm:flex-row sm:items-center sm:gap-12 sm:text-right">
        <ProfileAvatar name={displayName} />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-center gap-3 sm:justify-start">
            <h1 className="text-2xl font-black text-text sm:text-3xl">{displayName}</h1>
          </div>
          <div dir="ltr" className="mt-2 text-center text-sm font-bold text-emerald-700 sm:text-right">
            @{username}
          </div>

          <div className="mt-6 flex flex-wrap justify-center gap-x-7 gap-y-3 text-sm font-semibold text-slate-600 sm:justify-start">
            <span className="inline-flex items-center gap-2">
              <Calendar className="h-4.5 w-4.5 text-slate-500" />
              عضو از اردیبهشت ۱۴۰۳
            </span>
            <span className="hidden h-5 w-px bg-border sm:inline-block" />
            <span dir="ltr" className="inline-flex items-center gap-2">
              {email}
              <Mail className="h-4.5 w-4.5 text-slate-500" />
            </span>
            <span className="hidden h-5 w-px bg-border sm:inline-block" />
            <span className="inline-flex items-center gap-2">
              <Phone className="h-4.5 w-4.5 text-slate-500" />
              {phone}
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

function ProfileField({ label, value, icon: Icon, multiline = false, counter }: ProfileFieldProps) {
  return (
    <label className={multiline ? 'md:col-span-2' : ''}>
      <span className="mb-2 block text-right text-sm font-black text-slate-700">{label}</span>
      <div
        className={[
          'flex w-full items-center gap-3 rounded-2xl border border-border bg-white px-4 text-slate-700 shadow-sm',
          multiline ? 'min-h-[86px] items-start py-3' : 'h-12',
        ].join(' ')}
      >
        <Icon className="h-4.5 w-4.5 shrink-0 text-slate-500" />
        <div className="min-w-0 flex-1 text-right text-sm font-semibold leading-7">
          {value}
        </div>
        {counter ? <span className="self-end pb-1 text-xs font-semibold text-slate-500">{counter}</span> : null}
      </div>
    </label>
  );
}

function ProfileInput({
  label,
  value,
  icon: Icon,
  onChange,
  dir = 'rtl',
  helperText,
  tone = 'neutral',
}: ProfileInputProps) {
  const helperClass =
    tone === 'success'
      ? 'text-emerald-600'
      : tone === 'error'
        ? 'text-rose-600'
        : 'text-slate-500';

  return (
    <label>
      <span className="mb-2 block text-right text-sm font-black text-slate-700">{label}</span>
      <div className="flex h-12 w-full items-center gap-3 rounded-2xl border border-border bg-white px-4 text-slate-700 shadow-sm transition focus-within:border-emerald-500/50 focus-within:ring-4 focus-within:ring-emerald-500/10">
        <Icon className="h-4.5 w-4.5 shrink-0 text-slate-500" />
        <input
          dir={dir}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="h-full min-w-0 flex-1 border-0 bg-transparent text-sm font-semibold text-slate-700 outline-none"
        />
      </div>
      {helperText ? (
        <p className={`mt-2 text-right text-xs font-bold leading-6 ${helperClass}`}>{helperText}</p>
      ) : null}
    </label>
  );
}

function QuickAccessCard() {
  return (
    <aside className="rounded-3xl border border-border bg-white p-6 shadow-soft">
      <h2 className="mb-7 text-right text-xl font-black text-text">دسترسی‌های سریع</h2>

      <div className="space-y-6">
        {quickAccessItems.map((item) => {
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              type="button"
              className="flex w-full items-center justify-between gap-4 text-right transition hover:text-emerald-700"
            >
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
                <Icon className="h-5 w-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-black text-text">{item.title}</span>
                <span className="mt-1 block text-xs font-semibold leading-6 text-muted">{item.description}</span>
              </span>
            </button>
          );
        })}
      </div>

      <div className="my-7 h-px bg-border" />

      <div className="text-right">
        <h3 className="text-base font-black text-text">آخرین ورود</h3>
        <div className="mt-6 flex items-center justify-between gap-4">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
            <Clock3 className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <div className="text-sm font-black text-slate-700">امروز، ۱۰:۳۳</div>
            <div className="mt-1 text-xs font-semibold leading-6 text-muted">تهران، ایران • مرورگر Chrome</div>
          </div>
        </div>
      </div>
    </aside>
  );
}

function ToggleSwitch({ enabled }: { enabled: boolean }) {
  return (
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
  );
}

function SecurityCard({
  title,
  icon: Icon,
  children,
  className = '',
}: {
  title: string;
  icon: LucideIcon;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-3xl border border-border bg-white p-6 shadow-soft ${className}`}>
      <div dir="rtl" className="mb-5 flex items-center justify-start gap-3 text-right">
        <Icon className="h-6 w-6 shrink-0 text-slate-700" />
        <h2 className="min-w-0 text-right text-xl font-black text-text">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function PasswordStrengthBadge({
  label,
  tone,
  active = false,
}: {
  label: string;
  tone: 'low' | 'medium' | 'high';
  active?: boolean;
}) {
  const toneClass =
    tone === 'low'
      ? 'border-red-200 bg-red-50 text-red-600'
      : tone === 'medium'
        ? 'border-orange-200 bg-orange-50 text-orange-600'
        : 'border-emerald-200 bg-emerald-50 text-emerald-700';

  return (
    <span
      className={[
        'flex h-10 items-center justify-center rounded-2xl border px-4 text-sm font-black',
        toneClass,
        active ? 'ring-4 ring-emerald-500/10' : '',
      ].join(' ')}
    >
      {label}
    </span>
  );
}

function SecurityStatusPanel() {
  return (
    <SecurityCard title="وضعیت امنیت حساب" icon={Shield}>
      <div dir="rtl" className="space-y-5 text-right">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <span className="inline-flex h-10 items-center gap-2 rounded-2xl bg-emerald-50 px-4 text-sm font-black text-emerald-700">
            <CheckCircle2 className="h-4.5 w-4.5" />
            وضعیت خوب
          </span>
          <span className="flex items-center gap-2 text-right text-sm font-bold text-slate-700">
            حساب شما از نظر امنیتی پایدار است
            <CheckCircle2 className="h-4.5 w-4.5 text-emerald-600" />
          </span>
        </div>

        <div className="rounded-2xl border border-emerald-100 bg-slate-50/60 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm font-black text-slate-800">سطح امنیت رمز عبور</span>
            <span className="inline-flex h-9 items-center rounded-2xl bg-emerald-600 px-4 text-xs font-black text-white">
              عالی
            </span>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            <PasswordStrengthBadge label="کم" tone="low" />
            <PasswordStrengthBadge label="متوسط" tone="medium" />
            <PasswordStrengthBadge label="عالی" tone="high" active />
          </div>
        </div>

        <div className="flex items-center justify-start gap-2 text-sm font-bold text-slate-700">
          ایمیل تایید شده
          <CheckCircle2 className="h-4.5 w-4.5 text-emerald-600" />
        </div>
        <div className="flex items-center justify-start gap-2 text-sm font-bold text-slate-700">
          آخرین ورود: امروز، ۱۰:۳۳ از تهران
          <Clock3 className="h-4.5 w-4.5 text-slate-500" />
        </div>
      </div>
    </SecurityCard>
  );
}

function PasswordPanel() {
  return (
    <SecurityCard title="تغییر رمز عبور" icon={Lock}>
      <div className="space-y-3">
        {['رمز عبور فعلی', 'رمز عبور جدید', 'تکرار رمز عبور جدید'].map((placeholder) => (
          <div
            key={placeholder}
            className="flex h-12 items-center gap-3 rounded-2xl border border-border bg-white px-4 shadow-sm"
          >
            <Eye className="h-4.5 w-4.5 text-slate-500" />
            <input
              type="password"
              placeholder={placeholder}
              className="h-full min-w-0 flex-1 border-0 bg-transparent text-right text-sm font-semibold outline-none placeholder:text-slate-400"
            />
          </div>
        ))}
      </div>
      <button
        type="button"
        className="mt-4 inline-flex h-11 items-center justify-center rounded-2xl bg-emerald-600 px-5 text-sm font-black text-white shadow-[0_10px_24px_rgba(0,145,95,0.2)] transition hover:bg-emerald-700"
      >
        ذخیره رمز جدید
      </button>
    </SecurityCard>
  );
}

function ActiveDevicesPanel() {
  const devices = [
    {
      id: 1,
      title: 'تهران - Windows / Chrome',
      subtitle: 'آخرین فعالیت: امروز، ۱۰:۳۳',
      icon: Monitor,
    },
    {
      id: 2,
      title: 'شیراز - iPhone / Safari',
      subtitle: 'آخرین فعالیت: دیروز، ۲۰:۴۵',
      icon: Smartphone,
    },
    {
      id: 3,
      title: 'اصفهان - Android / Chrome',
      subtitle: 'آخرین فعالیت: ۲ روز پیش، ۱۸:۱۲',
      icon: Smartphone,
    },
  ];

  return (
    <SecurityCard title="دستگاه‌های فعال" icon={Laptop}>
      <p className="mb-4 text-right text-sm font-semibold leading-7 text-muted">
        دستگاه‌هایی که اکنون با حساب شما وارد شده‌اند.
      </p>
      <div className="space-y-3">
        {devices.map((device) => {
          const Icon = device.icon;

          return (
            <div key={device.id} className="grid grid-cols-[110px_minmax(0,1fr)_32px] items-center gap-4">
              <button
                type="button"
                className="h-10 rounded-xl border border-border bg-white px-3 text-xs font-black text-slate-700 transition hover:bg-slate-50"
              >
                خروج از دستگاه
              </button>
              <div className="min-w-0 text-right">
                <div className="truncate text-sm font-black text-slate-800">{device.title}</div>
                <div className="mt-1 truncate text-xs font-semibold text-muted">{device.subtitle}</div>
              </div>
              <Icon className="h-5 w-5 text-slate-700" />
            </div>
          );
        })}
      </div>
      <button
        type="button"
        className="mt-4 inline-flex items-center gap-2 text-sm font-black text-emerald-600 transition hover:text-emerald-700"
      >
        مشاهده همه دستگاه‌ها
        <Check className="h-4 w-4" />
      </button>
    </SecurityCard>
  );
}

function SensitiveOperationsPanel() {
  const operations = [
    { id: 1, label: 'برداشت از کیف پول', icon: WalletCards },
    { id: 2, label: 'تغییر رمز عبور', icon: Lock },
    { id: 3, label: 'تغییر نام کاربری', icon: Edit3 },
    { id: 4, label: 'تغییر شماره موبایل', icon: Smartphone },
    { id: 5, label: 'حذف حساب', icon: User },
  ];

  return (
    <SecurityCard title="تایید عملیات حساس" icon={Lock}>
      <p className="mb-5 text-right text-sm font-semibold leading-7 text-muted">
        برای انجام عملیات‌های حساس، تایید اضافی درخواست شود.
      </p>
      <div className="overflow-hidden rounded-2xl border border-border">
        {operations.map((operation, index) => {
          const Icon = operation.icon;

          return (
            <div
              key={operation.id}
              className={[
                'flex h-14 items-center justify-between gap-4 px-4',
                index === operations.length - 1 ? '' : 'border-b border-border',
              ].join(' ')}
            >
              <ToggleSwitch enabled />
              <span className="flex items-center gap-3 text-sm font-black text-slate-700">
                {operation.label}
                <Icon className="h-5 w-5 text-slate-700" />
              </span>
            </div>
          );
        })}
      </div>
    </SecurityCard>
  );
}

function SecurityPanel() {
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <SecurityStatusPanel />
      <PasswordPanel />
      <ActiveDevicesPanel />
      <SensitiveOperationsPanel />
    </div>
  );
}

function NotificationCard({
  title,
  icon: Icon,
  children,
  className = '',
}: {
  title: string;
  icon: LucideIcon;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-3xl border border-border bg-white p-6 shadow-soft ${className}`}>
      <div dir="rtl" className="mb-5 flex items-center justify-start gap-3 text-right">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
          <Icon className="h-6 w-6" />
        </span>
        <h2 className="min-w-0 text-right text-xl font-black text-text">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function NotificationRow({
  label,
  enabled = true,
  icon: Icon,
}: {
  label: string;
  enabled?: boolean;
  icon?: LucideIcon;
}) {
  return (
    <div className="flex h-12 items-center justify-between gap-4 border-b border-border last:border-b-0">
      <ToggleSwitch enabled={enabled} />
      <span className="flex items-center gap-3 text-right text-sm font-black text-slate-700">
        {label}
        {Icon ? <Icon className="h-5 w-5 text-slate-600" /> : null}
      </span>
    </div>
  );
}

function SelectPill({ label }: { label: string }) {
  return (
    <button
      type="button"
      className="flex h-12 w-full min-w-[140px] items-center justify-between gap-3 rounded-2xl border border-border bg-white px-4 text-sm font-black text-slate-700 shadow-sm transition hover:bg-slate-50"
    >
      <ChevronDown className="h-4 w-4 text-slate-500" />
      {label}
    </button>
  );
}

function PaymentNotificationPanel() {
  return (
    <NotificationCard title="اعلان‌های پرداخت و تسویه" icon={WalletCards}>
      <NotificationRow label="تایید پرداخت من" />
      <NotificationRow label="پرداخت اعضای گروه" />
      <NotificationRow label="نیاز به تایید کارت‌به‌کارت" />
      <NotificationRow label="تکمیل تسویه" />
    </NotificationCard>
  );
}

function GroupNotificationPanel() {
  return (
    <NotificationCard title="اعلان‌های گروه‌ها" icon={Users}>
      <NotificationRow label="دعوت به گروه جدید" />
      <NotificationRow label="ثبت هزینه جدید" />
      <NotificationRow label="افزودن رسید یا فاکتور" />
      <NotificationRow label="تغییر سهم من" />
      <NotificationRow label="تسویه کامل گروه" />
    </NotificationCard>
  );
}

function NotificationMethodsPanel() {
  return (
    <NotificationCard title="روش‌های دریافت اعلان" icon={Bell}>
      <NotificationRow label="اعلان داخل سایت" />
      <NotificationRow label="ایمیل" />
      <NotificationRow label="اعلان مرورگر" enabled={false} />
      <p className="mt-4 text-right text-xs font-semibold leading-6 text-muted">
        روش‌های فعال برای دریافت اعلان‌ها را انتخاب کنید.
      </p>
    </NotificationCard>
  );
}

function QuietHoursPanel() {
  return (
    <NotificationCard title="ساعات سکوت" icon={Moon}>
      <div className="flex items-start justify-between gap-4">
        <ToggleSwitch enabled />
        <p className="max-w-[430px] text-right text-sm font-semibold leading-7 text-muted">
          در بازه زمانی مشخص، فقط اعلان‌های امنیتی ارسال شوند.
        </p>
      </div>
      <div className="mt-6 flex justify-center">
        <div className="inline-flex h-12 items-center gap-3 rounded-2xl border border-border bg-white px-5 text-sm font-black text-slate-700 shadow-sm">
          <Clock3 className="h-5 w-5 text-slate-500" />
          ۲۲:۰۰ تا ۰۸:۰۰
        </div>
      </div>
    </NotificationCard>
  );
}

function DebtReminderPanel() {
  return (
    <NotificationCard title="یادآوری بدهی‌ها" icon={Bell} className="xl:col-span-2">
      <div dir="rtl" className="flex flex-col gap-4 rounded-2xl bg-emerald-50/50 p-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-[520px] text-right text-sm font-semibold leading-7 text-muted">
          دریافت یادآوری برای بدهی‌ها و پرداخت‌های معوق
        </p>
        <ToggleSwitch enabled />
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div dir="rtl" className="flex flex-col gap-3 rounded-2xl border border-border bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
          <span className="shrink-0 text-right text-sm font-black text-slate-700">اولین یادآوری:</span>
          <div className="w-full sm:max-w-[190px]">
            <SelectPill label="۲۴ ساعت بعد" />
          </div>
        </div>
        <div dir="rtl" className="flex flex-col gap-3 rounded-2xl border border-border bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
          <span className="shrink-0 text-right text-sm font-black text-slate-700">تکرار:</span>
          <div className="w-full sm:max-w-[190px]">
            <SelectPill label="هر ۲ روز" />
          </div>
        </div>
      </div>
    </NotificationCard>
  );
}

function NotificationSettingsPanel() {
  return (
    <div className="space-y-5">
      <div className="grid gap-5 xl:grid-cols-3">
        <PaymentNotificationPanel />
        <GroupNotificationPanel />
        <NotificationMethodsPanel />
        <QuietHoursPanel />
        <DebtReminderPanel />
      </div>

      <button
        type="button"
        className="inline-flex h-[52px] items-center justify-center gap-3 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-8 text-base font-black text-white shadow-[0_14px_30px_rgba(0,145,95,0.22)] transition hover:-translate-y-0.5"
      >
        <Check className="h-5 w-5" />
        ذخیره تنظیمات اعلان
      </button>
    </div>
  );
}

function PrivacySegment({
  label,
  active = false,
}: {
  label: string;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      className={[
        'h-10 rounded-xl border px-4 text-xs font-black transition sm:min-w-[112px]',
        active
          ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
          : 'border-border bg-white text-slate-600 hover:bg-slate-50',
      ].join(' ')}
    >
      {label}
    </button>
  );
}

function PrivacyVisibilityChoice({
  label,
  description,
  icon: Icon,
}: {
  label: string;
  description: string;
  icon: LucideIcon;
}) {
  return (
    <div className="rounded-2xl border border-emerald-100 bg-gradient-to-l from-emerald-50/70 to-white p-4">
      <div className="flex items-start justify-between gap-3">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm">
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0 text-right">
          <div className="text-sm font-black text-slate-800">{label}</div>
          <p className="mt-1 text-xs font-semibold leading-6 text-muted">{description}</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 rounded-2xl bg-slate-50 p-1">
        <PrivacySegment label="اعضای مشترک" />
        <PrivacySegment label="فقط خودم" active />
      </div>
    </div>
  );
}

function PrivacyActionRow({
  label,
  icon: Icon,
  danger = false,
}: {
  label: string;
  icon: LucideIcon;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      className={[
        'flex min-h-[76px] w-full items-center justify-between gap-4 rounded-2xl border px-5 py-4 text-sm font-black transition',
        danger
          ? 'border-red-100 bg-red-50/45 text-red-600 hover:bg-red-50'
          : 'border-border bg-white text-slate-700 hover:bg-slate-50',
      ].join(' ')}
    >
      <ChevronLeft className="h-5 w-5" />
      <span className="flex items-center gap-3">
        {label}
        <Icon className="h-5 w-5" />
      </span>
    </button>
  );
}

function ProfileVisibilityPanel() {
  return (
    <NotificationCard title="نمایش اطلاعات پروفایل" icon={Lock}>
      <div className="space-y-3">
        <PrivacyVisibilityChoice label="شماره موبایل" description="نمایش شماره فقط برای خودتان فعال است." icon={Phone} />
        <PrivacyVisibilityChoice label="ایمیل" description="ایمیل از دید اعضای گروه پنهان می‌ماند." icon={Mail} />
        <PrivacyVisibilityChoice label="تصویر پروفایل" description="نمایش تصویر فقط با انتخاب شما انجام می‌شود." icon={Camera} />
      </div>
    </NotificationCard>
  );
}

function ReceiptAccessPanel() {
  return (
    <NotificationCard title="دسترسی به رسیدها و فاکتورها" icon={FileText}>
      <NotificationRow label="اعضای گروه بتوانند تصویر رسید را ببینند" />
      <NotificationRow label="فقط افراد مرتبط با هزینه" />
    </NotificationCard>
  );
}

function DiscoveryPrivacyPanel() {
  return (
    <NotificationCard title="دعوت و پیدا شدن" icon={UserPlus}>
      <NotificationRow label="دیگران با شماره موبایل من را پیدا کنند" enabled={false} />
      <NotificationRow label="اجازه دعوت مستقیم به گروه‌ها" />
      <NotificationRow label="قبل از عضویت در گروه جدید تایید من لازم است" />
    </NotificationCard>
  );
}

function DataManagementPanel() {
  return (
    <NotificationCard title="مدیریت داده‌ها" icon={Database} className="min-h-[236px] xl:col-span-3">
      <p className="mb-5 text-right text-sm font-semibold leading-7 text-muted">
        خروجی گرفتن از اطلاعات، مشاهده قوانین حریم خصوصی و درخواست حذف حساب از این بخش انجام می‌شود.
      </p>
      <div className="grid gap-4 lg:grid-cols-3">
        <PrivacyActionRow label="دانلود اطلاعات حساب" icon={Download} />
        <PrivacyActionRow label="مشاهده سیاست حریم خصوصی" icon={Shield} />
        <PrivacyActionRow label="حذف حساب کاربری" icon={Trash2} danger />
      </div>
    </NotificationCard>
  );
}

function PrivacyPanel() {
  return (
    <div className="space-y-5">
      <div className="grid gap-5 xl:grid-cols-3">
        <DiscoveryPrivacyPanel />
        <ReceiptAccessPanel />
        <ProfileVisibilityPanel />
        <DataManagementPanel />
      </div>

      <button
        type="button"
        className="inline-flex h-[52px] items-center justify-center gap-3 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-8 text-base font-black text-white shadow-[0_14px_30px_rgba(0,145,95,0.22)] transition hover:-translate-y-0.5"
      >
        <Lock className="h-5 w-5" />
        ذخیره تنظیمات حریم خصوصی
      </button>
    </div>
  );
}

function getApiErrorCode(error: unknown) {
  if (!isApiError(error)) return '';
  const body = error.body as { error?: { code?: unknown } } | undefined;
  return typeof body?.error?.code === 'string' ? body.error.code : '';
}

type BankCardField = {
  id: number;
  number: string;
};

const iranianBankPrefixes: Record<string, string> = {
  '603799': 'بانک ملی ایران',
  '589210': 'بانک سپه',
  '627648': 'بانک توسعه صادرات',
  '627961': 'بانک صنعت و معدن',
  '603770': 'بانک کشاورزی',
  '628023': 'بانک مسکن',
  '627760': 'پست بانک ایران',
  '502908': 'بانک توسعه تعاون',
  '627412': 'بانک اقتصاد نوین',
  '622106': 'بانک پارسیان',
  '627884': 'بانک پارسیان',
  '639194': 'بانک پارسیان',
  '502229': 'بانک پاسارگاد',
  '639347': 'بانک پاسارگاد',
  '627488': 'بانک کارآفرین',
  '502910': 'بانک کارآفرین',
  '621986': 'بانک سامان',
  '639346': 'بانک سینا',
  '639607': 'بانک سرمایه',
  '502806': 'بانک شهر',
  '504706': 'بانک شهر',
  '502938': 'بانک دی',
  '603769': 'بانک صادرات ایران',
  '610433': 'بانک ملت',
  '991975': 'بانک ملت',
  '589463': 'بانک رفاه کارگران',
  '627353': 'بانک تجارت',
  '585983': 'بانک تجارت',
  '627381': 'بانک انصار',
  '639370': 'بانک مهر اقتصاد',
  '639599': 'بانک قوامین',
  '636949': 'بانک حکمت ایرانیان',
  '505801': 'موسسه اعتباری کوثر',
  '636214': 'بانک آینده',
  '505416': 'بانک گردشگری',
  '505785': 'بانک ایران زمین',
  '585947': 'بانک خاورمیانه',
  '606373': 'بانک قرض‌الحسنه مهر ایران',
  '504172': 'بانک قرض‌الحسنه رسالت',
};

function normalizeCardDigits(value: string) {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
    .replace(/\D/g, '')
    .slice(0, 16);
}

function formatCardNumber(value: string) {
  return normalizeCardDigits(value).replace(/(.{4})/g, '$1 ').trim();
}

function getIranianBankName(value: string) {
  const digits = normalizeCardDigits(value);
  if (digits.length < 6) return '';
  return iranianBankPrefixes[digits.slice(0, 6)] || '';
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
  const bankName = getIranianBankName(card.number);
  const statusText =
    digits.length < 6
      ? 'شش رقم اول کارت را وارد کنید'
      : bankName || 'بانک ایرانی شناسایی نشد';
  const statusClass =
    digits.length < 6
      ? 'bg-slate-50 text-slate-500'
      : bankName
        ? 'bg-emerald-50 text-emerald-700'
        : 'bg-red-50 text-red-600';

  return (
    <div className="rounded-2xl border border-border bg-slate-50/50 p-4">
      <div dir="rtl" className="grid gap-3 lg:grid-cols-[auto_minmax(0,1fr)_auto] lg:items-center">
        <div className="text-right">
          <div className="mb-2 text-sm font-black text-slate-700">شماره کارت</div>
          <span className={`inline-flex min-h-8 items-center rounded-2xl px-3 text-xs font-black ${statusClass}`}>
            {statusText}
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
}: {
  user: CurrentUser | null;
  onUserUpdated: (user: CurrentUser) => void;
}) {
  const displayName = getFullName(user);
  const email = user?.username?.includes('@') ? user.username : 'ali.ahmadi@example.com';
  const phone = user?.phone_number || user?.phone || '۰۹۱۲ ۳۴۵ ۶۷۸۱';
  const currentUsername = getUsername(user);
  const [fullName, setFullName] = useState(displayName);
  const [username, setUsername] = useState(currentUsername);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [messageTone, setMessageTone] = useState<'neutral' | 'success' | 'error'>('neutral');
  const [bankCards, setBankCards] = useState<BankCardField[]>([]);

  useEffect(() => {
    setFullName(displayName);
    setUsername(currentUsername);
    setMessage('');
    setMessageTone('neutral');
  }, [currentUsername, displayName]);

  async function handleSaveProfile() {
    const cleanFullName = fullName.trim();
    const cleanUsername = username.trim();

    if (!cleanFullName) {
      setMessage('نام و نام خانوادگی نمی‌تواند خالی باشد.');
      setMessageTone('error');
      return;
    }

    if (!cleanUsername) {
      setMessage('نام کاربری نمی‌تواند خالی باشد.');
      setMessageTone('error');
      return;
    }

    try {
      setSaving(true);
      setMessage(
        cleanUsername !== currentUsername
          ? 'در حال بررسی یکتا بودن نام کاربری...'
          : 'در حال ذخیره تغییرات...',
      );
      setMessageTone('neutral');

      const updatedUser = await updateCurrentUserProfile({
        display_name: cleanFullName,
        art_name: cleanUsername,
      });

      onUserUpdated(updatedUser);
      setMessage(
        cleanUsername !== currentUsername
          ? 'نام کاربری آزاد بود و با موفقیت جایگزین نام کاربری قبلی شد.'
          : 'تغییرات پروفایل ذخیره شد.',
      );
      setMessageTone('success');
    } catch (error) {
      const errorCode = getApiErrorCode(error);

      if (errorCode === 'ART_NAME_ALREADY_EXISTS') {
        setMessage('این نام کاربری قبلا ثبت شده است. لطفا یک نام کاربری دیگر انتخاب کنید.');
      } else if (errorCode === 'INVALID_ART_NAME') {
        setMessage('فرمت نام کاربری معتبر نیست. از حروف انگلیسی، عدد و خط زیر استفاده کنید.');
      } else {
        setMessage('ذخیره تغییرات ناموفق بود. دوباره تلاش کنید.');
      }

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

  return (
    <section className="rounded-3xl border border-border bg-white p-6 shadow-soft sm:p-7">
      <div className="grid gap-5 md:grid-cols-2">
        <ProfileInput label="نام و نام خانوادگی" value={fullName} icon={Edit3} onChange={setFullName} />
        <ProfileInput
          label="نام کاربری"
          value={username}
          icon={CheckCircle2}
          onChange={(value) => {
            setUsername(value);
            setMessage('');
            setMessageTone('neutral');
          }}
          dir="ltr"
        />
        <ProfileField label="شماره موبایل" value={phone} icon={Phone} />
        <ProfileField label="ایمیل" value={email} icon={Mail} />
        <ProfileField label="تاریخ تولد" value="۱۳۷۶/۰۵/۱۲" icon={Calendar} />
        <ProfileField label="شهر / محل سکونت" value="تهران، ایران" icon={MapPin} />
        <ProfileField
          label="درباره من (اختیاری)"
          value="عاشق سفر و دنیای فناوری هستم."
          icon={Edit3}
          multiline
          counter="۲۵/۲۰۰"
        />
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
              تشخیص بانک فقط برای کارت‌های بانک‌های ایرانی انجام می‌شود.
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
        ) : null}
      </div>

      <button
        type="button"
        onClick={handleSaveProfile}
        disabled={saving}
        className="mt-5 inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-black text-white shadow-[0_12px_28px_rgba(0,168,107,0.2)] transition hover:-translate-y-0.5"
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

function PlaceholderPanel({ title }: { title: string }) {
  return (
    <section className="rounded-3xl border border-dashed border-emerald-200 bg-emerald-50/35 p-10 text-center shadow-soft">
      <h2 className="text-xl font-black text-text">{title}</h2>
      <p className="mt-2 text-sm leading-7 text-muted">
        تنظیمات این بخش در مرحله بعدی به سرویس پروفایل متصل می‌شود.
      </p>
    </section>
  );
}

export function ProfilePage() {
  const [activeTab, setActiveTab] = useState<ProfileTab>('personal');
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    let mounted = true;

    getCurrentUser()
      .then((currentUser) => {
        if (mounted) setUser(currentUser);
      })
      .catch((error) => {
        console.warn('Could not load current user for profile page.', error);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const activePanel = useMemo(() => {
    if (activeTab === 'personal') return <PersonalInfoPanel user={user} onUserUpdated={setUser} />;
    if (activeTab === 'security') return <SecurityPanel />;
    if (activeTab === 'notifications') return <NotificationSettingsPanel />;
    return <PrivacyPanel />;
  }, [activeTab, user]);

  return (
    <main className="px-6 py-6 sm:px-8 sm:py-8 lg:px-10 xl:px-14 2xl:px-16">
      <div className="mx-auto max-w-[1240px] space-y-7">
        <ProfileHero user={user} />
        <ProfileTabs activeTab={activeTab} onChange={setActiveTab} />

        {activeTab === 'personal' ? (
          <div dir="ltr" className="grid gap-6 xl:grid-cols-[306px_minmax(0,1fr)]">
            <QuickAccessCard />
            <div dir="rtl">{activePanel}</div>
          </div>
        ) : (
          <div>{activePanel}</div>
        )}
      </div>
    </main>
  );
}
