import { useMemo, useState } from 'react';
import {
  ArrowLeft,
  Eye,
  EyeOff,
  Hash,
  Home,
  Mail,
  UserRound,
} from 'lucide-react';
import { isApiError } from '../lib/api';
import { getFriendlyApiErrorMessage } from '../lib/userMessages';
import {
  requestSignupOtp,
  setInitialPassword,
  updateSignupProfile,
  verifySignupOtp,
} from '../lib/authApi';
import {
  AuthShowcase,
  isValidEmail,
  LoginFooter,
  normalizeEmail,
  normalizeLocalizedDigits,
  otpDigitOnlyPattern,
} from './LoginPage';
import { ThemeToggle } from '../components/theme/ThemeToggle';
import './LoginPage.css';

type SignUpPageProps = {
  onLogin: () => void;
  onSignUp: () => void;
  onLanding?: () => void;
};

type SignUpStep = 'account' | 'otp' | 'profile';

const artNamePattern = /^[\w\-\u0600-\u06FF]{3,32}$/u;

type PasswordStrengthLevel = 'empty' | 'weak' | 'medium' | 'strong';

type PasswordStrengthResult = {
  level: PasswordStrengthLevel;
  score: number;
  label: string;
  message: string;
  isStrong: boolean;
};

function getPasswordStrength(value: string): PasswordStrengthResult {
  if (!value) {
    return {
      level: 'empty',
      score: 0,
      label: 'رمز عبور الزامی است',
      message: 'حداقل ۸ کاراکتر، حروف بزرگ و کوچک انگلیسی، عدد و نماد استفاده کنید.',
      isStrong: false,
    };
  }

  const checks = {
    length: value.length >= 8,
    mixedCase: /[a-z]/.test(value) && /[A-Z]/.test(value),
    number: /\d/.test(value),
    symbol: /[^A-Za-z0-9\s]/.test(value),
    noSpace: !/\s/.test(value),
  };
  const score = Object.values(checks).filter(Boolean).length;
  const isStrong = Object.values(checks).every(Boolean);

  if (isStrong) {
    return {
      level: 'strong',
      score,
      label: 'رمز عبور قوی است',
      message: 'عالیه! این رمز عبور شرایط امنیتی لازم را دارد.',
      isStrong: true,
    };
  }

  if (score >= 3) {
    return {
      level: 'medium',
      score,
      label: 'رمز عبور متوسط است',
      message: 'برای قوی شدن، حتماً حروف بزرگ و کوچک، عدد، نماد و حداقل ۸ کاراکتر داشته باشد.',
      isStrong: false,
    };
  }

  return {
    level: 'weak',
    score,
    label: 'رمز عبور ضعیف است',
    message: 'رمز عبور را قوی‌تر کنید؛ بدون رمز قوی امکان ادامه ثبت‌نام نیست.',
    isStrong: false,
  };
}

function getSignUpErrorMessage(error: unknown) {
  if (isApiError(error)) {
    const body = error.body as {
      error?: { code?: string; details?: Record<string, unknown> };
    };
    const code = body?.error?.code;

    if (code === 'INVALID_EMAIL') return 'ایمیل را درست وارد کن.';
    if (code === 'INVALID_REQUEST' && body?.error?.details?.email) {
      return 'ایمیل را درست وارد کن.';
    }

    return getFriendlyApiErrorMessage(error, {
      defaultMessage: 'ثبت‌نام انجام نشد. اطلاعات را بررسی کن و دوباره امتحان کن.',
      invalidMessage: 'اطلاعات ثبت‌نام کامل یا درست نیست.',
      unavailableMessage: 'فعلاً ثبت‌نام در دسترس نیست. کمی بعد دوباره امتحان کن.',
      codeMap: {
        INVALID_OTP: 'کد تأیید اشتباه است.',
        OTP_EXPIRED: 'زمان این کد تمام شده است. یک کد جدید بگیر.',
        OTP_IN_COOLDOWN: 'برای دریافت کد جدید کمی صبر کن.',
        OTP_RATE_LIMITED: 'درخواست‌های زیادی فرستاده شده است. چند دقیقه صبر کن و دوباره امتحان کن.',
        OTP_MAX_ATTEMPTS_EXCEEDED: 'تعداد تلاش‌ها زیاد شده است. چند دقیقه صبر کن و دوباره امتحان کن.',
        EMAIL_ALREADY_EXISTS: 'برای این ایمیل قبلاً حساب ساخته شده است. از صفحه ورود استفاده کن.',
        USER_NOT_FOUND: 'برای این ایمیل حسابی پیدا نشد.',
        ACCOUNT_DEACTIVATED: 'این حساب غیرفعال شده است.',
        ART_NAME_ALREADY_EXISTS: 'این نام کاربری قبلاً انتخاب شده است.',
        INVALID_ART_NAME: 'نام کاربری باید بین ۳ تا ۳۲ کاراکتر و بدون فاصله باشد.',
        PASSWORD_ALREADY_SET: 'برای این ایمیل قبلاً رمز ثبت شده است. از صفحه ورود استفاده کن.',
        WEAK_PASSWORD: 'رمز عبور انتخابی خیلی ضعیف است.',
        PASSWORD_CONFIRMATION_MISMATCH: 'رمز عبور و تکرارش یکی نیستند.',
      },
    });
  }

  return 'ارتباط برقرار نشد. اینترنتت را بررسی کن و دوباره امتحان کن.';
}

function SignUpForm({ onLogin, onSignUp }: SignUpPageProps) {
  const [step, setStep] = useState<SignUpStep>('account');
  const [artName, setArtName] = useState('');
  const [email, setEmail] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [password, setPassword] = useState('');
  const [repeatPassword, setRepeatPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [repeatPasswordVisible, setRepeatPasswordVisible] = useState(false);
  const [otpRequested, setOtpRequested] = useState(false);
  const [otpVerified, setOtpVerified] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [formError, setFormError] = useState('');
  const [requestingOtp, setRequestingOtp] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completingProfile, setCompletingProfile] = useState(false);

  const PasswordIcon = passwordVisible ? Eye : EyeOff;
  const RepeatPasswordIcon = repeatPasswordVisible ? Eye : EyeOff;

  const normalizedEmail = normalizeEmail(email);
  const normalizedOtpCode = normalizeLocalizedDigits(otpCode);
  const passwordStrength = useMemo(() => getPasswordStrength(password), [password]);
  const passwordStrengthPercent = Math.min(100, Math.max(10, passwordStrength.score * 20));

  const resetFeedback = () => {
    setFormError('');
    setStatusMessage('');
  };

  function validateAccountFields() {
    if (!isValidEmail(normalizedEmail)) {
      setFormError('یک ایمیل معتبر وارد کن.');
      return false;
    }

    if (!password || !repeatPassword) {
      setFormError('رمز عبور و تکرار آن را وارد کن.');
      return false;
    }

    if (password !== repeatPassword) {
      setFormError('رمز عبور و تکرارش یکی نیستند.');
      return false;
    }

    if (!passwordStrength.isStrong) {
      setFormError('برای ادامه ثبت‌نام، رمز عبور قوی‌تری انتخاب کن.');
      return false;
    }

    return true;
  }

  function validateArtName() {
    const cleanArtName = artName.trim();

    if (!artNamePattern.test(cleanArtName)) {
      setFormError('نام کاربری باید ۳ تا ۳۲ کاراکتر باشد و فاصله نداشته باشد.');
      return null;
    }

    return cleanArtName;
  }

  function handleBackToAccountStep() {
    setStep('account');
    setOtpRequested(false);
    setOtpVerified(false);
    setOtpCode('');
    resetFeedback();
  }

  function handleBackToPreviousStep() {
    if (step === 'profile') {
      setStep('otp');
      resetFeedback();
      return;
    }

    if (step === 'otp') {
      handleBackToAccountStep();
    }
  }

  async function handleRequestOtp() {
    if (!validateAccountFields()) return;

    setRequestingOtp(true);
    resetFeedback();

    try {
      await requestSignupOtp(normalizedEmail);
      setOtpRequested(true);
      setOtpVerified(false);
      setStep('otp');
      setStatusMessage('کد تایید به ایمیلت ارسال شد.');
    } catch (error) {
      setFormError(getSignUpErrorMessage(error));
    } finally {
      setRequestingOtp(false);
    }
  }

  async function handleOtpSubmit() {
    if (!validateAccountFields()) return;

    if (!otpVerified && !/^\d{6}$/.test(normalizedOtpCode)) {
      setFormError('کد تأیید ۶ رقمی را وارد کن.');
      return;
    }

    setSubmitting(true);
    resetFeedback();

    try {
      if (!otpVerified) {
        await verifySignupOtp({
          email: normalizedEmail,
          code: normalizedOtpCode,
        });

        setOtpVerified(true);
      }

      await setInitialPassword({
        new_password: password,
        new_password_confirm: repeatPassword,
      });

      setStep('profile');
      setStatusMessage('ایمیل تایید شد. حالا نام کاربری را انتخاب کنید.');
    } catch (error) {
      setFormError(getSignUpErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleProfileSubmit() {
    const cleanArtName = validateArtName();
    if (!cleanArtName) return;

    setCompletingProfile(true);
    resetFeedback();

    try {
      await updateSignupProfile({
        art_name: cleanArtName,
        display_name: cleanArtName,
      });

      onSignUp();
    } catch (error) {
      setFormError(getSignUpErrorMessage(error));
    } finally {
      setCompletingProfile(false);
    }
  }

  return (
    <form
      className="login-card login-card-signup"
      data-step={step}
      onSubmit={(event) => {
        event.preventDefault();

        if (step === 'account') {
          void handleRequestOtp();
        } else if (step === 'otp') {
          void handleOtpSubmit();
        } else {
          void handleProfileSubmit();
        }
      }}
    >
      <div className="login-card-heading">
        <h1>
          ثبت‌نام در <span>همدنگ</span>
        </h1>
        <p>
          {step === 'account'
            ? 'ایمیل و رمز عبور را وارد کنید.'
            : step === 'otp'
              ? 'کد تایید ارسال‌شده را وارد کنید.'
              : 'یک نام کاربری یکتا برای حساب خود انتخاب کنید.'}
        </p>
      </div>

      <div className="signup-step-indicator" aria-label="مرحله ثبت‌نام">
        <span className={step === 'account' ? 'is-active' : 'is-complete'}>۱</span>
        <i
          className={step === 'otp' || step === 'profile' ? 'is-complete' : undefined}
          aria-hidden="true"
        />
        <span
          className={
            step === 'otp'
              ? 'is-active'
              : step === 'profile'
                ? 'is-complete'
                : undefined
          }
        >
          ۲
        </span>
        <i className={step === 'profile' ? 'is-complete' : undefined} aria-hidden="true" />
        <span className={step === 'profile' ? 'is-active' : undefined}>۳</span>
      </div>

      <div className="signup-slide-window">
        <div
          className={`signup-slide-track ${
            step === 'otp' ? 'is-otp' : step === 'profile' ? 'is-profile' : ''
          }`}
        >
          <div className="signup-slide" aria-hidden={step !== 'account'}>
            <label className="login-field">
              <span>ایمیل</span>
              <div className="login-input-wrap">
                <input
                  type="email"
                  name="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value);
                    setOtpRequested(false);
                    setOtpVerified(false);
                    resetFeedback();
                  }}
                  placeholder="name@example.com"
                  aria-label="ایمیل"
                  disabled={step !== 'account' || requestingOtp || submitting}
                  required={step === 'account'}
                />
                <Mail className="login-input-icon" strokeWidth={2.4} />
              </div>
            </label>

            <label className="login-field">
              <span>رمز عبور</span>
              <div className="login-input-wrap">
                <input
                  type={passwordVisible ? 'text' : 'password'}
                  name="password"
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value);
                    resetFeedback();
                  }}
                  placeholder="رمز عبور خود را وارد کنید"
                  aria-label="رمز عبور"
                  aria-describedby="signup-password-strength"
                  disabled={step !== 'account' || submitting}
                  required={step === 'account'}
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

            <div
              className={`password-strength password-strength-${passwordStrength.level}`}
              id="signup-password-strength"
              aria-live="polite"
            >
              <div className="password-strength-head">
                <span>{passwordStrength.label}</span>
                <strong>{passwordStrength.score}/5</strong>
              </div>
              <div className="password-strength-bar" aria-hidden="true">
                <i style={{ width: `${passwordStrengthPercent}%` }} />
              </div>
              <p>{passwordStrength.message}</p>
            </div>

            <label className="login-field">
              <span>تکرار رمز عبور</span>
              <div className="login-input-wrap">
                <input
                  type={repeatPasswordVisible ? 'text' : 'password'}
                  name="repeatPassword"
                  autoComplete="new-password"
                  value={repeatPassword}
                  onChange={(event) => {
                    setRepeatPassword(event.target.value);
                    resetFeedback();
                  }}
                  placeholder="رمز عبور را دوباره وارد کنید"
                  aria-label="تکرار رمز عبور"
                  aria-describedby={formError ? 'signup-form-error' : undefined}
                  disabled={step !== 'account' || submitting}
                  required={step === 'account'}
                />
                <button
                  type="button"
                  className="login-password-toggle"
                  aria-label={
                    repeatPasswordVisible
                      ? 'پنهان کردن تکرار رمز عبور'
                      : 'نمایش تکرار رمز عبور'
                  }
                  aria-pressed={repeatPasswordVisible}
                  onClick={() => setRepeatPasswordVisible((visible) => !visible)}
                >
                  <RepeatPasswordIcon className="login-input-icon login-input-icon-muted" />
                </button>
              </div>
            </label>
          </div>

          <div className="signup-slide" aria-hidden={step !== 'otp'}>
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
                    setOtpCode(event.target.value.replace(otpDigitOnlyPattern, '').slice(0, 6));
                    setOtpVerified(false);
                    resetFeedback();
                  }}
                  pattern="[0-9۰-۹٠-٩]{6}"
                  placeholder="۱۲۳۴۵۶"
                  aria-label="کد تایید"
                  disabled={step !== 'otp' || submitting}
                  required={step === 'otp'}
                />
                <Hash className="login-input-icon" strokeWidth={2.4} />
              </div>
            </label>

            <div className="auth-step-actions">
              <button
                type="button"
                className="login-secondary-action auth-step-action-button"
                disabled={requestingOtp || submitting}
                onClick={() => void handleRequestOtp()}
              >
                {requestingOtp
                  ? 'در حال ارسال...'
                  : otpRequested
                    ? 'ارسال دوباره کد'
                    : 'دریافت دوباره کد'}
              </button>

              <button
                type="button"
                className="auth-step-back-button"
                disabled={requestingOtp || submitting}
                onClick={handleBackToAccountStep}
              >
                مرحله قبلی
              </button>
            </div>
          </div>

          <div className="signup-slide" aria-hidden={step !== 'profile'}>
            <label className="login-field">
              <span>نام کاربری</span>
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
                  aria-label="نام کاربری"
                  disabled={step !== 'profile' || completingProfile}
                  required={step === 'profile'}
                />
                <UserRound className="login-input-icon" strokeWidth={2.4} />
              </div>
            </label>

            <p className="signup-profile-hint">
              این نام برای ورود با رمز عبور هم استفاده می‌شود و باید یکتا باشد.
            </p>

            <div className="auth-step-actions auth-step-actions-single">
              <button
                type="button"
                className="auth-step-back-button"
                disabled={submitting || completingProfile}
                onClick={handleBackToPreviousStep}
              >
                مرحله قبلی
              </button>
            </div>
          </div>
        </div>
      </div>

      {formError ? (
        <p
          className="login-form-message login-form-message-error"
          id="signup-form-error"
          role="alert"
        >
          {formError}
        </p>
      ) : null}

      {statusMessage ? (
        <p className="login-form-message login-form-message-success">
          <span>{statusMessage}</span>
        </p>
      ) : null}

      <button
        className="login-submit"
        type="submit"
        disabled={
          requestingOtp ||
          submitting ||
          completingProfile ||
          (step === 'account' && Boolean(password) && !passwordStrength.isStrong)
        }
      >
        <ArrowLeft />
        <span>
          {step === 'account'
            ? requestingOtp
              ? 'در حال ارسال...'
              : password && !passwordStrength.isStrong
                ? 'رمز قوی لازم است'
                : 'دریافت کد تایید'
            : step === 'otp'
              ? submitting
                ? 'در حال ثبت‌نام...'
                : 'ثبت‌نام'
              : completingProfile
                ? 'در حال تکمیل...'
                : 'تکمیل اطلاعات'}
        </span>
      </button>

      <p className="login-register">
        حساب کاربری دارید؟
        <button type="button" onClick={onLogin}>
          وارد شوید
        </button>
      </p>
    </form>
  );
}

export function SignUpPage({ onLogin, onSignUp, onLanding }: SignUpPageProps) {
  return (
    <main className="login-page" dir="rtl">
      <div className="auth-page-actions">
        <button type="button" className="auth-landing-link" onClick={onLanding}>
          <Home aria-hidden="true" />
          <span>لندینگ</span>
        </button>
        <ThemeToggle className="h-11 w-11 rounded-full sm:h-12 sm:w-12" />
      </div>

      <section className="login-main">
        <AuthShowcase />

        <div className="login-form-panel">
          <SignUpForm onLogin={onLogin} onSignUp={onSignUp} />
        </div>
      </section>

      <LoginFooter />
    </main>
  );
}