import type { LucideIcon } from 'lucide-react';
import {
  ArrowLeft,
  Bell,
  Car,
  CheckCircle2,
  CreditCard,
  ImageUp,
  MoreVertical,
  ReceiptText,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  TrendingUp,
  Utensils,
  WalletCards,
  UsersRound,
} from 'lucide-react';

type LandingPageProps = {
  onStart: () => void;
};

type FeatureItem = {
  icon: LucideIcon;
  title: string;
  description: string;
  tone: string;
};

const avatarImages = [
  { src: '/landing/avatar-ali.png', alt: 'علی' },
  { src: '/landing/avatar-mahdi.png', alt: 'مهدی' },
  { src: '/landing/avatar-sara.png', alt: 'سارا' },
  { src: '/landing/avatar-nika.png', alt: 'نیکا' },
];

const expenseCards = [
  {
    icon: ShoppingCart,
    title: 'سوپرمارکت',
    amount: '1,250,000 تومان',
    meta: 'پرداخت توسط سارا',
    tone: 'orange',
  },
  {
    icon: Car,
    title: 'بنزین و عوارض',
    amount: '850,000 تومان',
    meta: 'پرداخت توسط احمد',
    tone: 'green',
  },
  {
    icon: Utensils,
    title: 'رستوران دربند',
    amount: '2,350,000 تومان',
    meta: 'پرداخت توسط مهدی',
    tone: 'orange',
  },
];

const heroHighlights = [
  { icon: WalletCards, label: 'هرکس به اندازه خودش' },
  { icon: ImageUp, label: 'رسید برای همه' },
  { icon: TrendingUp, label: 'تسویه بدون رودربایستی' },
];

const featureItems: FeatureItem[] = [
  {
    icon: UsersRound,
    title: 'دعوت با یک لینک',
    description: 'برای هر دورهمی یک فضای مشترک بسازید و اعضا را با لینک دعوت اضافه کنید',
    tone: 'bg-emerald-100 text-emerald-700',
  },
  {
    icon: ReceiptText,
    title: 'مالیات و سهم نابرابر',
    description: 'مبلغ هر نفر، مالیات و خدمات جداگانه حساب می‌شود تا سهم‌ها دقیق بماند',
    tone: 'bg-orange-100 text-orange-600',
  },
  {
    icon: ShieldCheck,
    title: 'رسید برای همه قابل مشاهده است',
    description: 'تصویر فاکتور و وضعیت حساب فقط برای اعضای مجاز رویداد قابل مشاهده است',
    tone: 'bg-emerald-100 text-emerald-700',
  },
  {
    icon: Bell,
    title: 'یادآوری بدون تعارف',
    description: 'یادآوری زمان‌بندی‌شده کمک می‌کند پیگیری پرداخت‌ها دستی و معذب‌کننده نباشد',
    tone: 'bg-orange-100 text-orange-600',
  },
];

const balances = [
  {
    avatar: avatarImages[1],
    label: 'مهدی به شما بدهکار است',
    amount: '1,250,000 تومان',
    tone: 'text-emerald-700',
  },
  {
    avatar: avatarImages[2],
    label: 'شما به سارا بدهکار هستید',
    amount: '850,000 تومان',
    tone: 'text-red-500',
  },
  {
    avatar: avatarImages[0],
    label: 'احمد به شما بدهکار است',
    amount: '650,000 تومان',
    tone: 'text-emerald-700',
  },
];

const useCases = [
  'هم‌خانه‌ای و زندگی مشترک',
  'سفرهای دوستانه و خانوادگی',
  'رستوران، کافه و خرید گروهی',
  'سفرها و رویدادهای چندپرداختی',
];

const howItWorks = [
  {
    icon: UsersRound,
    title: 'دورهمی را بساز',
    description: 'بعد از سفر، رستوران یا خرید مشترک، یک فضای حساب‌وکتاب بساز و لینک دعوت بفرست.',
  },
  {
    icon: ImageUp,
    title: 'خرج‌ها را شفاف ثبت کن',
    description: 'رسید، مالیات، خدمات و سهم‌های نابرابر را وارد کن تا همه چیز قابل پیگیری باشد.',
  },
  {
    icon: CreditCard,
    title: 'بدون پیگیری سخت تسویه کن',
    description: 'همدنگ سهم‌ها را محاسبه می‌کند و یادآوری‌های دوستانه می‌فرستد.',
  },
];

function Logo() {
  return (
    <div
      className="landing-logo flex min-w-0 shrink-0 items-center gap-3"
      dir="ltr"
      aria-label="همدنگ"
    >
      <div className="grid h-11 w-11 place-items-center rounded-[14px] bg-primary-gradient text-white shadow-button sm:h-12 sm:w-12 sm:rounded-[16px]">
        <span className="text-2xl font-extrabold leading-none sm:text-3xl">ه</span>
      </div>
      <span
        className="hidden whitespace-nowrap text-2xl font-extrabold tracking-normal text-slate-950 sm:inline"
        dir="rtl"
      >
        همدنگ
      </span>
    </div>
  );
}

function AvatarStack({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex flex-row-reverse items-center justify-end">
      {avatarImages.map((avatar, index) => (
        <img
          key={avatar.src}
          src={avatar.src}
          alt={avatar.alt}
          className={`rounded-full border-[3px] border-white object-cover shadow-[0_8px_18px_rgba(15,23,42,0.12)] ${
            compact ? 'h-8 w-8 -mr-2 first:mr-0' : 'h-11 w-11 -mr-3 first:mr-0'
          }`}
          style={{ zIndex: avatarImages.length - index }}
        />
      ))}
    </div>
  );
}

function ExpenseCard({
  item,
  index,
}: {
  item: (typeof expenseCards)[number];
  index: number;
}) {
  const Icon = item.icon;
  const toneClass =
    item.tone === 'green'
      ? 'bg-emerald-100 text-emerald-700'
      : 'bg-orange-100 text-orange-600';

  return (
    <article
      className={`hero-expense-card hero-expense-card-${index + 1}`}
      aria-label={`${item.title}، ${item.amount}`}
    >
      <div className={`grid h-10 w-10 place-items-center rounded-[15px] ${toneClass}`}>
        <Icon className="h-5 w-5" strokeWidth={2.6} />
      </div>
      <h3 className="mt-3 text-sm font-extrabold text-slate-950">{item.title}</h3>
      <p className="mt-1 text-sm font-extrabold text-slate-950">{item.amount}</p>
      <p className="mt-3 text-xs font-semibold text-slate-500">{item.meta}</p>
    </article>
  );
}

function HeroMockup() {
  return (
    <div className="hero-mockup" aria-label="نمایی از مدیریت هزینه‌های گروهی">
      <div className="hero-phone">
        <div className="hero-phone-screen">
          <div className="hero-phone-status" aria-hidden="true">
            <span>9:41</span>
            <span>LTE</span>
          </div>

          <div className="hero-phone-top rounded-t-[2rem] px-7 pb-10 pt-7 text-white">
            <div className="flex items-center justify-between">
              <ArrowLeft className="h-6 w-6" />
              <MoreVertical className="h-6 w-6" />
            </div>
            <div className="mt-14 text-center">
              <p className="text-xl font-extrabold">رویداد سفر شمال</p>
              <p className="mt-1 text-sm font-semibold text-white/80">7 عضو</p>
              <div className="mt-5 flex items-center justify-center gap-2">
                <span className="grid h-8 min-w-8 place-items-center rounded-full bg-slate-900 px-2 text-xs font-bold">
                  +3
                </span>
                <AvatarStack compact />
              </div>
            </div>
          </div>

          <div className="-mt-7 rounded-t-[2rem] bg-white px-7 py-8 shadow-[0_-10px_30px_rgba(15,23,42,0.05)]">
            <p className="text-center text-sm font-semibold text-slate-500">
              مجموع هزینه‌ها
            </p>
            <p className="mt-3 text-center text-3xl font-black text-slate-950">
              24,580,000
            </p>
            <p className="mt-1 text-center text-sm font-bold text-slate-500">تومان</p>

            <div className="mt-7 h-4 rounded-full bg-slate-100 p-1 shadow-inner">
              <div className="h-full w-[68%] rounded-full bg-primary-gradient shadow-[0_6px_18px_rgba(0,168,107,0.28)]" />
            </div>
            <div className="mt-5 flex items-center justify-between text-sm font-bold">
              <div>
                <p className="text-slate-500">پرداخت شده</p>
                <p className="mt-1 text-slate-950">18,450,000</p>
              </div>
              <div className="text-left">
                <p className="text-slate-500">باقی‌مانده</p>
                <p className="mt-1 text-slate-950">6,130,000</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="hero-expense-stack" aria-label="نمونه هزینه‌های ثبت شده">
        {expenseCards.map((item, index) => (
          <ExpenseCard key={item.title} item={item} index={index} />
        ))}
      </div>
    </div>
  );
}

function FeatureStrip() {
  return (
    <section className="relative z-10 mx-auto max-w-[1180px] px-5 py-8 sm:px-8 lg:px-10">
      <div className="feature-strip grid gap-5 rounded-[28px] border border-white/90 bg-white/[0.88] p-5 shadow-[0_24px_70px_rgba(15,23,42,0.08)] backdrop-blur md:grid-cols-2 lg:grid-cols-4 lg:p-7">
        {featureItems.map((item) => {
          const Icon = item.icon;

          return (
            <article key={item.title} className="feature-strip-item flex items-center gap-4 rounded-[22px] p-3">
              <div
                className={`grid h-14 w-14 shrink-0 place-items-center rounded-[18px] ${item.tone} shadow-[0_12px_26px_rgba(15,23,42,0.06)]`}
              >
                <Icon className="h-7 w-7" strokeWidth={2.5} />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-950">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm font-medium leading-7 text-slate-500">
                  {item.description}
                </p>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="relative z-10 mx-auto max-w-[1180px] px-5 py-12 sm:px-8 lg:px-10"
    >
      <div className="mb-8 text-center">
        <p className="text-sm font-extrabold text-primary">از ورود تا تسویه</p>
        <h2 className="mx-auto mt-3 max-w-3xl text-3xl font-black leading-[1.45] text-slate-950 sm:text-4xl">
          آخر دورهمی دنبال حساب‌کتاب دستی نرو
        </h2>
      </div>

      <div className="settlement-path grid gap-4 md:grid-cols-3">
        {howItWorks.map((item, index) => {
          const Icon = item.icon;

          return (
            <article
              key={item.title}
              className="how-card rounded-[26px] border border-white/[0.85] bg-white/[0.86] p-6 text-right shadow-[0_20px_54px_rgba(15,23,42,0.07)] backdrop-blur"
            >
              <div className="mb-6 flex items-center justify-between">
                <span className="grid h-12 w-12 place-items-center rounded-[18px] bg-emerald-50 text-primary shadow-[0_12px_26px_rgba(0,168,107,0.1)]">
                  <Icon className="h-6 w-6" strokeWidth={2.4} />
                </span>
                <span className="text-3xl font-black text-slate-200">
                  {String(index + 1).padStart(2, '0')}
                </span>
              </div>
              <h3 className="text-xl font-black text-slate-950">{item.title}</h3>
              <p className="mt-3 text-sm font-semibold leading-7 text-slate-500">
                {item.description}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function BalancePanel() {
  return (
    <div className="balance-panel relative mx-auto w-full max-w-[456px] rounded-[30px] border border-orange-200/70 bg-gradient-to-br from-orange-500 via-orange-300 to-orange-50 p-5 shadow-[0_28px_70px_rgba(249,115,22,0.22)]">
      <div className="mb-5 flex items-center justify-between rounded-[22px] bg-white/[0.72] px-4 py-3 text-right shadow-[0_12px_28px_rgba(15,23,42,0.08)] backdrop-blur">
        <div>
          <h3 className="text-lg font-black text-slate-950">موجودی‌ها</h3>
          <p className="mt-1 text-xs font-bold text-slate-500">وضعیت تسویه این رویداد</p>
        </div>
        <span className="grid h-11 w-11 place-items-center rounded-[16px] bg-orange-100 text-orange-600">
          <ReceiptText className="h-6 w-6" />
        </span>
      </div>
      <div className="space-y-2.5">
        {balances.map((balance) => (
          <div
            key={balance.label}
            className="balance-row flex min-h-[64px] items-center justify-between gap-3 rounded-[20px] bg-white px-4 py-2.5 shadow-[0_10px_24px_rgba(15,23,42,0.09)]"
          >
            <img
              src={balance.avatar.src}
              alt={balance.avatar.alt}
              className="h-11 w-11 rounded-full object-cover"
              loading="lazy"
            />
            <p className="min-w-0 flex-1 text-right text-sm font-extrabold leading-6 text-slate-700">
              {balance.label}
            </p>
            <p className={`shrink-0 text-sm font-black ${balance.tone}`}>
              {balance.amount}
            </p>
          </div>
        ))}
      </div>
      <button
        type="button"
        className="mt-4 flex h-14 w-full items-center justify-center gap-2 rounded-[20px] bg-gradient-to-l from-red-500 to-orange-500 px-5 text-base font-extrabold text-white shadow-[0_18px_36px_rgba(239,68,68,0.28)] transition hover:-translate-y-0.5"
      >
        <CreditCard className="h-6 w-6" />
        تسویه حساب‌ها (2,100,000 تومان)
      </button>
    </div>
  );
}

export function LandingPage({ onStart }: LandingPageProps) {
  return (
    <main className="landing-page relative min-h-screen overflow-hidden text-slate-950">
      <div className="landing-wave-lines" aria-hidden="true" />
      <img
        src="/landing/frame-dots.svg"
        alt=""
        aria-hidden="true"
        className="landing-frame-dots landing-frame-dots-1"
      />
      <img
        src="/landing/frame-dots.svg"
        alt=""
        aria-hidden="true"
        className="landing-frame-dots landing-frame-dots-2"
      />
      <header className="landing-header relative z-20 mx-auto flex max-w-[1180px] items-center justify-between gap-4 px-5 pb-4 pt-5 sm:px-8 sm:pb-5 sm:pt-6 lg:px-10 lg:py-7">
        <Logo />

        <nav
          className="hidden h-12 items-center gap-1 rounded-full border border-white/90 bg-white/[0.68] p-1 text-sm font-extrabold text-slate-600 shadow-[0_16px_38px_rgba(15,23,42,0.07)] backdrop-blur lg:flex"
          aria-label="ناوبری اصلی"
        >
          <a className="inline-flex h-10 items-center rounded-full bg-emerald-50 px-4 text-primary" href="#home">
            خانه
          </a>
          <a className="inline-flex h-10 items-center rounded-full px-4 transition hover:bg-white hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500/40" href="#how-it-works">
            چطور کار می‌کند
          </a>
          <a className="inline-flex h-10 items-center rounded-full px-4 transition hover:bg-white hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500/40" href="#features">
            امکانات
          </a>
        </nav>

        <div className="landing-actions flex items-center gap-3">
          <button
            type="button"
            onClick={onStart}
            className="landing-login-button hidden h-12 items-center px-6 text-sm font-extrabold shadow-[0_14px_34px_rgba(15,23,42,0.07)] transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500/40 sm:inline-flex"
          >
            ورود / ثبت‌نام
          </button>
        </div>
      </header>

      <section
        id="home"
        className="relative z-10 mx-auto grid max-w-[1180px] items-center gap-5 px-5 pb-4 pt-4 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:gap-8 lg:px-10 lg:pb-6"
      >
        <div className="w-full max-w-2xl justify-self-center text-center lg:justify-self-end lg:text-right">
          <div className="hero-eyebrow mx-auto inline-flex items-center gap-2 rounded-full border border-orange-200/70 bg-white/[0.78] px-5 py-2.5 text-sm font-extrabold text-orange-600 shadow-[0_14px_34px_rgba(249,115,22,0.1)] backdrop-blur lg:mx-0">
            <Sparkles className="h-4 w-4" fill="currentColor" />
            <span>مدیریت و تسویه هزینه‌های مشترک، شفاف و خودکار</span>
          </div>

          <h1 className="hero-title mt-7 text-[2.65rem] font-black leading-[1.28] text-slate-950 sm:text-5xl lg:text-6xl">
            همدنگ،
            <span className="hero-title-accent block">
              <span className="hero-title-accent-main">تسویه شفاف</span>
              <span className="hero-title-accent-emphasis">با کمترین دردسر</span>
            </span>
          </h1>
          <p className="mx-auto mt-5 max-w-[20rem] text-base font-semibold leading-8 text-slate-500 sm:max-w-xl sm:text-lg sm:leading-9 lg:mx-0">
            رسید را وارد کن، اعضا را دعوت کن، همدنگ سهم هر نفر را دقیق حساب می‌کند؛ حتی با مالیات، پرداخت نابرابر و چند نفر پرداخت‌کننده.
          </p>

          <div className="mx-auto mt-6 flex max-w-xl flex-wrap items-center justify-center gap-2.5 lg:mx-0 lg:justify-start">
            {heroHighlights.map((item) => {
              const Icon = item.icon;

              return (
                <span
                  key={item.label}
                  className="inline-flex h-10 items-center gap-2 rounded-full border border-white/90 bg-white/[0.72] px-4 text-sm font-extrabold text-slate-600 shadow-[0_10px_24px_rgba(15,23,42,0.05)] backdrop-blur"
                >
                  <Icon className="h-4 w-4 text-primary" />
                  {item.label}
                </span>
              );
            })}
          </div>

          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row lg:justify-start">
            <button
              type="button"
              onClick={onStart}
              className="inline-flex h-14 min-w-[190px] items-center justify-center gap-3 rounded-[20px] bg-primary-gradient px-6 text-base font-extrabold text-white shadow-button transition hover:-translate-y-1"
            >
              شروع حساب‌وکتاب
              <span className="grid h-10 w-10 place-items-center rounded-full bg-white text-slate-950">
                <ArrowLeft className="h-5 w-5" />
              </span>
            </button>
          </div>

          <p className="mx-auto mt-4 max-w-md text-sm font-bold leading-7 text-slate-500 lg:mx-0">
            وب‌اپ واکنش‌گرا؛ بدون نصب، مناسب مرورگر موبایل.
          </p>
        </div>

        <HeroMockup />
      </section>

      <HowItWorks />
      <FeatureStrip />

      <section
        id="features"
        className="feature-showcase-section relative z-10 mx-auto max-w-[1180px] px-5 pb-16 pt-10 sm:px-8 lg:px-10"
      >
        <div className="balance-cluster order-2 lg:order-2">
          <BalancePanel />
        </div>

        <div className="feature-copy order-1 lg:order-1">
          <div className="text-right">
            <h2 className="text-3xl font-black leading-[1.55] text-slate-950 sm:text-4xl">
              از خرج‌های پراکنده
              <span className="block text-orange-600">تا یک تسویه روشن</span>
            </h2>
            <ul className="mr-0 ml-auto mt-9 flex w-full max-w-[360px] flex-col items-stretch gap-5 lg:mx-0">
              {useCases.map((item) => (
                <li
                  key={item}
                  className="flex w-full items-center justify-start gap-3 text-right text-base font-bold text-slate-600"
                >
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-orange-600" />
                  <span className="block flex-1 text-right">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="relative z-10 mx-auto max-w-[1180px] px-5 pb-16 sm:px-8 lg:px-10">
        <div className="landing-final-cta overflow-hidden rounded-[32px] px-6 py-8 text-center shadow-[0_28px_78px_rgba(0,168,107,0.18)] sm:px-10 sm:py-10 lg:flex lg:items-center lg:justify-between lg:text-right">
          <div>
            <p className="text-sm font-black text-white/85">دعوت، ثبت خرج، تسویه</p>
            <h2 className="mt-3 text-3xl font-black leading-[1.45] text-white sm:text-4xl">
              اولین حساب‌وکتاب شفاف را شروع کن
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm font-semibold leading-7 text-white/[0.78] lg:mx-0">
              اعضا را دعوت کن، خرج‌ها را ثبت کن و بدون رودربایستی تسویه کن.
            </p>
          </div>

          <div className="mt-7 flex flex-col items-center justify-center gap-4 sm:flex-row lg:mt-0 lg:justify-end">
            <AvatarStack compact />
            <button
              type="button"
              onClick={onStart}
              className="inline-flex h-14 min-w-[190px] items-center justify-center gap-3 rounded-[20px] bg-white px-6 text-base font-extrabold text-emerald-700 shadow-[0_18px_38px_rgba(15,23,42,0.14)] transition hover:-translate-y-0.5"
            >
              شروع حساب‌وکتاب
              <span className="grid h-10 w-10 place-items-center rounded-full bg-emerald-50 text-slate-950">
                <ArrowLeft className="h-5 w-5" />
              </span>
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
