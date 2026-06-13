import { useState } from 'react';
import {
  ArrowLeft,
  Eye,
  EyeOff,
  Hash,
  Smartphone,
  UserRound,
} from 'lucide-react';
import { isApiError } from '../lib/api';
import {
  requestLoginOtp,
  setInitialPassword,
  updateSignupProfile,
  verifyLoginOtp,
} from '../lib/authApi';
import {
  AuthShowcase,
  LoginFooter,
  normalizePhoneDigits,
  phoneDigitOnlyPattern,
} from './LoginPage';
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
      error?: { code?: string; message?: string };
      detail?: string;
    };
    const code = body?.error?.code;

    if (error.status === 404) return 'مسیر ثبت‌نام در API پیدا نشد. تنظیمات /api/v1 یا API Gateway را بررسی کنید.';
    if ([502, 503, 504].includes(error.status)) return 'سرویس هویت در دسترس نیست. وضعیت API Gateway و identity-service را بررسی کنید.';

    if (code === 'INVALID_PHONE') return 'شماره موبایل معتبر نیست.';
    if (code === 'INVALID_OTP') return 'کد تایید اشتباه است.';
    if (code === 'OTP_EXPIRED') return 'کد تایید منقضی شده است.';
    if (code === 'OTP_IN_COOLDOWN') return 'برای دریافت کد جدید کمی صبر کنید.';
    if (code === 'OTP_RATE_LIMITED') return 'تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید.';
    if (code === 'ART_NAME_ALREADY_EXISTS') return 'این نام هنری قبلاً انتخاب شده است.';
    if (code === 'INVALID_ART_NAME') return 'نام هنری باید ۳ تا ۳۲ کاراکتر و بدون فاصله باشد.';
    if (code === 'PASSWORD_ALREADY_SET') return 'این شماره قبلاً حساب فعال دارد. از صفحه ورود استفاده کنید.';
    if (code === 'WEAK_PASSWORD') return 'رمز عبور به اندازه کافی قوی نیست.';
    if (code === 'PASSWORD_CONFIRMATION_MISMATCH') return 'رمز عبور و تکرار آن یکسان نیستند.';
    if (body?.error?.message) return body.error.message;
    if (body?.detail) return body.detail;
  }

  return 'ارتباط با سرور برقرار نشد. دوباره تلاش کنید.';
}

function SignUpForm({ onLogin, onSignUp }: SignUpPageProps) {
  const [step, setStep] = useState<SignUpStep>('account');
  const [artName, setArtName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [password, setPassword] = useState('');
  const [repeatPassword, setRepeatPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [repeatPasswordVisible, setRepeatPasswordVisible] = useState(false);
  const [otpRequested, setOtpRequested] = useState(false);
  const [otpVerified, setOtpVerified] = useState(false);
  const [otpDebugCode, setOtpDebugCode] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [formError, setFormError] = useState('');
  const [requestingOtp, setRequestingOtp] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completingProfile, setCompletingProfile] = useState(false);
  const PasswordIcon = passwordVisible ? Eye : EyeOff;
  const RepeatPasswordIcon = repeatPasswordVisible ? Eye : EyeOff;

  const normalizedPhoneNumber = normalizePhoneDigits(phoneNumber);
  const normalizedOtpCode = normalizePhoneDigits(otpCode);

  const resetFeedback = () => {
    setFormError('');
    setStatusMessage('');
  };

  function validateAccountFields() {
    if (!/^09\d{9}$/.test(normalizedPhoneNumber)) {
      setFormError('شماره موبایل را با فرمت 09xxxxxxxxx وارد کنید.');
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

  async function handleRequestOtp() {
    if (!validateAccountFields()) return;

    setRequestingOtp(true);
    resetFeedback();

    try {
      const response = await requestLoginOtp(normalizedPhoneNumber);
      setOtpRequested(true);
      setOtpVerified(false);
      setOtpDebugCode(response.debug_otp || '');
      setStep('otp');
      setStatusMessage('کد تایید برای شماره موبایل ارسال شد.');
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
          phone_number: normalizedPhoneNumber,
          code: normalizedOtpCode,
        });
        setOtpVerified(true);
      }

      await setInitialPassword({
        new_password: password,
        new_password_confirm: repeatPassword,
      });

      setStep('profile');
      setStatusMessage('شماره موبایل تایید شد. حالا نام کاربری را انتخاب کنید.');
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
            ? 'شماره موبایل و رمز عبور را وارد کنید.'
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
                    setOtpVerified(false);
                    setOtpDebugCode('');
                    resetFeedback();
                  }}
                  pattern="[0-9۰-۹٠-٩]*"
                  placeholder="۰۹۱۲۱۳۳۴۵۶۷"
                  aria-label="شماره موبایل"
                  disabled={step !== 'account' || requestingOtp || submitting}
                  required={step === 'account'}
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
                    setOtpCode(event.target.value.replace(phoneDigitOnlyPattern, '').slice(0, 6));
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

            <button
              type="button"
              className="login-secondary-action"
              disabled={requestingOtp || submitting}
              onClick={() => void handleRequestOtp()}
            >
              {requestingOtp ? 'در حال ارسال...' : otpRequested ? 'ارسال دوباره کد' : 'دریافت دوباره کد'}
            </button>
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

      {statusMessage || otpDebugCode ? (
        <p className="login-form-message login-form-message-success">
          {statusMessage ? <span>{statusMessage}</span> : null}
          {otpDebugCode ? <span>کد تست: {otpDebugCode}</span> : null}
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
