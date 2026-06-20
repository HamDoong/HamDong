import { Bell, ChevronDown, Menu, Search } from 'lucide-react';
import { LogoMark } from './BrandLogo';
import { ThemeToggle } from './theme/ThemeToggle';

function HeaderAvatar({
  compact = false,
  label = 'ک',
}: {
  compact?: boolean;
  label?: string;
}) {
  return (
    <div
      className={[
        'flex items-center justify-center rounded-full bg-gradient-to-br from-amber-300 via-orange-400 to-orange-600 text-sm font-bold text-white shadow-sm',
        compact ? 'h-10 w-10' : 'h-11 w-11',
      ].join(' ')}
    >
      {label.slice(0, 1)}
    </div>
  );
}

function DesktopSearch() {
  return (
    <div className="mx-6 w-full max-w-[540px] flex-1">
      <div className="relative">
        <Search className="pointer-events-none absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          placeholder="جستجو در گروه‌ها، افراد، افراد..."
          className="h-[52px] w-full rounded-[18px] border border-border bg-white pr-12 pl-4 text-right text-[15px] text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
        />
      </div>
    </div>
  );
}

interface TopBarProps {
  onMenuClick: () => void;
  displayName?: string;
  unreadNotificationCount?: number;
  onOpenNotifications?: () => void;
}

export function TopBar({
  onMenuClick,
  displayName = 'کاربر',
  unreadNotificationCount = 0,
  onOpenNotifications,
}: TopBarProps) {
  return (
    <header className="app-topbar sticky top-0 z-20 border-b border-border/90 bg-white/95 backdrop-blur">
      <div className="flex h-[78px] items-center justify-between px-4 sm:h-[86px] sm:px-6 lg:hidden">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="باز کردن منو"
          className="flex h-11 w-11 items-center justify-center rounded-full text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
        >
          <Menu className="h-6 w-6" strokeWidth={2} />
        </button>

        <div className="flex min-w-0 flex-1 items-center justify-center gap-2 px-3">
          <LogoMark className="h-8 w-8 sm:h-9 sm:w-9" />
          <span className="truncate text-lg font-extrabold tracking-[-0.03em] text-text">
            همدنگ
          </span>
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggle className="h-10 w-10 rounded-full sm:h-10 sm:w-10" />
          <button
            type="button"
            onClick={onOpenNotifications}
            className="relative hidden h-10 w-10 items-center justify-center rounded-full text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 sm:flex"
            aria-label="اعلان‌ها"
          >
            <Bell className="h-5 w-5" strokeWidth={1.9} />
            {unreadNotificationCount > 0 ? (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-emerald-500 px-1 text-[10px] font-bold text-white ring-2 ring-white">
                {unreadNotificationCount > 9 ? '۹+' : unreadNotificationCount.toLocaleString('fa-IR')}
              </span>
            ) : null}
          </button>

          <button
            type="button"
            className="flex items-center rounded-full transition hover:bg-slate-50"
            aria-label="حساب کاربری"
          >
            <HeaderAvatar compact label={displayName} />
          </button>
        </div>
      </div>

      <div className="hidden h-[94px] items-center justify-between px-6 xl:px-8 lg:flex">
        <div className="flex min-w-[240px] items-center justify-start gap-3">
          <button
            type="button"
            className="flex items-center gap-3 rounded-full px-1 transition hover:bg-slate-50"
          >
            <HeaderAvatar label={displayName} />
            <span className="text-[17px] font-semibold text-slate-800">
              {displayName}
            </span>
            <ChevronDown className="h-4 w-4 text-slate-500" />
          </button>

          <button
            type="button"
            onClick={onOpenNotifications}
            className="relative flex h-11 w-11 items-center justify-center rounded-full text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
            aria-label="اعلان‌ها"
          >
            <Bell className="h-5 w-5" strokeWidth={1.9} />
            {unreadNotificationCount > 0 ? (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-emerald-500 px-1 text-[10px] font-bold text-white ring-2 ring-white">
                {unreadNotificationCount > 9 ? '۹+' : unreadNotificationCount.toLocaleString('fa-IR')}
              </span>
            ) : null}
          </button>

          <ThemeToggle className="h-11 w-11 rounded-full" />
        </div>

        <DesktopSearch />
        <div className="min-w-[120px]" />
      </div>
    </header>
  );
}
