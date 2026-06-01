import { Bell, ChevronDown, Menu, Search } from 'lucide-react';
import { LogoMark } from './Sidebar';

function HeaderAvatar({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={[
        'flex items-center justify-center rounded-full bg-gradient-to-br from-amber-300 via-orange-400 to-orange-600 text-sm font-bold text-white shadow-sm',
        compact ? 'h-10 w-10' : 'h-11 w-11',
      ].join(' ')}
    >
      ع
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
}

export function TopBar({ onMenuClick }: TopBarProps) {
  return (
    <header className="sticky top-0 z-20 border-b border-border/90 bg-white/95 backdrop-blur">
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
          <LogoMark className="h-8 w-8" />
          <span className="truncate text-lg font-extrabold tracking-[-0.03em] text-text">
            همدنگ
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="relative hidden h-10 w-10 items-center justify-center rounded-full text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 sm:flex"
            aria-label="اعلان‌ها"
          >
            <Bell className="h-5 w-5" strokeWidth={1.9} />
            <span className="absolute right-2.5 top-2.5 h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-white" />
          </button>

          <button
            type="button"
            className="flex items-center rounded-full transition hover:bg-slate-50"
            aria-label="حساب کاربری"
          >
            <HeaderAvatar compact />
          </button>
        </div>
      </div>

      <div className="hidden h-[94px] items-center justify-between px-6 xl:px-8 lg:flex">
        <div className="flex min-w-[240px] items-center justify-start gap-3">
          <button
            type="button"
            className="flex items-center gap-3 rounded-full px-1 transition hover:bg-slate-50"
          >
            <HeaderAvatar />
            <span className="text-[17px] font-semibold text-slate-800">علی احمدی</span>
            <ChevronDown className="h-4 w-4 text-slate-500" />
          </button>

          <button
            type="button"
            className="relative flex h-11 w-11 items-center justify-center rounded-full text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
          >
            <Bell className="h-5 w-5" strokeWidth={1.9} />
            <span className="absolute right-2.5 top-2.5 h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-white" />
          </button>
        </div>

        <DesktopSearch />
        <div className="min-w-[120px]" />
      </div>
    </header>
  );
}