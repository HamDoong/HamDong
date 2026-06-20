import { Search, X, type LucideIcon } from 'lucide-react';
import { BrandLogo } from './BrandLogo';
import { primaryNavItems, secondaryNavItems } from '../data/mockData';

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function SidebarSearch() {
  return (
    <div className="relative">
      <Search className="pointer-events-none absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
      <input
        type="text"
        placeholder="جستجو در گروه‌ها، افراد، افراد..."
        className="h-12 w-full rounded-[18px] border border-border bg-white pr-12 pl-4 text-right text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
      />
    </div>
  );
}

function SidebarItem({
  id,
  label,
  active,
  icon: Icon,
  onNavigate,
}: {
  id: string;
  label: string;
  active?: boolean;
  icon: LucideIcon;
  onNavigate?: (itemId: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onNavigate?.(id)}
      className={cn(
        'flex h-14 w-full items-center gap-3 rounded-2xl px-4 text-right transition',
        active
          ? 'bg-emerald-50 text-emerald-600 shadow-[inset_3px_0_0_#10B981]'
          : 'text-slate-700 hover:bg-slate-50 hover:text-slate-900',
      )}
    >
      <Icon
        className={active ? 'h-5 w-5 text-emerald-600' : 'h-5 w-5 text-slate-500'}
        strokeWidth={1.9}
      />
      <span className="text-base font-medium">{label}</span>
    </button>
  );
}

interface SidebarProps {
  className?: string;
  mobile?: boolean;
  onClose?: () => void;
  activePage?: string;
  onNavigate?: (itemId: string) => void;
}

function isItemActive(itemId: string, activePage?: string) {
  if (itemId === 'activity') {
    return activePage === 'activities';
  }

  return itemId === activePage;
}

export function Sidebar({
  className = '',
  mobile = false,
  onClose,
  activePage = 'groups',
  onNavigate,
}: SidebarProps) {
  const handleNavigate = (itemId: string) => {
    onNavigate?.(itemId);

    if (mobile) {
      onClose?.();
    }
  };

  return (
    <aside
      className={cn(
        'flex flex-col bg-white',
        mobile ? 'h-full w-full' : 'h-screen',
        className,
      )}
    >
      <div className={cn('flex h-full flex-col px-5 py-6 lg:px-6 lg:py-7', mobile ? 'overflow-y-auto' : 'overflow-hidden')}>
        <div className="mb-6 flex items-center justify-between gap-3 lg:mb-8">
          <BrandLogo
            markClassName="h-10 w-10 lg:h-11 lg:w-11"
            textClassName="text-[26px] tracking-normal lg:text-[28px]"
          />

          {mobile ? (
            <button
              type="button"
              onClick={onClose}
              aria-label="بستن منو"
              className="flex h-11 w-11 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
            >
              <X className="h-5 w-5" strokeWidth={2} />
            </button>
          ) : null}
        </div>

        {mobile ? (
          <div className="mb-6">
            <SidebarSearch />
          </div>
        ) : null}

        <nav className="space-y-2">
          {primaryNavItems.map((item) => (
            <SidebarItem
              key={item.id}
              id={item.id}
              label={item.label}
              icon={item.icon}
              active={isItemActive(item.id, activePage)}
              onNavigate={handleNavigate}
            />
          ))}
        </nav>

        <div className="my-5 h-px bg-border" />

        <nav className="space-y-2">
          {secondaryNavItems.map((item) => (
            <SidebarItem
              key={item.id}
              id={item.id}
              label={item.label}
              icon={item.icon}
              onNavigate={handleNavigate}
            />
          ))}
        </nav>

        <div className="mt-auto" />
      </div>
    </aside>
  );
}
