import { useState } from 'react';
import {
  ArrowLeft,
  Eye,
  EyeOff,
  Smartphone,
} from 'lucide-react';
import {
  AuthShowcase,
  LoginFooter,
  phoneDigitOnlyPattern,
} from './LoginPage';
import './LoginPage.css';

type SignUpPageProps = {
  onLogin: () => void;
  onSignUp: () => void;
};

function SignUpForm({ onLogin, onSignUp }: SignUpPageProps) {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [repeatPassword, setRepeatPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [repeatPasswordVisible, setRepeatPasswordVisible] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const PasswordIcon = passwordVisible ? Eye : EyeOff;
  const RepeatPasswordIcon = repeatPasswordVisible ? Eye : EyeOff;

  return (
    <form
      className="login-card login-card-signup"
      onSubmit={(event) => {
        event.preventDefault();

        if (password !== repeatPassword) {
          setPasswordError('رمز عبور و تکرار آن یکسان نیستند.');
          return;
        }

        setPasswordError('');
        onSignUp();
      }}
    >
      <div className="login-card-heading">
        <h1>
          ثبت‌نام در <span>همدنگ</span>
        </h1>
        <p>برای ساخت حساب، شماره موبایل و رمز عبور خود را وارد کنید.</p>
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
            placeholder="۰۹۱۲ ۱۳۳ ۴۵ ۶۷"
            aria-label="شماره موبایل"
            required
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
              setPasswordError('');
            }}
            placeholder="رمز عبور خود را وارد کنید"
            aria-label="رمز عبور"
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
              setPasswordError('');
            }}
            placeholder="رمز عبور را دوباره وارد کنید"
            aria-label="تکرار رمز عبور"
            aria-describedby={passwordError ? 'signup-password-error' : undefined}
            required
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
        {passwordError ? (
          <small className="login-field-error" id="signup-password-error">
            {passwordError}
          </small>
        ) : null}
      </label>

      <button className="login-submit" type="submit">
        <ArrowLeft />
        <span>ثبت‌نام</span>
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
