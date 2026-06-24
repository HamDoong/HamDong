import { useState } from 'react';
import {
  ArrowLeft,
  Eye,
  EyeOff,
  Hash,
  Mail,
  UserRound,
} from 'lucide-react';
import { isApiError } from '../lib/api';
import { getFriendlyApiErrorMessage } from '../lib/userMessages';
import {
  requestLoginOtp,
  setInitialPassword,
  updateSignupProfile,
  verifyLoginOtp,
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
};

type SignUpStep = 'account' | 'otp' | 'profile';

const artNamePattern = /^[\w\-\u0600-\u06FF]{3,32}$/u;

function getSignUpErrorMessage(error: unknown) {
  if (isApiError(error)) {
    const body = error.body as {
      error?: { code?: string; details?: Record<string, unknown> };
    };
    const code = body?.error?.code;

    if (code === 'INVALID_EMAIL') return 'ایمیل را درست وارد کن.';
    if (code === 'INVALID_REQUEST' && body?.error?.details?.email) return 'ایمیل را درست وارد کن.';

    return getFriendlyApiErrorMessage(error, {
      defaultMessage: 'ثبت‌نام انجام نشد. دوباره تلاش کن.',
      invalidMessage: 'اطلاعات ثبت‌نام کامل یا درست نیست.',
      unavailableMessage: 'فعلاً ثبت‌نام در دسترس نیست. کمی بعد دوباره تلاش کن.',
      codeMap: {
        INVALID_OTP: 'کد تایید اشتباه است.',
        OTP_EXPIRED: 'زمان این کد تمام شده است. یک کد جدید بگیر.',
        OTP_IN_COOLDOWN: 'برای دریافت کد جدید کمی صبر کن.',
        OTP_RATE_LIMITED: 'درخواست‌ها زیاد شده است. کمی بعد دوباره تلاش کن.',
        ART_NAME_ALREADY_EXISTS: 'این نام کاربری قبلاً انتخاب شده است.',
        INVALID_ART_NAME: 'نام کاربری باید بین ۳ تا ۳۲ کاراکتر و بدون فاصله باشد.',
        PASSWORD_ALREADY_SET: 'برای این ایمیل قبلاً حساب ساخته شده است. از صفحه ورود استفاده کن.',
        WEAK_PASSWORD: 'رمز عبور انتخابی خیلی ضعیف است.',
        PASSWORD_CONFIRMATION_MISMATCH: 'رمز عبور و تکرار آن یکسان نیستند.',
      },
    });
  }

  return 'ارتباط با سرور برقرار نشد. دوباره تلاش کن.';
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

  const resetFeedback = () => {
    setFormError('');
    setStatusMessage('');
  };

  function validateAccountFields() {
    if (!isValidEmail(normalizedEmail)) {
      setFormError('ایمیل معتبر وارد کنید.');
      return false;
    }

    if (!password || !repeatPassword) {
      setFormError('رمز عبور و تکرار آن را وارد کنید.');
      return false;
    }

    if (password !== repeatPassword) {
      setFormError('رمز عبور و تکرار آن یکسان نیستند.');
      return false;
    }

    return true;
  }

  function validateArtName() {
    const cleanArtName = artName.trim();

    if (!artNamePattern.test(cleanArtName)) {
      setFormError('نام کاربری باید ۳ تا ۳۲ کاراکتر و بدون فاصله باشد.');
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

  async function handleRequestOtp() {
    if (!validateAccountFields()) return;

    setRequestingOtp(true);
    resetFeedback();

    try {
      await requestLoginOtp(normalizedEmail);
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
      setFormError('کد تایید ۶ رقمی را وارد کنید.');
      return;
    }

    setSubmitting(true);
    resetFeedback();

    try {
      if (!otpVerified) {
        await verifyLoginOtp({
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
        <i className={step === 'otp' || step === 'profile' ? 'is-complete' : undefined} aria-hidden="true" />
        <span className={step === 'otp' ? 'is-active' : step === 'profile' ? 'is-complete' : undefined}>۲</span>
        <i className={step === 'profile' ? 'is-complete' : undefined} aria-hidden="true" />
        <span className={step === 'profile' ? 'is-active' : undefined}>۳</span>
      </div>

      <div className="signup-slide-window">
        <div className={`signup-slide-track ${step === 'otp' ? 'is-otp' : step === 'profile' ? 'is-profile' : ''}`}>
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
                  aria-label={repeatPasswordVisible ? 'پنهان کردن تکرار رمز عبور' : 'نمایش تکرار رمز عبور'}
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
                {requestingOtp ? 'در حال ارسال...' : otpRequested ? 'ارسال دوباره کد' : 'دریافت دوباره کد'}
              </button>

              <button
                type="button"
                className="auth-step-back-button"
                disabled={requestingOtp || submitting}
                onClick={handleBackToAccountStep}
              >
                ویرایش ایمیل
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
          </div>
        </div>
      </div>

      {formError ? (
        <p className="login-form-message login-form-message-error" id="signup-form-error" role="alert">
          {formError}
        </p>
      ) : null}

      {statusMessage ? (
        <p className="login-form-message login-form-message-success">
          {statusMessage ? <span>{statusMessage}</span> : null}
        </p>
      ) : null}

      <button
        className="login-submit"
        type="submit"
        disabled={requestingOtp || submitting || completingProfile}
      >
        <ArrowLeft />
        <span>
          {step === 'account'
            ? requestingOtp
              ? 'در حال ارسال...'
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
        <button type="button" onClick={onLogin}>وارد شوید</button>
      </p>
    </form>
  );
}

export function SignUpPage({ onLogin, onSignUp }: SignUpPageProps) {
  return (
    <main className="login-page" dir="rtl">
      <div className="auth-page-theme-toggle">
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
