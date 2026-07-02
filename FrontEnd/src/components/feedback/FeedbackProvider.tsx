import {
  AlertTriangle,
  CheckCircle2,
  Info,
  Loader2,
  X,
} from 'lucide-react';
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react';

type ToastType = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  type: ToastType;
  title: string;
  description?: string;
}

interface ConfirmOptions {
  title: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  tone?: 'danger' | 'warning' | 'success';
}

interface ConfirmState extends ConfirmOptions {
  id: number;
}

interface FeedbackContextValue {
  notify: (toast: Omit<ToastItem, 'id'>) => void;
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const FeedbackContext = createContext<FeedbackContextValue | null>(null);
const TOAST_DURATION_MS = 20_000;

function getToastClasses(type: ToastType) {
  if (type === 'success') {
    return {
      wrapper: 'border-emerald-100 bg-emerald-50 text-emerald-700',
      icon: <CheckCircle2 className="h-5 w-5" />,
    };
  }

  if (type === 'error') {
    return {
      wrapper: 'border-rose-100 bg-rose-50 text-rose-600',
      icon: <AlertTriangle className="h-5 w-5" />,
    };
  }

  return {
    wrapper: 'border-sky-100 bg-sky-50 text-sky-700',
    icon: <Info className="h-5 w-5" />,
  };
}

function getConfirmButtonClass(tone?: ConfirmOptions['tone']) {
  if (tone === 'danger') {
    return 'bg-rose-600 text-white hover:bg-rose-700 shadow-[0_12px_28px_rgba(225,29,72,0.18)]';
  }

  if (tone === 'warning') {
    return 'bg-amber-500 text-white hover:bg-amber-600 shadow-[0_12px_28px_rgba(245,158,11,0.18)]';
  }

  return 'bg-gradient-to-l from-[#00915F] to-[#00A86B] text-white hover:-translate-y-0.5 shadow-[0_12px_28px_rgba(0,168,107,0.20)]';
}

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [confirmState, setConfirmState] = useState<ConfirmState | null>(null);
  const confirmResolverRef = useRef<((value: boolean) => void) | null>(null);

  const notify = useCallback((toast: Omit<ToastItem, 'id'>) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    const nextToast = { ...toast, id };

    setToasts((prev) => [nextToast, ...prev].slice(0, 4));

    window.setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id));
    }, TOAST_DURATION_MS);
  }, []);

  const confirm = useCallback((options: ConfirmOptions) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);

    setConfirmState({ ...options, id });

    return new Promise<boolean>((resolve) => {
      confirmResolverRef.current = resolve;
    });
  }, []);

  const closeConfirm = useCallback((value: boolean) => {
    confirmResolverRef.current?.(value);
    confirmResolverRef.current = null;
    setConfirmState(null);
  }, []);

  const value = useMemo(
    () => ({
      notify,
      confirm,
    }),
    [notify, confirm],
  );

  return (
    <FeedbackContext.Provider value={value}>
      {children}

      <div className="pointer-events-none fixed left-4 top-4 z-[100] flex w-[min(360px,calc(100vw-32px))] flex-col gap-3">
        {toasts.map((toast) => {
          const classes = getToastClasses(toast.type);

          return (
            <div
              key={toast.id}
              className={`pointer-events-auto flex items-start gap-3 rounded-3xl border p-4 shadow-[0_18px_60px_rgba(15,23,42,0.14)] backdrop-blur ${classes.wrapper}`}
              dir="rtl"
            >
              <div className="mt-0.5 shrink-0">{classes.icon}</div>
              <div className="min-w-0 flex-1 text-right">
                <div className="text-sm font-extrabold">{toast.title}</div>
                {toast.description ? (
                  <div className="mt-1 text-xs leading-6 opacity-80">
                    {toast.description}
                  </div>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() =>
                  setToasts((prev) => prev.filter((item) => item.id !== toast.id))
                }
                className="shrink-0 rounded-full p-1 transition hover:bg-white/60"
                aria-label="بستن پیام"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>

      {confirmState ? (
        <div className="fixed inset-0 z-[110] flex items-center justify-center bg-slate-950/40 px-4 py-6 backdrop-blur-sm">
          <div
            className="w-full max-w-[420px] rounded-[28px] border border-border bg-white p-6 text-right shadow-[0_24px_80px_rgba(15,23,42,0.24)]"
            dir="rtl"
          >
            <div className="mb-4 flex items-start gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                {confirmState.tone === 'danger' ? (
                  <AlertTriangle className="h-5 w-5 text-rose-600" />
                ) : confirmState.tone === 'warning' ? (
                  <AlertTriangle className="h-5 w-5 text-amber-600" />
                ) : (
                  <Info className="h-5 w-5" />
                )}
              </div>
              <div className="min-w-0">
                <h2 className="text-xl font-extrabold text-text">
                  {confirmState.title}
                </h2>
                {confirmState.description ? (
                  <p className="mt-2 text-sm leading-7 text-muted">
                    {confirmState.description}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => closeConfirm(false)}
                className="h-11 rounded-2xl border border-border bg-white px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
              >
                {confirmState.cancelText || 'انصراف'}
              </button>
              <button
                type="button"
                onClick={() => closeConfirm(true)}
                className={`h-11 rounded-2xl px-4 text-sm font-bold transition ${getConfirmButtonClass(
                  confirmState.tone,
                )}`}
              >
                {confirmState.confirmText || 'تأیید'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </FeedbackContext.Provider>
  );
}

export function useFeedback() {
  const context = useContext(FeedbackContext);

  if (!context) {
    return {
      notify: () => undefined,
      confirm: async () => false,
    } satisfies FeedbackContextValue;
  }

  return context;
}

export function InlineLoader({ label = 'در حال پردازش...' }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </span>
  );
}
