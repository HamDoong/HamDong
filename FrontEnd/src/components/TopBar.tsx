import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Bell, Menu, Search } from 'lucide-react';
import { LogoMark } from './BrandLogo';
import { ThemeToggle } from './theme/ThemeToggle';

interface SearchableGroup {
  id: string;
  name: string;
}

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

function normalizeSearchValue(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[أإآ]/g, 'ا')
    .replace(/ك/g, 'ک')
    .replace(/ي/g, 'ی')
    .replace(/ة/g, 'ه')
    .replace(/\s+/g, ' ');
}

function DesktopSearch({
  groups,
  onOpenGroup,
}: {
  groups: SearchableGroup[];
  onOpenGroup?: (groupId: string) => void;
}) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement | null>(null);

  const normalizedQuery = normalizeSearchValue(query);

  const matchedGroups = useMemo(() => {
    if (!normalizedQuery) return [];

    return groups
      .filter((group) => normalizeSearchValue(group.name).includes(normalizedQuery))
      .slice(0, 8);
  }, [groups, normalizedQuery]);

  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (!searchRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, [isOpen]);

  const openSearchResults = () => {
    if (normalizedQuery) {
      setIsOpen(true);
    }
  };

  const handleSelectGroup = (groupId: string) => {
    onOpenGroup?.(groupId);
    setQuery('');
    setIsOpen(false);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (matchedGroups.length > 0) {
      handleSelectGroup(matchedGroups[0]!.id);
    } else {
      setIsOpen(true);
    }
  };

  return (
    <div className="mx-4 w-full min-w-0 max-w-[720px] flex-1 2xl:mx-8" ref={searchRef}>
      <form className="relative" onSubmit={handleSubmit}>
        <Search className="pointer-events-none absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
        <input
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setIsOpen(Boolean(normalizeSearchValue(event.target.value)));
          }}
          onFocus={openSearchResults}
          placeholder="جستجو بین نام گروه‌ها..."
          className="h-[52px] w-full rounded-[18px] border border-border bg-white pr-12 pl-4 text-right text-[15px] text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500"
        />

        {isOpen && normalizedQuery ? (
          <div className="absolute inset-x-0 top-[calc(100%+10px)] z-40 overflow-hidden rounded-[20px] border border-border/80 bg-white/95 shadow-2xl backdrop-blur dark:bg-slate-950/95">
            {matchedGroups.length > 0 ? (
              <div className="max-h-[360px] overflow-y-auto p-2">
                {matchedGroups.map((group) => (
                  <button
                    key={group.id}
                    type="button"
                    onClick={() => handleSelectGroup(group.id)}
                    className="flex w-full items-center justify-between rounded-2xl px-4 py-3 text-right transition hover:bg-emerald-50 dark:hover:bg-emerald-500/10"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-bold text-slate-800 dark:text-slate-100">
                        {group.name}
                      </div>
                      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        برای رفتن به گروه، انتخابش کن
                      </div>
                    </div>
                    <span className="mr-4 shrink-0 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
                      مشاهده
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="px-4 py-5 text-right">
                <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                  گروهی با این عبارت پیدا نشد
                </div>
                <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  نام گروه را کمی متفاوت‌تر بنویس.
                </div>
              </div>
            )}
          </div>
        ) : null}
      </form>
    </div>
  );
}

interface TopBarProps {
  onMenuClick: () => void;
  displayName?: string;
  unreadNotificationCount?: number;
  onOpenNotifications?: () => void;
  groups?: SearchableGroup[];
  onOpenGroup?: (groupId: string) => void;
}

export function TopBar({
  onMenuClick,
  displayName = 'کاربر',
  unreadNotificationCount = 0,
  onOpenNotifications,
  groups = [],
  onOpenGroup,
}: TopBarProps) {
  return (
    <header className="app-topbar sticky top-0 z-20 border-b border-border/90 bg-white/95 backdrop-blur dark:bg-slate-950/95">
      <div className="flex h-[78px] items-center justify-between px-4 sm:h-[86px] sm:px-6 lg:hidden">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="باز کردن منو"
          className="flex h-11 w-11 items-center justify-center rounded-full text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-white"
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
            className="relative hidden h-10 w-10 items-center justify-center rounded-full text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 sm:flex dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-white"
            aria-label="اعلان‌ها"
          >
            <Bell className="h-5 w-5" strokeWidth={1.9} />
            {unreadNotificationCount > 0 ? (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-emerald-500 px-1 text-[10px] font-bold text-white ring-2 ring-white dark:ring-slate-950">
                {unreadNotificationCount > 9 ? '۹+' : unreadNotificationCount.toLocaleString('fa-IR')}
              </span>
            ) : null}
          </button>

          <button
            type="button"
            className="flex items-center rounded-full transition hover:bg-slate-50 dark:hover:bg-slate-900"
            aria-label="حساب کاربری"
          >
            <HeaderAvatar compact label={displayName} />
          </button>
        </div>
      </div>

      <div className="hidden h-[94px] items-center gap-4 px-6 lg:flex xl:px-8 2xl:h-[98px] 2xl:px-10">
        <div className="flex min-w-[220px] shrink-0 items-center justify-start gap-3 2xl:min-w-[260px]">
          <button
            type="button"
            className="flex items-center gap-3 rounded-full px-1 transition hover:bg-slate-50 dark:hover:bg-slate-900"
          >
            <HeaderAvatar label={displayName} />
            <span className="max-w-[140px] truncate text-[17px] font-semibold text-slate-800 dark:text-slate-100 2xl:max-w-[180px]">
              {displayName}
            </span>
          </button>

          <button
            type="button"
            onClick={onOpenNotifications}
            className="relative flex h-11 w-11 items-center justify-center rounded-full text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-white"
            aria-label="اعلان‌ها"
          >
            <Bell className="h-5 w-5" strokeWidth={1.9} />
            {unreadNotificationCount > 0 ? (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-emerald-500 px-1 text-[10px] font-bold text-white ring-2 ring-white dark:ring-slate-950">
                {unreadNotificationCount > 9 ? '۹+' : unreadNotificationCount.toLocaleString('fa-IR')}
              </span>
            ) : null}
          </button>

          <ThemeToggle className="h-11 w-11 rounded-full" />
        </div>

        <DesktopSearch groups={groups} onOpenGroup={onOpenGroup} />
      </div>
    </header>
  );
}
