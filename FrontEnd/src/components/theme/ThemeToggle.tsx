import { Moon, Sun } from 'lucide-react';
import type { MouseEvent } from 'react';
import { useTheme } from './ThemeProvider';

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

export function ThemeToggle({ className = '' }: { className?: string }) {
  const { isDark, toggleTheme } = useTheme();
  const Icon = isDark ? Sun : Moon;
  const label = isDark ? 'تغییر به حالت روشن' : 'تغییر به حالت تاریک';

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX || rect.left + rect.width / 2;
    const y = event.clientY || rect.top + rect.height / 2;
    toggleTheme({ origin: { x, y } });
  };

  return (
    <button
      type="button"
      className={cn(
        'theme-toggle inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-border bg-white text-slate-600 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-300 hover:text-emerald-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500/40 dark:bg-slate-900 dark:text-slate-200 dark:hover:text-emerald-300',
        className,
      )}
      aria-label={label}
      title={label}
      aria-pressed={isDark}
      onClick={handleClick}
    >
      <Icon key={isDark ? 'sun' : 'moon'} className="theme-toggle-icon h-5 w-5" strokeWidth={2.2} />
    </button>
  );
}
