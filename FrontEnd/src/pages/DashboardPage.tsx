import {
  AlertCircle,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Bell,
  CheckCircle2,
  CreditCard,
  Gift,
  Home,
  Mountain,
  Plus,
  ReceiptText,
  TrendingUp,
  UserPlus,
  Users,
  UtensilsCrossed,
  WalletCards,
  type LucideIcon,
} from 'lucide-react';
import type { ReactNode } from 'react';
import type { Group } from '../types';
import type { GroupBalanceSummary } from './GroupsPage';

interface DashboardPageProps {
  groups: Group[];
  groupBalances?: GroupBalanceSummary[];
  balancesLoading?: boolean;
  onCreateGroup: () => void;
  onOpenGroups: () => void;
  onOpenGroup: (groupId: string) => void;
  onOpenActivities: () => void;
  onOpenWallet: () => void;
}

interface SettlementSuggestion {
  id: number;
  name: string;
  description: string;
  amount: number;
  avatar: string;
}

interface DashboardEvent {
  id: number;
  title: string;
  time: string;
  timeText: string;
  icon: LucideIcon;
  toneClassName: string;
}

interface FallbackGroup {
  id: string;
  title: string;
  membersLabel: string;
  statusLabel: string;
  amount: number;
  tone: Group['tone'];
  illustration: Group['illustration'];
}

const settlementSuggestions: SettlementSuggestion[] = [
  {
    id: 1,
    name: 'علی رضایی',
    description: 'باید به شما پرداخت کند',
    amount: 2450000,
    avatar: '/landing/avatar-ali.png',
  },
  {
    id: 2,
    name: 'سارا احمدی',
    description: 'باید به شما پرداخت کند',
    amount: 1800000,
    avatar: '/landing/avatar-sara.png',
  },
  {
    id: 3,
    name: 'شام دوستانه',
    description: '۵ عضو',
    amount: 1230000,
    avatar: '/landing/high-five.png',
  },
];

const dashboardEvents: DashboardEvent[] = [
  {
    id: 1,
    title: 'سارا احمدی هنوز سهم «شام دوستانه» را پرداخت نکرده',
    time: '۱۰ دقیقه پیش',
    timeText: 'ده دقیقه پیش',
    icon: AlertCircle,
    toneClassName: 'bg-rose-50 text-rose-500',
  },
  {
    id: 2,
    title: 'علی رضایی هزینه رستوران ایتالیایی را ثبت کرد',
    time: '۳ ساعت پیش',
    timeText: 'سه ساعت پیش',
    icon: WalletCards,
    toneClassName: 'bg-emerald-50 text-emerald-600',
  },
  {
    id: 3,
    title: 'پرداخت شما از «شام سه‌شنبه» تایید شد',
    time: '۵ ساعت پیش',
    timeText: 'پنج ساعت پیش',
    icon: CheckCircle2,
    toneClassName: 'bg-emerald-50 text-emerald-600',
  },
  {
    id: 4,
    title: '۲ روز تا سررسید پرداخت «سفر شمال» باقی مانده است',
    time: '۱ روز پیش',
    timeText: 'یک روز پیش',
    icon: CreditCard,
    toneClassName: 'bg-amber-50 text-amber-500',
  },
];

const fallbackGroups: FallbackGroup[] = [
  {
    id: 'home',
    title: 'خانه',
    membersLabel: '۴ عضو',
    statusLabel: 'شما بدهکار هستید',
    amount: -3000000,
    tone: 'negative',
    illustration: 'home',
  },
  {
    id: 'trip',
    title: 'سفر شمال',
    membersLabel: '۶ عضو',
    statusLabel: 'شما طلبکار هستید',
    amount: 12450000,
    tone: 'positive',
    illustration: 'trip',
  },
  {
    id: 'dinner',
    title: 'شام دوستانه',
    membersLabel: '۵ عضو',
    statusLabel: 'شما طلبکار هستید',
    amount: 1230000,
    tone: 'positive',
    illustration: 'cafe',
  },
];

function formatMoney(amount: number) {
  return `${Math.abs(Math.round(amount)).toLocaleString('fa-IR')} تومان`;
}

function formatSignedMoney(amount: number) {
  const sign = amount > 0 ? '+' : amount < 0 ? '-' : '';
  return `${sign}${formatMoney(amount)}`;
}

const ones = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه'];
const teens = ['ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده'];
const tens = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود'];
const hundreds = ['', 'صد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد'];
const groups = ['', 'هزار', 'میلیون', 'میلیارد', 'تریلیون'];

function joinPersianParts(parts: string[]) {
  return parts.filter(Boolean).join(' و ');
}

function threeDigitToPersianWords(value: number) {
  const parts: string[] = [];
  const hundred = Math.floor(value / 100);
  const rest = value % 100;

  if (hundred) {
    parts.push(hundreds[hundred]);
  }

  if (rest >= 10 && rest < 20) {
    parts.push(teens[rest - 10]);
  } else {
    const ten = Math.floor(rest / 10);
    const one = rest % 10;

    if (ten) {
      parts.push(tens[ten]);
    }

    if (one) {
      parts.push(ones[one]);
    }
  }

  return joinPersianParts(parts);
}

function numberToPersianWords(value: number) {
  const roundedValue = Math.abs(Math.round(value));

  if (roundedValue === 0) return 'صفر';

  const parts: string[] = [];
  let remaining = roundedValue;
  let groupIndex = 0;

  while (remaining > 0) {
    const chunk = remaining % 1000;

    if (chunk) {
      const chunkText = threeDigitToPersianWords(chunk);
      const groupText = groups[groupIndex] || '';
      parts.unshift([chunkText, groupText].filter(Boolean).join(' '));
    }

    remaining = Math.floor(remaining / 1000);
    groupIndex += 1;
  }

  return joinPersianParts(parts);
}

function formatMoneyText(amount: number) {
  return `${numberToPersianWords(amount)} تومان`;
}

function formatSignedMoneyText(amount: number) {
  if (amount < 0) return `منفی ${formatMoneyText(amount)}`;
  if (amount > 0) return `مثبت ${formatMoneyText(amount)}`;
  return formatMoneyText(amount);
}

function toEnglishDigits(value: string) {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)));
}

function getMemberCountText(label: string) {
  const match = toEnglishDigits(label).match(/(\d+)\s*عضو/);

  if (!match) return '';

  return `${numberToPersianWords(Number(match[1]))} عضو`;
}

function SectionCard({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-3xl border border-border bg-white shadow-soft ${className}`}>
      {children}
    </section>
  );
}

function SectionHeader({
  title,
  actionLabel,
  icon,
  onAction,
}: {
  title: string;
  actionLabel: string;
  icon: ReactNode;
  onAction?: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 px-5 py-4 sm:px-6">
      <button
        type="button"
        onClick={onAction}
        className="inline-flex items-center gap-2 text-xs font-extrabold text-emerald-600 transition hover:text-emerald-700"
      >
        {actionLabel}
        <ArrowLeft className="h-4 w-4" />
      </button>

      <div className="flex items-center gap-2 text-right">
        <h2 className="text-lg font-black text-text sm:text-xl">{title}</h2>
        {icon}
      </div>
    </div>
  );
}

function QuickActionCard({
  icon: Icon,
  title,
  description,
  onClick,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex min-h-[98px] items-center justify-between gap-4 rounded-2xl border border-emerald-200/70 bg-gradient-to-br from-emerald-50/80 to-white px-5 text-right shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-[0_18px_40px_rgba(15,23,42,0.07)]"
    >
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm transition group-hover:bg-emerald-600 group-hover:text-white">
        <Icon className="h-6 w-6" />
      </div>
      <div className="min-w-0">
        <div className="flex items-center justify-end gap-2 text-lg font-black text-emerald-800">
          <Plus className="h-4.5 w-4.5" />
          <span>{title}</span>
        </div>
        <p className="mt-1 text-sm leading-6 text-muted">{description}</p>
      </div>
    </button>
  );
}

function BalanceHero({
  creditMinor,
  debtMinor,
  loading,
}: {
  creditMinor: number;
  debtMinor: number;
  loading?: boolean;
}) {
  const netMinor = creditMinor - debtMinor;
  const isPositive = netMinor >= 0;

  return (
    <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#007A4F] via-[#009A66] to-[#00785B] p-6 text-white shadow-[0_24px_60px_rgba(0,128,89,0.24)] sm:p-8">
      <div className="pointer-events-none absolute -left-16 -top-20 h-64 w-64 rounded-full bg-white/10 blur-2xl" />
      <div className="pointer-events-none absolute bottom-0 right-1/4 h-32 w-32 rounded-full bg-white/10 blur-2xl" />

      <div className="relative grid gap-7 lg:grid-cols-[220px_minmax(0,1fr)] lg:items-center">
        <div className="order-2 flex justify-center lg:order-1">
          <div className="flex h-32 w-32 items-center justify-center rounded-full bg-white/10 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.16)] sm:h-36 sm:w-36">
            <WalletCards className="h-16 w-16" strokeWidth={1.7} />
          </div>
        </div>

        <div className="order-1 min-w-0 text-right lg:order-2">
          <div className="mb-5">
            <h1 className="text-xl font-black sm:text-2xl">وضعیت شما</h1>
            <p className="mt-2 text-sm font-semibold text-white/80">شما در مجموع</p>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-3">
            <span className="text-[28px] font-black tracking-normal sm:text-[36px]">
              {loading ? 'در حال محاسبه' : formatMoney(Math.abs(netMinor))}
            </span>
            {!loading ? (
              <span className="text-xl font-black sm:text-2xl">
                {isPositive ? 'طلبکار هستید' : 'بدهکار هستید'}
              </span>
            ) : null}
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white/12 text-white">
              {isPositive ? <TrendingUp className="h-6 w-6" /> : <ArrowDown className="h-6 w-6" />}
            </span>
          </div>
          {!loading ? (
            <p className="mt-2 text-sm font-semibold leading-7 text-white/75">
              {formatMoneyText(Math.abs(netMinor))}
            </p>
          ) : null}

          <div className="my-6 h-px bg-white/18" />

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex items-center justify-between gap-4 rounded-2xl bg-white/5 px-4 py-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white/12 text-emerald-100">
                <ArrowDown className="h-5 w-5" />
              </span>
              <div className="text-right">
                <div className="text-sm text-white/78">طلب شما</div>
                <div className="mt-1 text-lg font-black">{formatMoney(creditMinor)}</div>
                <div className="mt-1 max-w-[220px] text-xs font-semibold leading-5 text-white/60">
                  {formatMoneyText(creditMinor)}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between gap-4 rounded-2xl bg-white/5 px-4 py-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-orange-400/35 text-orange-100">
                <ArrowUp className="h-5 w-5" />
              </span>
              <div className="text-right">
                <div className="text-sm text-white/78">بدهی شما</div>
                <div className="mt-1 text-lg font-black">{formatMoney(debtMinor)}</div>
                <div className="mt-1 max-w-[220px] text-xs font-semibold leading-5 text-white/60">
                  {formatMoneyText(debtMinor)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function SettlementRow({ item }: { item: SettlementSuggestion }) {
  const descriptionNumberText = getMemberCountText(item.description);

  return (
    <div className="grid grid-cols-[minmax(128px,176px)_32px_minmax(0,1fr)] items-center gap-3 border-b border-border px-4 py-3 last:border-b-0 sm:px-5">
      <div className="text-left">
        <div className="text-base font-black text-emerald-600">{formatMoney(item.amount)}</div>
        <div className="mt-1 text-[11px] font-semibold leading-5 text-slate-500">
          {formatMoneyText(item.amount)}
        </div>
      </div>

      <div className="flex justify-center text-emerald-600">
        <ArrowLeft className="h-5 w-5" />
      </div>

      <div className="flex min-w-0 items-center justify-end gap-3">
        <div className="min-w-0 text-right">
          <div className="truncate text-sm font-black text-text">{item.name}</div>
          <div className="mt-1 truncate text-xs text-muted">{item.description}</div>
          {descriptionNumberText ? (
            <div className="mt-1 truncate text-[11px] font-semibold text-slate-400">
              {descriptionNumberText}
            </div>
          ) : null}
        </div>
        <img
          src={item.avatar}
          alt=""
          className="h-11 w-11 shrink-0 rounded-full border border-border object-cover"
        />
      </div>
    </div>
  );
}

function EventRow({ event }: { event: DashboardEvent }) {
  const Icon = event.icon;

  return (
    <div className="grid grid-cols-[76px_minmax(0,1fr)_48px] items-center gap-3 border-b border-border px-4 py-3 last:border-b-0 sm:px-5">
      <div className="text-left text-xs font-semibold text-slate-500">
        <div>{event.time}</div>
        <div className="mt-1 leading-5 text-slate-400">{event.timeText}</div>
      </div>
      <p className="min-w-0 truncate text-right text-sm font-semibold text-slate-700">
        {event.title}
      </p>
      <div className={`flex h-10 w-10 items-center justify-center rounded-full ${event.toneClassName}`}>
        <Icon className="h-5 w-5" />
      </div>
    </div>
  );
}

function GroupArtwork({ type }: { type: Group['illustration'] }) {
  const Icon = type === 'trip' ? Mountain : type === 'home' ? Home : UtensilsCrossed;
  const background =
    type === 'trip'
      ? 'from-sky-100 via-emerald-50 to-lime-100 text-emerald-700'
      : type === 'home'
        ? 'from-amber-100 via-orange-50 to-emerald-100 text-orange-700'
        : 'from-orange-100 via-amber-50 to-rose-100 text-orange-700';

  return (
    <div className={`relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br ${background}`}>
      <div className="absolute inset-x-0 bottom-0 h-6 bg-white/35" />
      <Icon className="relative h-9 w-9" strokeWidth={1.8} />
    </div>
  );
}

function DashboardGroupCard({
  id,
  title,
  membersLabel,
  statusLabel,
  amount,
  tone,
  illustration,
  onOpen,
}: {
  id: string;
  title: string;
  membersLabel: string;
  statusLabel: string;
  amount: number;
  tone: Group['tone'];
  illustration: Group['illustration'];
  onOpen: (groupId: string) => void;
}) {
  const memberCountText = getMemberCountText(membersLabel);

  return (
    <button
      type="button"
      onClick={() => onOpen(id)}
      className="grid min-h-[142px] grid-cols-[minmax(0,1fr)_92px] items-center gap-4 rounded-2xl border border-border bg-white px-5 py-4 text-right transition hover:-translate-y-0.5 hover:border-emerald-200 hover:shadow-[0_18px_40px_rgba(15,23,42,0.07)]"
    >
      <div className="min-w-0">
        <h3 className="truncate text-lg font-black text-text">{title}</h3>
        <p className="mt-1 text-sm text-muted">{membersLabel}</p>
        {memberCountText ? (
          <p className="mt-1 text-xs font-semibold text-slate-400">{memberCountText}</p>
        ) : null}
        <p className={['mt-4 text-xs font-bold', tone === 'positive' ? 'text-emerald-600' : 'text-rose-500'].join(' ')}>
          {statusLabel}
        </p>
        <div className={['mt-1 text-xl font-black tracking-normal', tone === 'positive' ? 'text-emerald-600' : 'text-rose-500'].join(' ')}>
          {formatSignedMoney(amount)}
        </div>
        <p className={['mt-1 text-xs font-semibold leading-5', tone === 'positive' ? 'text-emerald-700/70' : 'text-rose-500/70'].join(' ')}>
          {formatSignedMoneyText(amount)}
        </p>
      </div>
      <GroupArtwork type={illustration} />
    </button>
  );
}

function getDashboardTotals(groupBalances: GroupBalanceSummary[] = []) {
  const activeBalances = groupBalances.filter((item) => item.status !== 'ARCHIVED');

  if (activeBalances.length === 0) {
    return {
      creditMinor: 12450000,
      debtMinor: 3230000,
    };
  }

  return activeBalances.reduce(
    (totals, item) => {
      if (item.netMinor > 0) {
        totals.creditMinor += item.netMinor;
      }

      if (item.netMinor < 0) {
        totals.debtMinor += Math.abs(item.netMinor);
      }

      return totals;
    },
    { creditMinor: 0, debtMinor: 0 },
  );
}

function getGroupCards(groups: Group[], groupBalances: GroupBalanceSummary[] = []) {
  const activeGroups = groups.filter((group) => group.status !== 'ARCHIVED').slice(0, 3);
  const balanceMap = new Map(groupBalances.map((item) => [String(item.groupId), item]));

  if (activeGroups.length === 0) {
    return fallbackGroups;
  }

  return activeGroups.map((group) => {
    const balance = balanceMap.get(String(group.id));
    const amount = balance?.netMinor ?? 0;
    const tone: Group['tone'] = amount < 0 ? 'negative' : 'positive';

    return {
      id: String(group.id),
      title: group.name,
      membersLabel: group.membersLabel,
      statusLabel: amount < 0 ? 'شما بدهکار هستید' : amount > 0 ? 'شما طلبکار هستید' : 'تسویه شده',
      amount,
      tone,
      illustration: group.illustration,
    };
  });
}

export function DashboardPage({
  groups,
  groupBalances = [],
  balancesLoading = false,
  onCreateGroup,
  onOpenGroups,
  onOpenGroup,
  onOpenActivities,
  onOpenWallet,
}: DashboardPageProps) {
  const totals = getDashboardTotals(groupBalances);
  const groupCards = getGroupCards(groups, groupBalances);

  return (
    <main className="px-6 py-5 sm:px-8 sm:py-7 lg:px-10 xl:px-14 2xl:px-16">
      <div className="mx-auto max-w-[1160px] space-y-4 sm:space-y-5">
        <section className="grid gap-4 lg:grid-cols-3">
          <QuickActionCard
            icon={WalletCards}
            title="هزینه جدید"
            description="ثبت هزینه و تقسیم"
            onClick={onOpenActivities}
          />
          <QuickActionCard
            icon={UserPlus}
            title="گروه جدید"
            description="ایجاد فضای گروهی"
            onClick={onCreateGroup}
          />
          <QuickActionCard
            icon={CreditCard}
            title="تسویه حساب"
            description="مشاهده تسویه‌های پیشنهادی"
            onClick={onOpenWallet}
          />
        </section>

        <BalanceHero
          creditMinor={totals.creditMinor}
          debtMinor={totals.debtMinor}
          loading={balancesLoading}
        />

        <section className="grid gap-4 xl:grid-cols-2">
          <SectionCard className="overflow-hidden">
            <SectionHeader
              title="تسویه‌های پیشنهادی"
              actionLabel="مشاهده همه"
              icon={<ReceiptText className="h-5 w-5 text-slate-700" />}
              onAction={onOpenWallet}
            />
            <div>
              {settlementSuggestions.map((item) => (
                <SettlementRow key={item.id} item={item} />
              ))}
            </div>
            <button
              type="button"
              onClick={onOpenWallet}
              className="flex h-12 w-full items-center justify-center gap-2 border-t border-border text-sm font-black text-emerald-600 transition hover:bg-emerald-50/45"
            >
              مشاهده همه تسویه‌ها
              <ArrowLeft className="h-4 w-4" />
            </button>
          </SectionCard>

          <SectionCard className="overflow-hidden">
            <SectionHeader
              title="اقدامات و رویدادها"
              actionLabel="مشاهده همه"
              icon={<Bell className="h-5 w-5 text-slate-700" />}
              onAction={onOpenActivities}
            />
            <div>
              {dashboardEvents.map((event) => (
                <EventRow key={event.id} event={event} />
              ))}
            </div>
          </SectionCard>
        </section>

        <SectionCard className="p-5 sm:p-6">
          <div className="mb-5 flex items-center justify-between gap-4">
            <button
              type="button"
              onClick={onOpenGroups}
              className="text-xs font-extrabold text-emerald-600 transition hover:text-emerald-700"
            >
              مشاهده همه گروه‌ها
            </button>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-black text-text sm:text-xl">گروه‌های فعال شما</h2>
              <Users className="h-5 w-5 text-slate-700" />
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            {groupCards.map((group) => (
              <DashboardGroupCard
                key={group.id}
                id={group.id}
                title={group.title}
                membersLabel={group.membersLabel}
                statusLabel={group.statusLabel}
                amount={group.amount}
                tone={group.tone}
                illustration={group.illustration}
                onOpen={onOpenGroup}
              />
            ))}
          </div>
        </SectionCard>

        <section className="grid gap-4 lg:hidden">
          <div className="rounded-3xl border border-emerald-100 bg-emerald-50/60 p-5 text-right shadow-soft">
            <div className="flex items-start justify-between gap-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm">
                <Gift className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-black text-emerald-900">همدنگ را به دوستانتان معرفی کنید</h2>
                <p className="mt-2 text-sm leading-7 text-muted">
                  با دعوت از دوستان، مدیریت هزینه‌ها آسان‌تر می‌شود.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
