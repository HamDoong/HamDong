import type { LucideIcon } from 'lucide-react';
import {
  ArrowLeft,
  Bell,
  Car,
  CheckCircle2,
  CreditCard,
  Download,
  Heart,
  MoreVertical,
  Play,
  Plus,
  ReceiptText,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Utensils,
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
    time: 'دیروز',
    tone: 'orange',
  },
  {
    icon: Car,
    title: 'بنزین و عوارض',
    amount: '850,000 تومان',
    meta: 'پرداخت توسط احمد',
    time: '2 روز پیش',
    tone: 'green',
  },
  {
    icon: Utensils,
    title: 'رستوران دربند',
    amount: '2,350,000 تومان',
    meta: 'پرداخت توسط مهدی',
    time: '3 روز پیش',
    tone: 'orange',
  },
];

const featureItems: FeatureItem[] = [
  {
    icon: UsersRound,
    title: 'گروه‌های نامحدود',
    description: 'هر تعداد گروه که می‌خواهید بسازید و مدیریت کنید',
    tone: 'bg-emerald-100 text-emerald-700',
  },
  {
    icon: ReceiptText,
    title: 'محاسبه خودکار',
    description: 'سهم هر نفر به‌صورت خودکار محاسبه می‌شود',
    tone: 'bg-orange-100 text-orange-600',
  },
  {
    icon: ShieldCheck,
    title: 'شفاف و امن',
    description: 'همه چیز شفاف و اطلاعات شما کاملا امن است',
    tone: 'bg-emerald-100 text-emerald-700',
  },
  {
    icon: Bell,
    title: 'یادآوری پرداخت',
    description: 'یادآوری هوشمند برای تسویه حساب‌ها',
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
  'سفرهای دوستانه و خانوادگی',
  'زندگی مشترک و هم‌خانه‌ای',
  'پروژه‌های کاری و تیمی',
  'کلاس‌ها و دوره‌های آموزشی',
];

function Logo() {
  return (
    <div
      className="landing-logo flex min-w-0 shrink-0 items-center gap-3"
      dir="ltr"
      aria-label="هم‌هزینه"
    >
      <div className="grid h-11 w-11 place-items-center rounded-[14px] bg-primary-gradient text-white shadow-button sm:h-12 sm:w-12 sm:rounded-[16px]">
        <span className="text-2xl font-extrabold leading-none sm:text-3xl">ه</span>
      </div>
      <span
        className="hidden whitespace-nowrap text-2xl font-extrabold tracking-normal text-slate-950 sm:inline"
        dir="rtl"
      >
        هم‌هزینه
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
      <div className={`grid h-12 w-12 place-items-center rounded-[18px] ${toneClass}`}>
        <Icon className="h-6 w-6" strokeWidth={2.6} />
      </div>
      <h3 className="mt-5 text-lg font-extrabold text-slate-950">{item.title}</h3>
      <p className="mt-1 text-base font-extrabold text-slate-950">{item.amount}</p>
      <p className="mt-5 text-sm font-medium text-slate-400">{item.meta}</p>
      <p className="mt-1 text-xs font-semibold text-slate-400">{item.time}</p>
    </article>
  );
}

function HeroMockup() {
  return (
    <div className="hero-mockup" aria-label="نمایی از مدیریت هزینه‌های گروهی">
      <div className="hero-avatar hero-avatar-1">
        <img src="/landing/avatar-ali.png" alt="عضو گروه" />
      </div>
      <div className="hero-avatar hero-avatar-2">
        <img src="/landing/avatar-mahdi.png" alt="عضو گروه" />
      </div>
      <div className="hero-avatar hero-avatar-3">
        <img src="/landing/avatar-sara.png" alt="عضو گروه" />
      </div>
      <div className="hero-avatar hero-avatar-4">
        <img src="/landing/avatar-nika.png" alt="عضو گروه" />
      </div>

      <div className="hero-phone">
        <div className="rounded-t-[2rem] bg-primary-gradient px-7 pb-10 pt-7 text-white">
          <div className="flex items-center justify-between">
            <ArrowLeft className="h-6 w-6" />
            <MoreVertical className="h-6 w-6" />
          </div>
          <div className="mt-14 text-center">
            <p className="text-xl font-extrabold">سفر شمال</p>
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
          <p className="text-center text-sm font-semibold text-slate-400">
            مجموع هزینه‌ها
          </p>
          <p className="mt-3 text-center text-3xl font-black text-slate-950">
            24,580,000
          </p>
          <p className="mt-1 text-center text-sm font-bold text-slate-500">تومان</p>

          <div className="mt-7 h-4 rounded-full bg-slate-100 p-1">
            <div className="h-full w-[68%] rounded-full bg-primary-gradient" />
          </div>
          <div className="mt-5 flex items-center justify-between text-sm font-bold">
            <div>
              <p className="text-slate-400">پرداخت شده</p>
              <p className="mt-1 text-slate-950">18,450,000</p>
            </div>
            <div className="text-left">
              <p className="text-slate-400">باقی‌مانده</p>
              <p className="mt-1 text-slate-950">6,130,000</p>
            </div>
          </div>
        </div>
      </div>

      {expenseCards.map((item, index) => (
        <ExpenseCard key={item.title} item={item} index={index} />
      ))}

      <button
        type="button"
        className="hero-plus-button"
        aria-label="افزودن هزینه جدید"
      >
        <Plus className="h-8 w-8" />
      </button>

      <div className="hero-add-note">
        <img
          className="hero-add-arrow"
          src="/landing/arrow.png"
          alt=""
          aria-hidden="true"
        />
        <span>افزودن هزینه جدید</span>
      </div>
    </div>
  );
}

function FeatureStrip() {
  return (
    <section className="relative z-10 mx-auto max-w-6xl px-5 pb-8 sm:px-8 lg:px-10">
      <div className="grid gap-6 rounded-[28px] border border-white/80 bg-white/86 p-6 shadow-[0_24px_70px_rgba(15,23,42,0.08)] backdrop-blur md:grid-cols-2 lg:grid-cols-4 lg:p-8">
        {featureItems.map((item) => {
          const Icon = item.icon;

          return (
            <article key={item.title} className="flex items-center gap-4">
              <div
                className={`grid h-14 w-14 shrink-0 place-items-center rounded-[18px] ${item.tone}`}
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

function BalancePanel() {
  return (
    <div className="balance-panel relative mx-auto w-full max-w-[430px] rounded-[30px] bg-gradient-to-br from-orange-400 via-orange-200 to-white p-5 shadow-[0_24px_70px_rgba(244,126,24,0.22)]">
      <h3 className="mb-5 text-center text-lg font-black text-slate-950">موجودی‌ها</h3>
      <div className="space-y-3">
        {balances.map((balance) => (
          <div
            key={balance.label}
            className="flex items-center justify-between gap-3 rounded-[22px] bg-white px-4 py-3 shadow-[0_10px_26px_rgba(15,23,42,0.07)]"
          >
            <img
              src={balance.avatar.src}
              alt={balance.avatar.alt}
              className="h-12 w-12 rounded-full object-cover"
              loading="lazy"
            />
            <p className="min-w-0 flex-1 text-right text-sm font-bold text-slate-700">
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
        className="mt-5 flex h-14 w-full items-center justify-center gap-2 rounded-[20px] bg-gradient-to-l from-red-500 to-orange-500 px-5 text-base font-extrabold text-white shadow-[0_16px_32px_rgba(239,68,68,0.28)]"
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
      <div className="landing-dot-grid right-0 top-44 h-72 w-72 opacity-40" />
      <div className="landing-dot-grid bottom-16 left-4 h-72 w-72 opacity-35" />

      <header className="landing-header relative z-20 mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 pb-4 pt-5 sm:px-8 sm:pb-5 sm:pt-6 lg:px-10 lg:py-7">
        <Logo />

        <nav
          className="hidden h-12 items-center gap-1 rounded-full border border-white/80 bg-white/60 p-1 text-sm font-extrabold text-slate-600 shadow-[0_14px_34px_rgba(15,23,42,0.06)] backdrop-blur lg:flex"
          aria-label="ناوبری اصلی"
        >
          <a className="inline-flex h-10 items-center rounded-full bg-emerald-50 px-4 text-primary" href="#home">
            خانه
          </a>
          <a className="inline-flex h-10 items-center rounded-full px-4 transition hover:bg-white hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500/40" href="#features">
            امکانات
          </a>
          <a className="inline-flex h-10 items-center rounded-full px-4 transition hover:bg-white hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500/40" href="#pricing">
            قیمت‌ها
          </a>
          <a className="inline-flex h-10 items-center rounded-full px-4 transition hover:bg-white hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500/40" href="#blog">
            وبلاگ
          </a>
          <a className="inline-flex h-10 items-center rounded-full px-4 transition hover:bg-white hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500/40" href="#about">
            درباره ما
          </a>
        </nav>

        <div className="landing-actions flex items-center gap-3">
          <button
            type="button"
            onClick={onStart}
            className="hidden h-12 items-center rounded-[18px] bg-white/85 px-6 text-sm font-extrabold text-slate-950 shadow-[0_14px_34px_rgba(15,23,42,0.07)] ring-1 ring-white/80 transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500/40 sm:inline-flex"
          >
            ورود
          </button>
          <button
            type="button"
            className="inline-flex h-12 items-center justify-center gap-2 rounded-[18px] bg-primary-gradient px-4 text-sm font-extrabold text-white shadow-button transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500/40 sm:px-6"
          >
            <Download className="h-5 w-5" />
            دانلود اپلیکیشن
          </button>
        </div>
      </header>

      <section
        id="home"
        className="relative z-10 mx-auto grid max-w-7xl items-center gap-8 px-5 pb-6 pt-6 sm:px-8 lg:grid-cols-[0.92fr_1.08fr] lg:px-10 lg:pb-10"
      >
        <div className="max-w-2xl justify-self-end text-center lg:text-right">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full bg-orange-50 px-5 py-3 text-sm font-extrabold text-orange-600 shadow-[0_10px_30px_rgba(249,115,22,0.08)] lg:mx-0">
            <Sparkles className="h-4 w-4" fill="currentColor" />
            مدیریت هزینه‌ها گروهی، ساده و شفاف
          </div>

          <h1 className="mt-9 text-4xl font-black leading-[1.35] text-slate-950 sm:text-6xl lg:text-7xl">
            هزینه‌ها را
            <span className="block text-primary">با هم تقسیم کنید</span>
          </h1>
          <p className="mx-auto mt-7 max-w-[20rem] text-base font-semibold leading-9 text-slate-500 sm:max-w-xl sm:text-lg sm:leading-10 lg:mx-0">
            با هم‌هزینه، هزینه‌های گروهی سفر، زندگی مشترک یا هر پروژه‌ای را
            با سادگی مدیریت کنید.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row lg:justify-start">
            <button
              type="button"
              onClick={onStart}
              className="inline-flex h-16 min-w-[210px] items-center justify-center gap-3 rounded-[24px] bg-primary-gradient px-7 text-lg font-extrabold text-white shadow-button transition hover:-translate-y-1"
            >
              شروع رایگان
              <span className="grid h-11 w-11 place-items-center rounded-full bg-white text-slate-950">
                <ArrowLeft className="h-6 w-6" />
              </span>
            </button>
            <button
              type="button"
              className="inline-flex h-16 min-w-[210px] items-center justify-center gap-4 rounded-[24px] bg-white px-7 text-lg font-extrabold text-slate-950 shadow-[0_14px_34px_rgba(15,23,42,0.07)] transition hover:-translate-y-1"
            >
              تماشای ویدیو
              <span className="grid h-11 w-11 place-items-center rounded-full bg-white shadow-[0_10px_22px_rgba(15,23,42,0.09)]">
                <Play className="h-5 w-5 fill-slate-950" />
              </span>
            </button>
          </div>

          <div className="mt-11 flex flex-col items-center justify-center gap-6 sm:flex-row lg:justify-start">
            <AvatarStack />
            <p className="text-base font-semibold leading-8 text-slate-500">
              <span className="font-black text-orange-500">+12K</span> کاربر فعال
              <span className="block">به ما اعتماد کرده‌اند</span>
            </p>
            <div className="grid h-16 w-16 place-items-center rounded-full bg-white text-primary shadow-[0_14px_34px_rgba(15,23,42,0.07)]">
              <Heart className="h-7 w-7" fill="currentColor" />
            </div>
          </div>
        </div>

        <HeroMockup />
      </section>

      <FeatureStrip />

      <section
        id="features"
        className="feature-showcase-section relative z-10 mx-auto max-w-7xl px-5 pb-24 pt-10 sm:px-8 lg:px-10"
      >
        <div className="feature-orb rounded-full bg-gradient-to-br from-emerald-500 to-emerald-300" />

        <div className="balance-cluster order-3 lg:order-1">
          <div className="reminder-card rounded-[24px] bg-white/92 p-5 text-right shadow-[0_24px_60px_rgba(239,68,68,0.16)]">
            <div className="mb-4 flex items-center justify-between">
              <div className="grid h-11 w-11 place-items-center rounded-full bg-red-100 text-red-500">
                <Bell className="h-5 w-5" />
              </div>
              <span className="grid h-11 w-11 place-items-center rounded-full bg-red-500 text-xl font-black text-white">
                !
              </span>
            </div>
            <h3 className="text-base font-black text-red-500">یادآوری پرداخت</h3>
            <p className="mt-2 text-sm font-semibold leading-7 text-slate-500">
              مهدی هنوز سهم خود را پرداخت نکرده است
            </p>
          </div>
          <BalancePanel />
        </div>

        <div className="feature-copy order-1 lg:order-3">
          <div className="text-center lg:text-right">
            <h2 className="text-3xl font-black leading-[1.55] text-slate-950 sm:text-4xl">
              برای هر نوع هزینه گروهی
              <span className="block text-orange-500">یک راه‌حل هوشمند</span>
            </h2>
            <ul className="mt-9 space-y-5">
              {useCases.map((item) => (
                <li
                  key={item}
                  className="flex items-center justify-center gap-3 text-base font-bold text-slate-600 lg:justify-start"
                >
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-orange-500" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="high-five-card order-2 lg:order-2">
          <img
            src="/landing/high-five.png"
            alt="دو دست در حال همکاری برای تقسیم هزینه‌ها"
            className="high-five-image"
            loading="lazy"
          />
        </div>
      </section>
    </main>
  );
}
