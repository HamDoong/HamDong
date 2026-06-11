import { useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  ArrowLeft,
  Bell,
  Calculator,
  Check,
  Eye,
  EyeOff,
  Headphones,
  ShieldCheck,
  Smartphone,
  Smile,
  WalletCards,
} from 'lucide-react';
import './LoginPage.css';

type LoginPageProps = {
  onLogin: () => void;
  onSignUp?: () => void;
};

type BenefitItem = {
  icon: LucideIcon;
  title: string;
  description: string;
};

const benefitItems: BenefitItem[] = [
  {
    icon: Calculator,
    title: 'محاسبه دقیق سهم‌ها',
    description: 'با در نظر گرفتن مالیات و خدمات',
  },
  {
    icon: Bell,
    title: 'یادآوری دوستانه',
    description: 'بدون مزاحمت و پیگیری!',
  },
  {
    icon: WalletCards,
    title: 'تسویه سریع و شفاف',
    description: 'کیف پول داخلی و گزارش‌های دقیق',
  },
];

export const phoneDigitOnlyPattern = /[^0-9۰-۹٠-٩]/g;

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="login-social-icon" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09Z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A10.99 10.99 0 0 0 12 23Z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.1A6.6 6.6 0 0 1 5.5 12c0-.73.12-1.44.34-2.1V7.06H2.18A10.99 10.99 0 0 0 1 12c0 1.77.42 3.44 1.18 4.94l3.66-2.84Z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A10.99 10.99 0 0 0 2.18 7.06L5.84 9.9C6.71 7.31 9.14 5.38 12 5.38Z"
      />
    </svg>
  );
}

function AppleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="login-social-icon" aria-hidden="true">
      <path
        fill="currentColor"
        d="M16.96 12.9c-.03-2.53 2.06-3.75 2.16-3.81-1.18-1.72-3.01-1.96-3.65-1.98-1.55-.16-3.02.91-3.8.91-.79 0-2-.89-3.29-.86-1.69.03-3.25.98-4.12 2.5-1.76 3.05-.45 7.56 1.26 10.03.84 1.21 1.84 2.57 3.15 2.52 1.26-.05 1.74-.82 3.27-.82 1.52 0 1.96.82 3.3.79 1.36-.03 2.22-1.24 3.05-2.46.96-1.4 1.35-2.76 1.37-2.83-.03-.01-2.65-1.02-2.7-3.99ZM14.45 5.47c.69-.84 1.16-2.01 1.03-3.17-.99.04-2.2.66-2.92 1.5-.64.74-1.21 1.93-1.05 3.06 1.1.09 2.24-.56 2.94-1.39Z"
      />
    </svg>
  );
}

function BenefitList() {
  return (
    <div className="login-benefits">
      {benefitItems.map((item) => {
        const Icon = item.icon;

        return (
          <div className="login-benefit" key={item.title}>
            <span className="login-benefit-icon">
              <Icon strokeWidth={2.5} />
            </span>
            <span>
              <strong>{item.title}</strong>
              <small>{item.description}</small>
            </span>
          </div>
        );
      })}
    </div>
  );
}

function LoginForm({ onLogin, onSignUp }: LoginPageProps) {
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState('');
  const PasswordIcon = passwordVisible ? Eye : EyeOff;

  return (
    <form
      className="login-card"
      onSubmit={(event) => {
        event.preventDefault();
        onLogin();
      }}
    >
      <div className="login-card-heading">
        <h1>
          ورود به <span>همدنگ</span>
        </h1>
        <p>خوش برگشتی! لطفاً وارد حساب کاربری خود شوید.</p>
      </div>

      <label className="login-field">
        <span>شماره موبایل</span>
        <div className="login-input-wrap">
          <input
            type="tel"
            name="phone"
            inputMode="numeric"
            autoComplete="tel"
            value={phoneNumber}
            onChange={(event) => {
              setPhoneNumber(event.target.value.replace(phoneDigitOnlyPattern, ''));
            }}
            pattern="[0-9۰-۹٠-٩]*"
            placeholder=" ۰۹۱۲ ۱۳۳ ۴۵ ۶۷"
            aria-label="شماره موبایل"
          />
          <Smartphone className="login-input-icon" strokeWidth={2.4} />
        </div>
      </label>

      <label className="login-field">
        <span>رمز عبور</span>
        <div className="login-input-wrap">
          <input
            type={passwordVisible ? 'text' : 'password'}
            name="password"
            autoComplete="current-password"
            placeholder="رمز عبور خود را وارد کنید"
            aria-label="رمز عبور"
          />
          <button
            type="button"
            className="login-password-toggle"
            aria-label={passwordVisible ? 'Ù¾Ù†Ù‡Ø§Ù† Ú©Ø±Ø¯Ù† Ø±Ù…Ø² Ø¹Ø¨ÙˆØ±' : 'Ù†Ù…Ø§ÛŒØ´ Ø±Ù…Ø² Ø¹Ø¨ÙˆØ±'}
            aria-pressed={passwordVisible}
            onClick={() => setPasswordVisible((visible) => !visible)}
          >
            <PasswordIcon className="login-input-icon login-input-icon-muted" />
          </button>
        </div>
      </label>

      <div className="login-options-row">
        <a href="#forgot">رمز عبور را فراموش کرده‌اید؟</a>
        <label>
          <span>مرا به خاطر بسپار</span>
          <input type="checkbox" />
        </label>
      </div>

      <button className="login-submit" type="submit">
        <ArrowLeft />
        <span>ورود</span>
      </button>

      <div className="login-divider">
        <span>یا با حساب‌های دیگر وارد شوید</span>
      </div>

      <div className="login-social-grid">
        <button type="button" aria-label="ÙˆØ±ÙˆØ¯ Ø¨Ø§ Ø­Ø³Ø§Ø¨ Ø§Ù¾Ù„">
          <AppleIcon />
          <span>ورود با اپل</span>
        </button>
        <button type="button" aria-label="ÙˆØ±ÙˆØ¯ Ø¨Ø§ Ø­Ø³Ø§Ø¨ Ú¯ÙˆÚ¯Ù„">
          <GoogleIcon />
          <span>ورود با گوگل</span>
        </button>
      </div>

      <p className="login-register">
        حساب کاربری ندارید؟
        <button type="button" onClick={onSignUp}>ثبت‌نام کنید</button>
      </p>
    </form>
  );
}

export function LoginFooter() {
  return (
    <footer className="login-footer">
      <div className="login-footer-meta">
        <span>
          <ShieldCheck />
          تضمین امنیت اطلاعات
        </span>
        <span>
          <Headphones />
          پشتیبانی ۲۴/۷
        </span>
        <span>
          <Smile />
          تجربه‌ای ساده و لذت‌بخش
        </span>
      </div>
      <nav aria-label="پیوندهای پایین صفحه">
        <a href="#rules">قوانین و مقررات</a>
        <a href="#privacy">حریم خصوصی</a>
        <a href="#contact">تماس با ما</a>
      </nav>
    </footer>
  );
}

export function AuthShowcase() {
  return (
    <div className="login-showcase">
      <div className="login-copy">
        <h2>
          خرج گروهی
          <span>بدون دردسر!</span>
        </h2>
      </div>

      <BenefitList />

      <div className="login-visual-stage" aria-hidden="true">
        <div className="login-settled-badge">
          <strong>تسویه شد</strong>
          <span>
            <Check />
          </span>
        </div>
        <img
          src="/login/wallet-coins-receipt.png"
          alt=""
          className="login-wallet-asset"
          loading="eager"
          fetchPriority="high"
        />
      </div>
    </div>
  );
}

export function LoginPage({ onLogin, onSignUp }: LoginPageProps) {
  return (
    <main className="login-page" dir="rtl">
      <section className="login-main">
        <AuthShowcase />

        <div className="login-form-panel">
          <LoginForm onLogin={onLogin} onSignUp={onSignUp} />
        </div>
      </section>
      <LoginFooter />
    </main>
  );
}
