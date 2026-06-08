import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, CheckCircle2, Link2, Users } from 'lucide-react';
import { InlineLoader, useFeedback } from '../components/feedback/FeedbackProvider';
import { isApiError } from '../lib/api';
import {
  acceptInvite,
  extractInviteToken,
  getInvitePreview,
  type InvitePreview,
} from '../lib/groupApi';

interface InviteJoinPageProps {
  initialToken: string;
  onBack: () => void;
  onAccepted: () => void;
}

function getPreviewTitle(preview: InvitePreview | null) {
  return preview?.group?.title || preview?.title || 'دعوت به گروه';
}

function getPreviewDescription(preview: InvitePreview | null) {
  return preview?.group?.description || preview?.description || 'برای مشاهده جزئیات و عضویت در گروه، دعوت را بررسی کن.';
}

function getPreviewType(preview: InvitePreview | null) {
  const type = preview?.group?.group_type || preview?.group_type;
  return type === 'EVENT' ? 'رویداد' : 'عمومی';
}

function getBackendMessage(error: unknown) {
  if (isApiError(error)) {
    if (typeof error.body === 'object' && error.body && 'detail' in error.body) {
      return String((error.body as { detail?: unknown }).detail);
    }

    if (error.bodyText) return error.bodyText;
  }

  return '';
}

export function InviteJoinPage({
  initialToken,
  onBack,
  onAccepted,
}: InviteJoinPageProps) {
  const { notify } = useFeedback();
  const [inviteInput, setInviteInput] = useState(initialToken);
  const [token, setToken] = useState(extractInviteToken(initialToken));
  const [preview, setPreview] = useState<InvitePreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const normalizedToken = useMemo(() => extractInviteToken(token), [token]);

  async function loadPreview(nextToken = normalizedToken) {
    const cleanToken = extractInviteToken(nextToken);

    if (!cleanToken) {
      setError('لینک یا توکن دعوت را وارد کن.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const invitePreview = await getInvitePreview(cleanToken);
      setPreview(invitePreview);
      setToken(cleanToken);
      setInviteInput(cleanToken);
    } catch (err) {
      console.error(err);
      setPreview(null);
      setError(getBackendMessage(err) || 'دعوت پیدا نشد یا منقضی شده است.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const cleanToken = extractInviteToken(initialToken);

    if (cleanToken) {
      setToken(cleanToken);
      setInviteInput(cleanToken);
      loadPreview(cleanToken);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialToken]);

  async function handleCheckInvite() {
    const cleanToken = extractInviteToken(inviteInput);
    await loadPreview(cleanToken);
  }

  async function handleAcceptInvite() {
    const cleanToken = extractInviteToken(token || inviteInput);

    if (!cleanToken) {
      setError('اول لینک دعوت را وارد یا بررسی کن.');
      return;
    }

    try {
      setAccepting(true);
      await acceptInvite(cleanToken);
      notify({
        type: 'success',
        title: 'عضویت انجام شد',
        description: 'گروه به لیست گروه‌های تو اضافه شد.',
      });
      onAccepted();
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'عضویت ناموفق بود',
        description: getBackendMessage(err) || 'ممکن است دعوت منقضی شده باشد یا قبلاً عضو گروه باشی.',
      });
    } finally {
      setAccepting(false);
    }
  }

  return (
    <main className="px-4 py-6 sm:px-6 xl:px-8">
      <div className="mx-auto max-w-[860px] space-y-6">
        <div className="rounded-3xl border border-border bg-white p-6 text-right shadow-soft">
          <button
            type="button"
            onClick={onBack}
            className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-slate-600 transition hover:text-text"
          >
            <ArrowLeft className="h-4.5 w-4.5" />
            بازگشت به گروه‌ها
          </button>

          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-[30px] font-extrabold tracking-[-0.03em] text-text">
                پیوستن به گروه
              </h1>
              <p className="mt-2 text-sm leading-7 text-muted">
                لینک دعوت را وارد کن؛ بعد از بررسی می‌توانی به گروه بپیوندی.
              </p>
            </div>
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-3xl bg-emerald-50 text-emerald-600">
              <Users className="h-7 w-7" />
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <section className="rounded-3xl border border-border bg-white p-6 shadow-soft">
            <label className="mb-2 block text-sm font-semibold text-text">
              لینک یا توکن دعوت
            </label>
            <div className="relative">
              <Link2 className="pointer-events-none absolute right-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" />
              <input
                dir="ltr"
                value={inviteInput}
                onChange={(event) => setInviteInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') handleCheckInvite();
                }}
                placeholder="https://localhost:5173/invites/..."
                className="h-12 w-full rounded-2xl border border-border bg-white pr-11 pl-4 text-left text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
              />
            </div>

            <button
              type="button"
              onClick={handleCheckInvite}
              disabled={loading || !extractInviteToken(inviteInput)}
              className="mt-4 inline-flex h-12 w-full items-center justify-center gap-2 rounded-2xl border border-emerald-100 bg-emerald-50 px-5 text-sm font-bold text-emerald-700 transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-55"
            >
              {loading ? <InlineLoader label="در حال بررسی..." /> : 'بررسی دعوت'}
            </button>

            {error ? (
              <div className="mt-4 rounded-2xl border border-rose-100 bg-rose-50 p-4 text-sm leading-7 text-rose-600">
                {error}
              </div>
            ) : null}
          </section>

          <aside className="rounded-3xl border border-emerald-100 bg-emerald-50/60 p-6 shadow-soft">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm">
              <CheckCircle2 className="h-5 w-5" />
            </div>

            <h2 className="text-2xl font-extrabold text-text">
              {getPreviewTitle(preview)}
            </h2>
            <p className="mt-2 text-sm leading-7 text-muted">
              {getPreviewDescription(preview)}
            </p>

            <div className="mt-5 space-y-3 rounded-2xl bg-white/70 p-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted">نوع گروه</span>
                <span className="font-bold text-text">{getPreviewType(preview)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted">وضعیت دعوت</span>
                <span className="font-bold text-text">
                  {preview ? preview.invite_status || preview.status || 'قابل استفاده' : 'بررسی نشده'}
                </span>
              </div>
              {preview?.expires_at ? (
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted">اعتبار تا</span>
                  <span className="truncate font-bold text-text">{preview.expires_at}</span>
                </div>
              ) : null}
            </div>

            <button
              type="button"
              onClick={handleAcceptInvite}
              disabled={accepting || !preview}
              className="mt-5 inline-flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-5 text-sm font-bold text-white shadow-[0_12px_28px_rgba(0,168,107,0.20)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-55"
            >
              {accepting ? <InlineLoader label="در حال عضویت..." /> : 'عضویت در گروه'}
            </button>
          </aside>
        </div>
      </div>
    </main>
  );
}
