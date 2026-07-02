import { X } from 'lucide-react';
import {
  useEffect,
  useId,
  useRef,
  type ReactNode,
  type RefObject,
} from 'react';

type ModalSize = 'sm' | 'md' | 'lg' | 'xl';

interface ModalProps {
  open: boolean;
  title: string;
  description?: string;
  icon?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
  size?: ModalSize;
  closeLabel?: string;
  initialFocusRef?: RefObject<HTMLElement>;
  closeOnOverlayClick?: boolean;
}

const sizeClasses: Record<ModalSize, string> = {
  sm: 'max-w-[440px]',
  md: 'max-w-[620px]',
  lg: 'max-w-[900px]',
  xl: 'max-w-[1080px]',
};

const focusableSelector = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

export function Modal({
  open,
  title,
  description,
  icon,
  children,
  footer,
  onClose,
  size = 'md',
  closeLabel = 'بستن پنجره',
  initialFocusRef,
  closeOnOverlayClick = true,
}: ModalProps) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const focusFrame = window.requestAnimationFrame(() => {
      initialFocusRef?.current?.focus?.();
      if (!initialFocusRef?.current) closeButtonRef.current?.focus();
    });

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== 'Tab' || !dialogRef.current) return;

      const focusableElements = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(focusableSelector),
      ).filter((element) => element.offsetParent !== null || element === document.activeElement);

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (!firstElement || !lastElement) return;

      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      window.cancelAnimationFrame(focusFrame);
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, [initialFocusRef, onClose, open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 px-3 py-3 backdrop-blur-sm sm:items-center dark:bg-black/55"
      dir="rtl"
      role="presentation"
      onMouseDown={(event) => {
        if (closeOnOverlayClick && event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        className={`modal-surface max-h-[92dvh] w-full overflow-hidden text-right ${sizeClasses[size]}`.trim()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-emerald-100/70 bg-white/[0.55] px-4 py-4 sm:px-5 dark:border-emerald-500/15 dark:bg-slate-900/70">
          <div className="flex min-w-0 items-start gap-3 text-right">
            {icon ? (
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[18px] bg-emerald-50 text-emerald-600 shadow-[inset_3px_0_0_#10B981] dark:bg-emerald-500/10 dark:text-emerald-300 dark:shadow-[inset_3px_0_0_#34D399]">
                {icon}
              </span>
            ) : null}

            <div className="min-w-0 text-right">
              <h2 id={titleId} className="text-lg font-black tracking-[-0.03em] text-text sm:text-xl dark:text-slate-100">
                {title}
              </h2>
              {description ? (
                <p id={descriptionId} className="mt-1 text-sm font-bold leading-6 text-muted dark:text-slate-400">
                  {description}
                </p>
              ) : null}
            </div>
          </div>

          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[18px] bg-slate-50 text-slate-500 transition hover:bg-rose-50 hover:text-rose-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-rose-500/10 dark:hover:text-rose-200"
            aria-label={closeLabel}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="max-h-[calc(92dvh-92px)] overflow-y-auto px-4 py-4 text-right sm:px-5">
          {children}
        </div>

        {footer ? (
          <div className="sticky bottom-0 border-t border-slate-100 bg-white/95 px-4 py-3 backdrop-blur sm:px-5 dark:border-slate-800 dark:bg-slate-950/95">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}
