import { useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  ArrowLeft,
  Bell,
  Calculator,
  Check,
  Eye,
  EyeOff,
  Hash,
  Headphones,
  ShieldCheck,
  Smartphone,
  Smile,
  UserRound,
  WalletCards,
} from 'lucide-react';
import { isApiError } from '../lib/api';
import {
  loginWithPassword,
  requestLoginOtp,
  verifyLoginOtp,
} from '../lib/authApi';
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

const localizedDigitMap: Record<string, string> = {
  '۰': '0',
  '۱': '1',
  '۲': '2',
  '۳': '3',
  '۴': '4',
  '۵': '5',
  '۶': '6',
  '۷': '7',
  '۸': '8',
  '۹': '9',
  '٠': '0',
  '١': '1',
  '٢': '2',
  '٣': '3',
  '٤': '4',
  '٥': '5',
  '٦': '6',
  '٧': '7',
  '٨': '8',
  '٩': '9',
};

type LoginMode = 'password' | 'otp';

export function normalizePhoneDigits(value: string) {
  return value.replace(/[۰-۹٠-٩]/g, (digit) => localizedDigitMap[digit] || digit);
}

function getLoginErrorMessage(error: unknown) {
  if (isApiError(error)) {
    const body = error.body as {
      error?: { code?: string; message?: string };
      detail?: string;
    };
    const code = body?.error?.code;

    if (error.status === 404) return 'مسیر ورود در API پیدا نشد. تنظیمات /api/v1 یا API Gateway را بررسی کنید.';
    if ([502, 503, 504].includes(error.status)) return 'سرویس ورود در دسترس نیست. وضعیت API Gateway و identity-service را بررسی کنید.';

    if (code === 'INVALID_CREDENTIALS') return 'نام هنری یا رمز عبور اشتباه است.';
    if (code === 'INVALID_PHONE') return 'شماره موبایل معتبر نیست.';
    if (code === 'INVALID_OTP') return 'کد تایید اشتباه است.';
    if (code === 'OTP_EXPIRED') return 'کد تایید منقضی شده است.';
    if (code === 'OTP_IN_COOLDOWN') return 'برای دریافت کد جدید کمی صبر کنید.';
    if (code === 'OTP_RATE_LIMITED') return 'تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید.';
    if (body?.error?.message) return body.error.message;
    if (body?.detail) return body.detail;
  }

  return 'ارتباط با سرور برقرار نشد. دوباره تلاش کنید.';
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
  const [mode, setMode] = useState<LoginMode>('password');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [artName, setArtName] = useState('');
  const [password, setPassword] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [otpRequested, setOtpRequested] = useState(false);
  const [otpDebugCode, setOtpDebugCode] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [requestingOtp, setRequestingOtp] = useState(false);
  const PasswordIcon = passwordVisible ? Eye : EyeOff;

  const resetFeedback = () => {
    setErrorMessage('');
    setStatusMessage('');
  };

  const normalizedPhoneNumber = normalizePhoneDigits(phoneNumber);
  const normalizedOtpCode = normalizePhoneDigits(otpCode);

  async function handlePasswordLogin() {
    const cleanArtName = artName.trim();

    if (!cleanArtName || !password) {
      setErrorMessage('نام هنری و رمز عبور را وارد کنید.');
      return;
    }

    setSubmitting(true);
    resetFeedback();

    try {
      await loginWithPassword({ art_name: cleanArtName, password });
      onLogin();
    } catch (error) {
      setErrorMessage(getLoginErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRequestOtp() {
    if (!/^09\d{9}$/.test(normalizedPhoneNumber)) {
      setErrorMessage('شماره موبایل را با فرمت 09xxxxxxxxx وارد کنید.');
      return;
    }

    setRequestingOtp(true);
    resetFeedback();

    try {
      const response = await requestLoginOtp(normalizedPhoneNumber);
      setOtpRequested(true);
      setOtpDebugCode(response.debug_otp || '');
      setStatusMessage('کد تایید برای شماره موبایل ارسال شد.');
    } catch (error) {
      setErrorMessage(getLoginErrorMessage(error));
    } finally {
      setRequestingOtp(false);
    }
  }

  async function handleOtpLogin() {
    if (!/^09\d{9}$/.test(normalizedPhoneNumber)) {
      setErrorMessage('شماره موبایل را با فرمت 09xxxxxxxxx وارد کنید.');
      return;
    }

    if (!/^\d{6}$/.test(normalizedOtpCode)) {
      setErrorMessage('کد تایید ۶ رقمی را وارد کنید.');
      return;
    }

    setSubmitting(true);
    resetFeedback();

    try {
      await verifyLoginOtp({
        phone_number: normalizedPhoneNumber,
        code: normalizedOtpCode,
      });
      onLogin();
    } catch (error) {
      setErrorMessage(getLoginErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      className="login-card"
      onSubmit={(event) => {
        event.preventDefault();
        if (mode === 'password') {
          void handlePasswordLogin();
        } else {
          void handleOtpLogin();
        }
      }}
    >
      <div className="login-card-heading">
        <h1>
          ورود به <span>همدنگ</span>
        </h1>
        <p>خوش برگشتی! لطفاً وارد حساب کاربری خود شوید.</p>
      </div>

      <div className="login-auth-tabs" role="tablist" aria-label="روش ورود">
        <button
          type="button"
          className={mode === 'password' ? 'is-active' : undefined}
          aria-pressed={mode === 'password'}
          onClick={() => {
            setMode('password');
            resetFeedback();
          }}
        >
          ورود با رمز
        </button>
        <button
          type="button"
          className={mode === 'otp' ? 'is-active' : undefined}
          aria-pressed={mode === 'otp'}
          onClick={() => {
            setMode('otp');
            resetFeedback();
          }}
        >
          کد پیامکی
        </button>
      </div>

      {mode === 'password' ? (
        <>
          <label className="login-field">
            <span>نام هنری</span>
            <div className="login-input-wrap">
              <input
                type="text"
                name="artName"
                autoComplete="username"
                value={artName}
                onChange={(event) => {
                  setArtName(event.target.value);
                  resetFeedback();
                }}
                placeholder="ali_artist"
                aria-label="نام هنری"
                disabled={submitting}
                required
              />
              <UserRound className="login-input-icon" strokeWidth={2.4} />
            </div>
          </label>

          <label className="login-field">
            <span>رمز عبور</span>
            <div className="login-input-wrap">
              <input
                type={passwordVisible ? 'text' : 'password'}
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  resetFeedback();
                }}
                placeholder="رمز عبور خود را وارد کنید"
                aria-label="رمز عبور"
                disabled={submitting}
                required
              />
              <button
                type="button"
                className="login-password-toggle"
                aria-label={passwordVisible ? 'پنهان کردن رمز عبور' : 'نمایش رمز عبور'}
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
        </>
      ) : (
        <>
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
                  setOtpRequested(false);
                  setOtpDebugCode('');
                  resetFeedback();
                }}
                pattern="[0-9۰-۹٠-٩]*"
                placeholder="۰۹۱۲۱۳۳۴۵۶۷"
                aria-label="شماره موبایل"
                disabled={submitting || requestingOtp}
                required
              />
              <Smartphone className="login-input-icon" strokeWidth={2.4} />
            </div>
          </label>

          <button
            type="button"
            className="login-secondary-action"
            disabled={requestingOtp || submitting}
            onClick={() => void handleRequestOtp()}
          >
            {requestingOtp ? 'در حال ارسال...' : otpRequested ? 'ارسال دوباره کد' : 'دریافت کد تایید'}
          </button>

          <label className="login-field login-field-compact">
            <span>کد تایید</span>
            <div className="login-input-wrap">
              <input
                type="text"
                name="otp"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={otpCode}
                onChange={(event) => {
                  setOtpCode(event.target.value.replace(phoneDigitOnlyPattern, '').slice(0, 6));
                  resetFeedback();
                }}
                pattern="[0-9۰-۹٠-٩]{6}"
                placeholder="۱۲۳۴۵۶"
                aria-label="کد تایید"
                disabled={submitting}
                required
              />
              <Hash className="login-input-icon" strokeWidth={2.4} />
            </div>
          </label>
        </>
      )}

      {errorMessage ? (
        <p className="login-form-message login-form-message-error" role="alert">
          {errorMessage}
        </p>
      ) : null}

      {statusMessage ? (
        <p className="login-form-message login-form-message-success">
          {statusMessage}
          {otpDebugCode ? <span>کد تست: {otpDebugCode}</span> : null}
        </p>
      ) : null}

      <button className="login-submit" type="submit" disabled={submitting || requestingOtp}>
        <ArrowLeft />
        <span>{submitting ? 'در حال ورود...' : mode === 'otp' ? 'تایید و ورود' : 'ورود'}</span>
      </button>

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
