import { useMemo, useState } from 'react';
import {
  ArrowLeft,
  Check,
  ChevronLeft,
  Copy,
  Info,
  Link2,
  MessageCircle,
  MoreHorizontal,
  Search,
  Send,
  ShieldCheck,
  Smartphone,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import {
  CreateGroupStepper,
} from '../components/create-group/CreateGroupStepper';
import {
  GroupInfoStep,
  type GroupInfoValues,
  type GroupTypeValue,
} from '../components/create-group/GroupInfoStep';

export interface CreatedGroupPayload {
  name: string;
  description: string;
  groupType: GroupTypeValue;
  amount: string;
  memberCount: number;
}

interface CreateGroupWizardProps {
  onBack: () => void;
  onComplete: (payload: CreatedGroupPayload) => void;
}

interface Contact {
  id: number;
  name: string;
  phone: string;
  isFriend: boolean;
  isFrequent: boolean;
  avatar: string;
  avatarClass: string;
  isYou?: boolean;
}

type ContactFilter = 'all' | 'friends' | 'frequent';
type WizardStep = 1 | 2 | 3;

const contacts: Contact[] = [
  {
    id: 1,
    name: 'علی احمدی',
    phone: '0912 345 6781',
    isFriend: true,
    isFrequent: true,
    avatar: 'ع',
    avatarClass: 'from-amber-300 via-orange-400 to-orange-600',
    isYou: true,
  },
  {
    id: 2,
    name: 'سارا محمدی',
    phone: '0913 222 3344',
    isFriend: true,
    isFrequent: true,
    avatar: 'س',
    avatarClass: 'from-pink-300 to-rose-500',
  },
  {
    id: 3,
    name: 'رضا کریمی',
    phone: '0914 555 6677',
    isFriend: true,
    isFrequent: true,
    avatar: 'ر',
    avatarClass: 'from-amber-200 to-orange-500',
  },
  {
    id: 4,
    name: 'مینا حسینی',
    phone: '0915 888 9900',
    isFriend: true,
    isFrequent: false,
    avatar: 'م',
    avatarClass: 'from-cyan-300 to-sky-500',
  },
  {
    id: 5,
    name: 'حامد نوروزی',
    phone: '0916 111 2233',
    isFriend: true,
    isFrequent: false,
    avatar: 'ح',
    avatarClass: 'from-slate-400 to-slate-600',
  },
  {
    id: 6,
    name: 'ندا رحیمی',
    phone: '0917 222 4455',
    isFriend: true,
    isFrequent: false,
    avatar: 'ن',
    avatarClass: 'from-emerald-300 to-teal-500',
  },
  {
    id: 7,
    name: 'امیر رضایی',
    phone: '0918 876 4432',
    isFriend: true,
    isFrequent: false,
    avatar: 'ا',
    avatarClass: 'from-violet-300 to-fuchsia-500',
  },
  {
    id: 8,
    name: 'الهام صادقی',
    phone: '0919 223 9900',
    isFriend: true,
    isFrequent: false,
    avatar: 'ا',
    avatarClass: 'from-indigo-300 to-blue-500',
  },
  {
    id: 9,
    name: 'کیوان مرادی',
    phone: '0920 555 7788',
    isFriend: false,
    isFrequent: true,
    avatar: 'ک',
    avatarClass: 'from-lime-300 to-green-500',
  },
  {
    id: 10,
    name: 'بهاره کاظمی',
    phone: '0921 900 1122',
    isFriend: false,
    isFrequent: false,
    avatar: 'ب',
    avatarClass: 'from-yellow-300 to-amber-500',
  },
  {
    id: 11,
    name: 'آرمان نیکزاد',
    phone: '0922 765 1100',
    isFriend: false,
    isFrequent: false,
    avatar: 'آ',
    avatarClass: 'from-sky-300 to-indigo-500',
  },
  {
    id: 12,
    name: 'نگار موسوی',
    phone: '0923 445 6600',
    isFriend: false,
    isFrequent: false,
    avatar: 'ن',
    avatarClass: 'from-rose-300 to-pink-500',
  },
];

const steps = [
  { id: 1, label: 'اطلاعات گروه' },
  { id: 2, label: 'افزودن اعضا' },
  { id: 3, label: 'دعوت' },
];

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function Avatar({
  label,
  className,
}: {
  label: string;
  className: string;
}) {
  return (
    <div
      className={cn(
        'flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br text-sm font-bold text-white shadow-sm',
        className,
      )}
    >
      {label}
    </div>
  );
}

function SummaryCard({
  values,
  memberCount,
  currentStep,
}: {
  values: GroupInfoValues;
  memberCount: number;
  currentStep: WizardStep;
}) {
  const groupTypeLabel = (() => {
    switch (values.groupType) {
      case 'travel':
        return 'سفر';
      case 'food':
        return 'غذا و رستوران';
      case 'home':
        return 'خانه و زندگی';
      case 'other':
        return 'سایر';
      default:
        return '-';
    }
  })();

  const infoText =
    currentStep === 1
      ? 'بعد از ایجاد گروه می‌توانید اعضای خود را اضافه کرده و شروع به ثبت هزینه‌ها کنید.'
      : currentStep === 2
        ? 'پس از دعوت اعضا، می‌توانید هزینه‌ها را ثبت کرده و تسویه حساب را شروع کنید.'
        : 'پس از ایجاد گروه، می‌توانید هزینه‌ها را ثبت کرده و تسویه حساب را شروع کنید.';

  return (
    <aside className="panel-surface order-2 p-6 xl:order-2">
      <div className="mb-8 flex items-center justify-between">
        <h3 className="text-[28px] font-bold tracking-[-0.03em] text-text">
          خلاصه گروه
        </h3>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
          <Users className="h-5 w-5" strokeWidth={1.9} />
        </div>
      </div>

      <div className="space-y-8">
        <div className="space-y-2 text-right">
          <div className="text-sm text-muted">نام گروه</div>
          <div className="text-lg font-semibold text-text">
            {values.name || '-'}
          </div>
        </div>

        <div className="space-y-2 text-right">
          <div className="text-sm text-muted">نوع گروه</div>
          <div className="text-lg font-semibold text-text">{groupTypeLabel}</div>
        </div>

        <div className="space-y-2 text-right">
          <div className="text-sm text-muted">تاریخ شروع</div>
          <div className="text-lg font-semibold text-text">
            {values.startDate || 'تعیین نشده'}
          </div>
        </div>

        <div className="space-y-2 text-right">
          <div className="text-sm text-muted">تعداد اعضا</div>
          <div className="text-lg font-semibold text-text">
            {memberCount} نفر
          </div>
        </div>
      </div>

      <div className="mt-10 rounded-[20px] border border-emerald-100 bg-emerald-50/50 p-4">
        <div className="mb-3 flex items-center gap-2 text-emerald-600">
          <Info className="h-4.5 w-4.5" />
          <span className="text-sm font-semibold">اطلاع‌رسانی</span>
        </div>
        <p className="text-sm leading-7 text-slate-600">{infoText}</p>
      </div>
    </aside>
  );
}

function AddMembersStep({
  contactsList,
  searchValue,
  filter,
  selectedIds,
  onSearchChange,
  onFilterChange,
  onToggleMember,
  onRemoveMember,
}: {
  contactsList: Contact[];
  searchValue: string;
  filter: ContactFilter;
  selectedIds: number[];
  onSearchChange: (value: string) => void;
  onFilterChange: (value: ContactFilter) => void;
  onToggleMember: (id: number) => void;
  onRemoveMember: (id: number) => void;
}) {
  const selectedMembers = contactsList.filter((member) =>
    selectedIds.includes(member.id),
  );

  const filteredContacts = contactsList.filter((contact) => {
    const matchesSearch =
      !searchValue ||
      contact.name.includes(searchValue) ||
      contact.phone.includes(searchValue);

    const matchesFilter =
      filter === 'all'
        ? true
        : filter === 'friends'
          ? contact.isFriend
          : contact.isFrequent;

    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-8">
      <div className="flex flex-col items-start justify-between gap-3 border-b border-border/80 pb-6 lg:flex-row lg:items-center">
        <div className="text-right">
          <h2 className="text-[28px] font-bold tracking-[-0.03em] text-text">
            افزودن اعضا
          </h2>
          <p className="mt-2 text-sm text-muted">
            دوستان خود را برای اضافه شدن به گروه انتخاب کنید.
          </p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <div className="rounded-[24px] border border-border bg-white p-5">
          <div className="mb-5 flex items-center justify-between">
            <h3 className="text-[22px] font-bold text-text">اعضای انتخاب شده</h3>
            <span className="inline-flex h-8 min-w-[32px] items-center justify-center rounded-full bg-emerald-50 px-2 text-sm font-bold text-emerald-600">
              {selectedMembers.length}
            </span>
          </div>

          <div className="space-y-3">
            {selectedMembers.length === 0 ? (
              <div className="rounded-[18px] border border-dashed border-border px-4 py-8 text-center text-sm text-muted">
                هنوز عضوی انتخاب نشده است.
              </div>
            ) : (
              selectedMembers.map((member) => (
                <div
                  key={member.id}
                  className="flex items-center justify-between rounded-[18px] border border-border bg-white px-4 py-3"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <Avatar label={member.avatar} className={member.avatarClass} />
                    <div className="min-w-0 text-right">
                      <div className="truncate text-base font-semibold text-text">
                        {member.name}
                        {member.isYou ? ' (شما)' : ''}
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => onRemoveMember(member.id)}
                    className="flex h-9 w-9 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-rose-500"
                  >
                    <X className="h-4.5 w-4.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-[24px] border border-border bg-white p-5">
          <div className="mb-5">
            <div className="relative">
              <Search className="pointer-events-none absolute right-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" />
              <input
                dir="rtl"
                value={searchValue}
                onChange={(event) => onSearchChange(event.target.value)}
                placeholder="جستجو با نام یا شماره موبایل..."
                className="h-12 w-full rounded-[16px] border border-border bg-white pr-11 pl-4 text-sm text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
              />
            </div>
          </div>

          <div className="mb-5 grid grid-cols-3 gap-2 rounded-[18px] bg-slate-50 p-1">
            {[
              { key: 'all' as const, label: 'همه', count: 12 },
              { key: 'friends' as const, label: 'دوستان', count: 8 },
              { key: 'frequent' as const, label: 'همیشگی', count: 4 },
            ].map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => onFilterChange(item.key)}
                className={cn(
                  'rounded-[14px] px-3 py-2.5 text-sm font-semibold transition',
                  filter === item.key
                    ? 'bg-emerald-50 text-emerald-700 shadow-sm'
                    : 'text-slate-600 hover:text-text',
                )}
              >
                {item.label} ({item.count})
              </button>
            ))}
          </div>

          <div className="overflow-hidden rounded-[20px] border border-border">
            {filteredContacts.map((contact, index) => {
              const selected = selectedIds.includes(contact.id);

              return (
                <button
                  key={contact.id}
                  type="button"
                  onClick={() => onToggleMember(contact.id)}
                  className={cn(
                    'flex w-full items-center justify-between gap-4 px-4 py-3 text-right transition hover:bg-slate-50',
                    index !== filteredContacts.length - 1 && 'border-b border-border/70',
                  )}
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div
                      className={cn(
                        'flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition',
                        selected
                          ? 'border-emerald-500 bg-emerald-500 text-white'
                          : 'border-slate-300 bg-white text-transparent',
                      )}
                    >
                      <Check className="h-3.5 w-3.5" strokeWidth={3} />
                    </div>

                    <Avatar label={contact.avatar} className={contact.avatarClass} />

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-base font-semibold text-text">
                          {contact.name}
                        </span>
                        {contact.isYou ? (
                          <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                            شما
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>

                  <div className="shrink-0 text-sm text-muted">{contact.phone}</div>
                </button>
              );
            })}
          </div>

          <div className="mt-4 flex items-center gap-2 text-sm font-semibold text-slate-600">
            <UserPlus className="h-4.5 w-4.5 text-slate-400" />
            {selectedMembers.length} نفر انتخاب شده‌اند
          </div>
        </div>
      </div>
    </div>
  );
}

function InviteStep({
  values,
  selectedMembers,
}: {
  values: GroupInfoValues;
  selectedMembers: Contact[];
}) {
  const [copied, setCopied] = useState(false);
  const [invitePhone, setInvitePhone] = useState('');

  const inviteLink = 'https://hamdong.app/invite/7k3a9b';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(inviteLink);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col items-start justify-between gap-3 border-b border-border/80 pb-6 lg:flex-row lg:items-center">
        <div className="text-right">
          <h2 className="text-[28px] font-bold tracking-[-0.03em] text-text">
            دعوت اعضا به گروه
          </h2>
          <p className="mt-2 text-sm text-muted">
            لینک دعوت گروه خود را با دوستانتان به اشتراک بگذارید.
          </p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <div className="rounded-[24px] border border-border bg-white p-5">
          <h3 className="mb-4 text-lg font-bold text-text">پیش‌نمایش دعوت</h3>

          <div className="rounded-[22px] bg-slate-50 px-5 py-6 text-center">
            <div className="mx-auto mb-4 flex h-28 w-28 items-center justify-center overflow-hidden rounded-full border border-border bg-gradient-to-b from-sky-100 to-amber-50 text-[44px]">
              🚐
            </div>

            <div className="text-[22px] font-bold text-text">
              {values.name || 'سفر شمال تابستان ۱۴۰۳'}
            </div>
            <div className="mt-2 text-sm text-muted">دعوت به گروه در همدنگ</div>

            <div className="mt-5 flex items-center justify-center">
              <div className="flex -space-x-3 rtl:space-x-reverse">
                {selectedMembers.slice(0, 4).map((member) => (
                  <Avatar
                    key={member.id}
                    label={member.avatar}
                    className={cn('h-10 w-10 border-2 border-white', member.avatarClass)}
                  />
                ))}
                <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-white bg-white text-xs font-bold text-slate-500 shadow-sm">
                  +{Math.max(selectedMembers.length, 12) - Math.min(selectedMembers.length, 4)}
                </div>
              </div>
            </div>

            <div className="mt-3 text-sm font-semibold text-slate-600">
              {Math.max(selectedMembers.length, 12)} عضو
            </div>

            <p className="mt-5 text-sm leading-7 text-slate-600">
              بیایید هزینه‌ها را با هم مدیریت کنیم و سفر خاطره‌انگیزی داشته باشیم! 🚐🌿
            </p>
          </div>
        </div>

        <div className="rounded-[24px] border border-border bg-white p-5">
          <div>
            <label className="mb-2 block text-sm font-semibold text-text">
              لینک دعوت
            </label>

            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={handleCopy}
                className={cn(
                  'inline-flex h-12 shrink-0 items-center justify-center gap-2 rounded-[16px] border px-5 text-sm font-semibold transition sm:w-auto',
                  copied
                    ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                    : 'border-border bg-white text-slate-700 hover:border-emerald-300 hover:text-emerald-700',
                )}
              >
                <Copy className="h-4.5 w-4.5" />
                {copied ? 'کپی شد' : 'کپی لینک'}
              </button>

              <div className="relative flex-1">
                <Link2 className="pointer-events-none absolute right-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" />
                <input
                  readOnly
                  dir="ltr"
                  value={inviteLink}
                  className="h-12 w-full rounded-[16px] border border-border bg-white pr-11 pl-4 text-sm text-slate-600 outline-none"
                />
              </div>
            </div>
          </div>

          <div className="mt-5 rounded-[20px] border border-emerald-100 bg-emerald-50/50 p-4">
            <div className="flex items-start gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-emerald-600">
                <ShieldCheck className="h-5 w-5" />
              </div>

              <div className="min-w-0 text-right">
                <p className="text-sm leading-7 text-slate-600">
                  هر کسی که این لینک را داشته باشد می‌تواند به گروه بپیوندد.
                </p>
                <button
                  type="button"
                  className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-emerald-600"
                >
                  <Info className="h-4.5 w-4.5" />
                  تغییر تنظیمات لینک
                </button>
              </div>
            </div>
          </div>

          <div className="mt-6">
            <h3 className="mb-4 text-sm font-semibold text-text">اشتراک گذاری سریع</h3>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              {[
                { label: 'کپی لینک', icon: Copy },
                { label: 'واتساپ', icon: MessageCircle },
                { label: 'تلگرام', icon: Send },
                { label: 'پیامک', icon: Smartphone },
                { label: 'سایر', icon: MoreHorizontal },
              ].map((item) => {
                const Icon = item.icon;

                return (
                  <button
                    key={item.label}
                    type="button"
                    className="flex min-h-[84px] flex-col items-center justify-center gap-2 rounded-[18px] border border-border bg-white text-sm font-medium text-slate-700 transition hover:border-emerald-300 hover:text-emerald-700"
                  >
                    <Icon className="h-5 w-5" strokeWidth={1.9} />
                    {item.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-sm text-slate-400">یا</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-text">
              دعوت با شماره موبایل
            </label>

            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                className="inline-flex h-12 shrink-0 items-center justify-center gap-2 rounded-[16px] bg-emerald-50 px-5 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100"
              >
                افزودن
                <ChevronLeft className="h-4.5 w-4.5" />
              </button>

              <input
                dir="rtl"
                value={invitePhone}
                onChange={(event) => setInvitePhone(event.target.value)}
                placeholder="شماره موبایل را وارد کنید"
                className="h-12 flex-1 rounded-[16px] border border-border bg-white px-4 text-sm text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function CreateGroupWizard({
  onBack,
  onComplete,
}: CreateGroupWizardProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>(1);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [values, setValues] = useState<GroupInfoValues>({
    name: '',
    groupType: '',
    description: '',
    amount: '',
    currency: 'تومان (IRT)',
    startDate: '',
  });
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [filter, setFilter] = useState<ContactFilter>('all');
  const [searchValue, setSearchValue] = useState('');

  const selectedMembers = useMemo(
    () => contacts.filter((contact) => selectedIds.includes(contact.id)),
    [selectedIds],
  );

  const updateField = <K extends keyof GroupInfoValues>(
    field: K,
    value: GroupInfoValues[K],
  ) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const goToStep = (nextStep: WizardStep) => {
    if (nextStep === currentStep) {
      return;
    }

    setDirection(nextStep > currentStep ? 1 : -1);
    setCurrentStep(nextStep);
  };

  const handleToggleMember = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const handleFinish = () => {
    onComplete({
      name: values.name || 'گروه جدید',
      description: values.description,
      groupType: values.groupType,
      amount: values.amount,
      memberCount: selectedIds.length,
    });
  };

  return (
    <main className="px-4 py-6 sm:px-6 xl:px-8">
      <div className="mx-auto grid max-w-[1280px] gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
        <section className="card-surface order-1 overflow-hidden">
          <div className="border-b border-border/80 px-5 py-6 sm:px-8">
            <div className="flex items-center justify-between gap-4">
              <h1 className="text-[32px] font-extrabold tracking-[-0.03em] text-text">
                تشکیل گروه جدید
              </h1>
              <button
                type="button"
                onClick={onBack}
                className="inline-flex items-center gap-2 text-slate-600 transition hover:text-text"
              >
                <ArrowLeft className="h-5 w-5" />
                <span className="text-sm font-semibold">بازگشت</span>
              </button>
            </div>

            <div className="mt-8">
              <CreateGroupStepper currentStep={currentStep} steps={steps} />
            </div>
          </div>

          <div className="p-5 sm:p-8">
            <div
              key={currentStep}
              className={cn(
                'will-change-transform',
                direction === 1
                  ? 'wizard-step-enter-forward'
                  : 'wizard-step-enter-backward',
              )}
            >
              {currentStep === 1 ? (
                <GroupInfoStep values={values} onChange={updateField} />
              ) : currentStep === 2 ? (
                <AddMembersStep
                  contactsList={contacts}
                  searchValue={searchValue}
                  filter={filter}
                  selectedIds={selectedIds}
                  onSearchChange={setSearchValue}
                  onFilterChange={setFilter}
                  onToggleMember={handleToggleMember}
                  onRemoveMember={handleToggleMember}
                />
              ) : (
                <InviteStep values={values} selectedMembers={selectedMembers} />
              )}
            </div>
          </div>

          <div className="border-t border-border/80 px-5 py-5 sm:px-8">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex flex-col gap-3 sm:flex-row">
                {currentStep > 1 ? (
                  <button
                    type="button"
                    onClick={() => goToStep((currentStep - 1) as WizardStep)}
                    className="inline-flex h-12 items-center justify-center rounded-[16px] border border-border bg-white px-6 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                  >
                    مرحله قبل
                  </button>
                ) : null}

                {currentStep < 3 ? (
                  <button
                    type="button"
                    onClick={() => goToStep((currentStep + 1) as WizardStep)}
                    className="inline-flex h-12 items-center justify-center gap-2 rounded-[16px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5"
                  >
                    مرحله بعدی
                    <ChevronLeft className="h-4.5 w-4.5" />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleFinish}
                    className="inline-flex h-12 items-center justify-center gap-2 rounded-[16px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5"
                  >
                    اتمام و ایجاد گروه
                    <Check className="h-4.5 w-4.5" />
                  </button>
                )}
              </div>

              <button
                type="button"
                onClick={onBack}
                className="inline-flex h-12 items-center justify-center rounded-[16px] border border-border bg-white px-6 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 sm:mr-auto"
              >
                انصراف
              </button>
            </div>
          </div>
        </section>

        <SummaryCard
          values={values}
          memberCount={selectedIds.length}
          currentStep={currentStep}
        />
      </div>
    </main>
  );
}