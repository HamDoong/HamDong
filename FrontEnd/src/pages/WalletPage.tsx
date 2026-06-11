import {
  ArrowDown,
  ArrowUp,
  Banknote,
  ChevronLeft,
  Clock3,
  CreditCard,
  Download,
  Eye,
  History,
  Landmark,
  Link2,
  Plus,
  Send,
  Settings,
  ShieldCheck,
  Star,
  WalletCards,
} from 'lucide-react';

type TransactionTone = 'positive' | 'negative';
type TransactionStatus = 'received' | 'paid';

interface WalletTransaction {
  id: number;
  title: string;
  subtitle: string;
  time: string;
  amount: number;
  status: TransactionStatus;
  tone: TransactionTone;
  avatar: string;
  avatarClassName: string;
}

interface PaymentMethod {
  id: number;
  title: string;
  maskedNumber: string;
  badge?: string;
  icon: string;
}

const transactions: WalletTransaction[] = [
  {
    id: 1,
    title: 'دریافت از رضا کریمی',
    subtitle: 'بابت پرداخت هزینه شام گروه',
    time: 'امروز، ۱۰:۳۰',
    amount: 90000,
    status: 'received',
    tone: 'positive',
    avatar: 'ر',
    avatarClassName: 'from-emerald-300 to-teal-700',
  },
  {
    id: 2,
    title: 'پرداخت به علی رضایی',
    subtitle: 'هزینه اقامت سفر شمال',
    time: 'دیروز، ۱۸:۴۵',
    amount: -90000,
    status: 'paid',
    tone: 'negative',
    avatar: 'ع',
    avatarClassName: 'from-sky-300 to-cyan-700',
  },
  {
    id: 3,
    title: 'افزایش موجودی',
    subtitle: 'انتقال از بانک ملت',
    time: '۸ خرداد، ۱۴:۲۰',
    amount: 500000,
    status: 'received',
    tone: 'positive',
    avatar: 'م',
    avatarClassName: 'from-red-300 to-rose-600',
  },
  {
    id: 4,
    title: 'پرداخت به هتل آرامش',
    subtitle: 'رزرو اتاق دو تخته',
    time: '۷ خرداد، ۱۶:۱۰',
    amount: -40000,
    status: 'paid',
    tone: 'negative',
    avatar: 'ه',
    avatarClassName: 'from-emerald-300 to-green-700',
  },
  {
    id: 5,
    title: 'دریافت از سارا محمدی',
    subtitle: 'سهم تور تفریحی',
    time: '۶ خرداد، ۱۲:۴۰',
    amount: 60000,
    status: 'received',
    tone: 'positive',
    avatar: 'س',
    avatarClassName: 'from-fuchsia-300 to-purple-700',
  },
];

const paymentMethods: PaymentMethod[] = [
  {
    id: 1,
    title: 'بانک ملت',
    maskedNumber: '**** **** **** ۱۲۳۴',
    badge: 'پیش‌فرض',
    icon: '🏦',
  },
  {
    id: 2,
    title: 'بانک سامان',
    maskedNumber: '**** **** **** ۵۶۷۸',
    icon: '💳',
  },
  {
    id: 3,
    title: 'کارت ملت',
    maskedNumber: '**** **** **** ۹۰۱۲',
    icon: '🔴',
  },
];

function formatMoney(amount: number) {
  const prefix = amount > 0 ? '+' : amount < 0 ? '-' : '';
  return `${prefix}${Math.abs(amount).toLocaleString('en-US')}`;
}

function ActionButton({
  icon: Icon,
  label,
}: {
  icon: typeof Plus;
  label: string;
}) {
  return (
    <button
      type="button"
      className="group flex h-[72px] items-center justify-center gap-3 rounded-3xl border border-border bg-white px-5 text-base font-bold text-text shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-200 hover:shadow-[0_18px_45px_rgba(15,23,42,0.07)]"
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 transition group-hover:bg-emerald-600 group-hover:text-white">
        <Icon className="h-5.5 w-5.5" />
      </span>
      {label}
    </button>
  );
}

function TransactionRow({ transaction }: { transaction: WalletTransaction }) {
  const isPositive = transaction.tone === 'positive';
  const DirectionIcon = isPositive ? ArrowDown : ArrowUp;

  return (
    <div className="grid grid-cols-[minmax(92px,150px)_minmax(0,1fr)] items-center gap-4 border-b border-border px-5 py-4 last:border-b-0 md:grid-cols-[minmax(120px,180px)_minmax(110px,150px)_minmax(0,1fr)]">
      <div className="text-left">
        <div
          className={[
            'text-lg font-extrabold tracking-[-0.02em]',
            isPositive ? 'text-emerald-600' : 'text-rose-500',
          ].join(' ')}
        >
          {formatMoney(transaction.amount)}
        </div>
        <div className="mt-1 text-xs font-semibold text-slate-500">تومان</div>
      </div>

      <div className="hidden md:flex md:justify-center">
        <span
          className={[
            'inline-flex h-8 items-center justify-center rounded-xl px-4 text-xs font-bold',
            transaction.status === 'received'
              ? 'bg-emerald-50 text-emerald-600'
              : 'bg-rose-50 text-rose-500',
          ].join(' ')}
        >
          {transaction.status === 'received' ? 'دریافت شد' : 'پرداخت شد'}
        </span>
      </div>

      <div className="flex min-w-0 items-center justify-end gap-4">
        <div className="min-w-0 text-right">
          <div className="truncate text-base font-bold text-text">{transaction.title}</div>
          <div className="mt-1 truncate text-sm text-muted">{transaction.subtitle}</div>
        </div>

        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br ${transaction.avatarClassName} text-sm font-bold text-white`}
        >
          {transaction.avatar}
        </div>

        <div className="hidden w-24 shrink-0 text-center text-sm text-muted sm:block">
          {transaction.time}
        </div>

        <div
          className={[
            'flex h-11 w-11 shrink-0 items-center justify-center rounded-full',
            isPositive ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-500',
          ].join(' ')}
        >
          <DirectionIcon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

function SummaryRow({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
}) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-muted">{label}</span>
      <span
        className={[
          'font-extrabold tracking-[-0.02em]',
          tone === 'positive' ? 'text-emerald-600' : '',
          tone === 'negative' ? 'text-rose-500' : '',
          tone === 'neutral' ? 'text-text' : '',
        ].join(' ')}
      >
        {value}
      </span>
    </div>
  );
}

function PaymentMethodCard({ method }: { method: PaymentMethod }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border py-4 last:border-b-0">
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-border bg-white text-xl shadow-sm">
          {method.icon}
        </div>
        <div className="text-right">
          <div className="font-bold text-text">{method.title}</div>
          <div dir="ltr" className="mt-1 text-sm text-muted">
            {method.maskedNumber}
          </div>
        </div>
      </div>

      {method.badge ? (
        <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-600">
          {method.badge}
        </span>
      ) : null}
    </div>
  );
}

function QuickAction({ icon: Icon, label }: { icon: typeof History; label: string }) {
  return (
    <button
      type="button"
      className="flex w-full items-center justify-between border-b border-border py-4 text-right text-sm font-semibold text-slate-700 transition last:border-b-0 hover:text-emerald-600"
    >
      <ChevronLeft className="h-4.5 w-4.5 text-slate-400" />
      <span className="flex items-center gap-3">
        {label}
        <Icon className="h-5 w-5 text-slate-500" />
      </span>
    </button>
  );
}

export function WalletPage() {
  return (
    <main className="px-4 py-6 sm:px-6 xl:px-8">
      <div className="mx-auto grid max-w-[1240px] gap-6 xl:grid-cols-[minmax(0,1fr)_354px]">
        <section className="min-w-0 space-y-6">
          <div className="text-right">
            <h1 className="text-[32px] font-extrabold leading-tight tracking-[-0.03em] text-text">
              کیف پول
            </h1>
            <p className="mt-2 text-base text-muted">
              مدیریت موجودی، تراکنش‌ها و روش‌های پرداخت
            </p>
          </div>

          <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-[#007A4F] via-[#009966] to-[#006B4D] p-7 text-white shadow-[0_24px_60px_rgba(0,128,89,0.22)]">
            <div className="pointer-events-none absolute -left-16 -top-16 h-52 w-52 rounded-full bg-white/10 blur-2xl" />
            <div className="pointer-events-none absolute bottom-3 right-8 text-[88px] opacity-15">
              <WalletCards />
            </div>

            <div className="relative grid gap-8 lg:grid-cols-[1.3fr_1fr_1fr_1fr] lg:items-center">
              <div className="text-right">
                <div className="mb-5 flex items-center justify-end gap-3 text-sm font-semibold text-white/85">
                  <Eye className="h-4.5 w-4.5" />
                  موجودی قابل استفاده
                </div>

                <div className="flex flex-wrap items-end justify-end gap-3">
                  <span className="text-[42px] font-black tracking-[-0.05em] md:text-[52px]">
                    ۱,۲۵۰,۰۰۰
                  </span>
                  <span className="mb-3 text-xl font-bold text-white/90">تومان</span>
                </div>

                <button
                  type="button"
                  className="mt-6 h-11 rounded-2xl border border-white/45 px-5 text-sm font-bold text-white transition hover:bg-white/12"
                >
                  مشاهده جزئیات
                </button>
              </div>

              <div className="border-white/20 lg:border-r lg:pr-8">
                <div className="text-sm text-white/75">در انتظار دریافت</div>
                <div className="mt-3 text-2xl font-black text-emerald-200">+۳۵۰,۰۰۰</div>
                <div className="mt-2 text-sm text-white/75">تومان</div>
              </div>

              <div className="border-white/20 lg:border-r lg:pr-8">
                <div className="text-sm text-white/75">در انتظار پرداخت</div>
                <div className="mt-3 text-2xl font-black text-orange-300">-۲۰۰,۰۰۰</div>
                <div className="mt-2 text-sm text-white/75">تومان</div>
              </div>

              <div className="border-white/20 lg:border-r lg:pr-8">
                <div className="text-sm text-white/75">موجودی رزرو شده</div>
                <div className="mt-3 text-2xl font-black text-white">۱۰۰,۰۰۰</div>
                <div className="mt-2 text-sm text-white/75">تومان</div>
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <ActionButton icon={Plus} label="افزایش موجودی" />
            <ActionButton icon={Send} label="ارسال پول" />
            <ActionButton icon={Download} label="برداشت" />
            <ActionButton icon={Landmark} label="انتقال به بانک" />
          </div>

          <div className="overflow-hidden rounded-3xl border border-border bg-white shadow-soft">
            <div className="flex items-center justify-between border-b border-border px-6 py-5">
              <button
                type="button"
                className="text-sm font-bold text-emerald-600 transition hover:text-emerald-700"
              >
                مشاهده همه
              </button>
              <h2 className="text-2xl font-extrabold text-text">تراکنش‌های اخیر</h2>
            </div>

            <div>
              {transactions.map((transaction) => (
                <TransactionRow key={transaction.id} transaction={transaction} />
              ))}
            </div>

            <button
              type="button"
              className="flex h-14 w-full items-center justify-center gap-2 border-t border-border text-sm font-bold text-slate-700 transition hover:bg-slate-50 hover:text-emerald-600"
            >
              مشاهده همه تراکنش‌ها
              <ChevronLeft className="h-4 w-4" />
            </button>
          </div>

          <div className="grid items-center gap-6 overflow-hidden rounded-3xl border border-border bg-white p-6 shadow-soft md:grid-cols-[220px_minmax(0,1fr)_160px]">
            <div className="mx-auto flex h-28 w-44 items-center justify-center rounded-[26px] bg-gradient-to-br from-emerald-500 to-teal-700 text-white shadow-[0_18px_40px_rgba(0,128,89,0.22)]">
              <WalletCards className="h-14 w-14" />
            </div>

            <div className="text-center md:text-right">
              <h3 className="text-xl font-black text-text">
                از کیف پول همدنگ برای تسویه سریع‌تر استفاده کنید
              </h3>
              <p className="mt-2 text-sm leading-7 text-muted">
                پرداخت‌ها و دریافت‌ها را در چند ثانیه انجام دهید و مدیریت هزینه‌های گروهی را ساده‌تر کنید.
              </p>
            </div>

            <button
              type="button"
              className="h-11 rounded-2xl bg-emerald-600 px-5 text-sm font-bold text-white transition hover:bg-emerald-700"
            >
              افزایش موجودی
            </button>
          </div>
        </section>

        <aside className="space-y-6">
          <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
            <div className="mb-6 flex items-center justify-between">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                <WalletCards className="h-5.5 w-5.5" />
              </div>
              <h2 className="text-xl font-extrabold text-text">خلاصه کیف پول</h2>
            </div>

            <div className="space-y-5">
              <SummaryRow label="موجودی قابل استفاده" value="۱,۲۵۰,۰۰۰ تومان" />
              <SummaryRow label="در انتظار دریافت" value="+۳۵۰,۰۰۰ تومان" tone="positive" />
              <SummaryRow label="در انتظار پرداخت" value="-۲۰۰,۰۰۰ تومان" tone="negative" />
              <SummaryRow label="موجودی رزرو شده" value="۱۰۰,۰۰۰ تومان" />
            </div>
          </div>

          <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
            <div className="mb-4 flex items-center justify-between">
              <button
                type="button"
                className="text-sm font-bold text-emerald-600 transition hover:text-emerald-700"
              >
                مدیریت
              </button>
              <h2 className="text-xl font-extrabold text-text">روش‌های پرداخت متصل</h2>
            </div>

            <div>
              {paymentMethods.map((method) => (
                <PaymentMethodCard key={method.id} method={method} />
              ))}
            </div>

            <button
              type="button"
              className="mt-4 flex h-12 w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-emerald-300 bg-emerald-50/40 text-sm font-bold text-emerald-700 transition hover:bg-emerald-50"
            >
              <Plus className="h-4.5 w-4.5" />
              افزودن روش جدید
            </button>
          </div>

          <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
            <h2 className="mb-3 text-xl font-extrabold text-text">اقدامات سریع</h2>
            <QuickAction icon={History} label="تاریخچه تراکنش‌ها" />
            <QuickAction icon={Banknote} label="درخواست پول" />
            <QuickAction icon={Link2} label="لینک پرداخت" />
            <QuickAction icon={Settings} label="تنظیمات کیف پول" />
          </div>

          <div className="rounded-3xl border border-emerald-100 bg-emerald-50/60 p-6 shadow-soft">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm">
                <Star className="h-5.5 w-5.5" />
              </div>
              <div className="text-right">
                <h2 className="text-lg font-extrabold text-text">کیف پول امن</h2>
                <p className="mt-1 text-sm text-muted">محافظت چندلایه</p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-2xl bg-white/70 p-4 text-right text-sm leading-7 text-slate-600">
              <ShieldCheck className="mt-1 h-5 w-5 shrink-0 text-emerald-600" />
              تراکنش‌ها با تأیید چندمرحله‌ای و تاریخچه قابل پیگیری مدیریت می‌شوند.
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
