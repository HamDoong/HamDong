import type { ReactNode } from 'react';

type StateTone = 'info' | 'success' | 'warning' | 'danger' | 'neutral';

interface StateMessageProps {
  tone?: StateTone;
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

const toneClasses: Record<StateTone, string> = {
  info: 'border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-500/25 dark:bg-sky-500/10 dark:text-sky-200',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-200',
  warning: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/25 dark:bg-amber-500/10 dark:text-amber-200',
  danger: 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/25 dark:bg-rose-500/10 dark:text-rose-200',
  neutral: 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200',
};

export function StateMessage({
  tone = 'neutral',
  title,
  description,
  icon,
  action,
  className = '',
}: StateMessageProps) {
  return (
    <div className={`rounded-[20px] border px-4 py-3 text-right ${toneClasses[tone]} ${className}`.trim()} role={tone === 'danger' ? 'alert' : 'status'}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          {icon ? <span className="mt-0.5 shrink-0">{icon}</span> : null}
          <div className="min-w-0">
            <p className="text-sm font-black">{title}</p>
            {description ? <p className="mt-1 text-xs font-semibold leading-6 opacity-85">{description}</p> : null}
          </div>
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </div>
  );
}
