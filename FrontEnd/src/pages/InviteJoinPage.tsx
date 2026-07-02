import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, CheckCircle2, Users } from 'lucide-react';
import {
  InlineLoader,
  useFeedback,
} from '../components/feedback/FeedbackProvider';
import { isApiError } from '../lib/api';
import { humanizeMachineLabel } from '../lib/userMessages';
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
  return (
    preview?.group?.description ||
    preview?.description ||
    'برای عضویت در این گروه، دکمه عضویت را بزن.'
  );
}

function getPreviewType(preview: InvitePreview | null) {
  const type = preview?.group?.group_type || preview?.group_type;
  return type === 'EVENT' ? 'رویداد' : 'عمومی';
}

function getInviteStatusLabel(status?: string) {
  if (!status) return 'فعال';
  if (status === 'ACTIVE' || status === 'VALID') return 'فعال';
  if (status === 'EXPIRED') return 'منقضی‌شده';
  if (status === 'REVOKED') return 'لغوشده';

  return humanizeMachineLabel(status, 'فعال');
}

function getBackendErrorCode(error: unknown) {
  if (!isApiError(error)) return '';

  if (typeof error.body !== 'object' || !error.body) {
    return '';
  }

  const body = error.body as {
    code?: unknown;
    error?: {
      code?: unknown;
    };
  };

  return String(body.error?.code || body.code || '');
}

function getBackendMessage(error: unknown) {
  if (!isApiError(error)) {
    return 'اتفاق غیرمنتظره‌ای افتاد. چند لحظه بعد دوباره امتحان کن.';
  }

  const code = getBackendErrorCode(error);

  if (code === 'ALREADY_GROUP_MEMBER') {
    return 'شما در حال حاضر عضو این گروه هستید.';
  }

  if (code === 'INVITE_EXPIRED') {
    return 'این لینک دعوت منقضی شده است.';
  }

  if (
    code === 'INVITE_NOT_FOUND' ||
    code === 'INVALID_INVITE'
  ) {
    return 'این لینک دعوت معتبر نیست یا منقضی شده است.';
  }

  if (error.status === 401) {
    return 'برای ادامه دوباره وارد حساب خود شوید.';
  }

  if (error.status === 403) {
    return 'اجازه استفاده از این دعوت را ندارید.';
  }

  if (error.status >= 500) {
    return 'فعلاً ارتباط با سرویس عضویت برقرار نیست. کمی بعد دوباره امتحان کن.';
  }

  return 'عضویت در گروه انجام نشد. لینک را بررسی کن یا دوباره امتحان کن.';
}

export function InviteJoinPage({
  initialToken,
  onBack,
  onAccepted,
}: InviteJoinPageProps) {
  const { notify } = useFeedback();

  const [token, setToken] = useState(
    extractInviteToken(initialToken),
  );
  const [preview, setPreview] =
    useState<InvitePreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const normalizedToken = useMemo(
    () => extractInviteToken(token),
    [token],
  );

  async function loadPreview(nextToken = normalizedToken) {
    const cleanToken = extractInviteToken(nextToken);

    if (!cleanToken) {
      setError('این لینک دعوت معتبر نیست یا منقضی شده است.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const invitePreview = await getInvitePreview(cleanToken);

      setPreview(invitePreview);
      setToken(cleanToken);
    } catch (err) {
      console.error(err);
      setPreview(null);
      setError(getBackendMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const cleanToken = extractInviteToken(initialToken);

    if (cleanToken) {
      setToken(cleanToken);
      loadPreview(cleanToken);
    } else {
      setError('این لینک دعوت معتبر نیست یا منقضی شده است.');
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialToken]);

  async function handleAcceptInvite() {
    const cleanToken = extractInviteToken(token);

    if (!cleanToken) {
      setError('این لینک دعوت معتبر نیست یا منقضی شده است.');
      return;
    }

    try {
      setAccepting(true);

      await acceptInvite(cleanToken);

      notify({
        type: 'success',
        title: 'به گروه اضافه شدی',
        description: 'این گروه به لیست گروه‌هایت اضافه شد.',
      });

      onAccepted();
    } catch (err) {
      console.error(err);

      const alreadyMember =
        getBackendErrorCode(err) === 'ALREADY_GROUP_MEMBER';

      notify({
        type: alreadyMember ? 'info' : 'error',
        title: alreadyMember
          ? 'شما عضو این گروه هستید'
          : 'عضویت انجام نشد',
        description: alreadyMember
          ? 'امکان عضویت دوباره در این گروه وجود ندارد.'
          : getBackendMessage(err),
      });
    } finally {
      setAccepting(false);
    }
  }

  return (
    <main className="app-page">
      <div className="app-container app-container-narrow space-y-6">
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
                اطلاعات گروه را بررسی کن و در صورت تمایل عضو شو.
              </p>
            </div>

            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-3xl bg-emerald-50 text-emerald-600">
              <Users className="h-7 w-7" />
            </div>
          </div>
        </div>

        <div className="mx-auto max-w-[520px]">
          <aside className="rounded-3xl border border-emerald-100 bg-emerald-50/60 p-6 shadow-soft">
            {loading ? (
              <div className="flex min-h-[250px] items-center justify-center">
                <InlineLoader label="در حال دریافت اطلاعات گروه..." />
              </div>
            ) : (
              <>
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
                    <span className="font-bold text-text">
                      {getPreviewType(preview)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-muted">وضعیت دعوت</span>
                    <span className="font-bold text-text">
                      {getInviteStatusLabel(
                        preview?.invite_status || preview?.status,
                      )}
                    </span>
                  </div>

                  {preview?.expires_at ? (
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-muted">اعتبار تا</span>
                      <span className="truncate font-bold text-text">
                        {preview.expires_at}
                      </span>
                    </div>
                  ) : null}
                </div>

                {error ? (
                  <div className="mt-4 rounded-2xl border border-rose-100 bg-rose-50 p-4 text-sm leading-7 text-rose-600">
                    {error}
                  </div>
                ) : null}

                <div className="mt-5 grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={handleAcceptInvite}
                    disabled={accepting || !preview}
                    className="inline-flex h-12 items-center justify-center rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-5 text-sm font-bold text-white shadow-[0_12px_28px_rgba(0,168,107,0.20)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-55"
                  >
                    {accepting ? (
                      <InlineLoader label="در حال عضویت..." />
                    ) : (
                      'عضویت در گروه'
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={onBack}
                    disabled={accepting}
                    className="h-12 rounded-2xl border border-border bg-white px-5 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:opacity-55"
                  >
                    لغو
                  </button>
                </div>
              </>
            )}
          </aside>
        </div>
      </div>
    </main>
  );
}
