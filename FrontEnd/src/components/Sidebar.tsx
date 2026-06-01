import { Search, X, type LucideIcon } from 'lucide-react';
import { primaryNavItems, secondaryNavItems } from '../data/mockData';

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

export function LogoMark({ className = '' }: { className?: string }) {
  return (
    <div className={cn('relative h-12 w-12 shrink-0', className)}>
      <span className="absolute left-1/2 top-0 h-3.5 w-3.5 -translate-x-1/2 rounded-full bg-[#12B76A]" />
      <span className="absolute right-0 top-3.5 h-3.5 w-3.5 rounded-full bg-[#10B981]" />
      <span className="absolute left-0 top-3.5 h-3.5 w-3.5 rounded-full bg-[#10B981]" />
      <span className="absolute bottom-1.5 left-1.5 h-3.5 w-3.5 rounded-full bg-[#16A34A]" />
      <span className="absolute bottom-1.5 right-1.5 h-3.5 w-3.5 rounded-full bg-[#16A34A]" />
      <span className="absolute bottom-0 left-1/2 h-4.5 w-4.5 -translate-x-1/2 rounded-full bg-[#0EAF66]" />
    </div>
  );
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
  label,
  active,
  icon: Icon,
}: {
  label: string;
  active?: boolean;
  icon: LucideIcon;
}) {
  return (
    <button
      type="button"
      className={cn(
        'flex h-14 w-full items-center gap-3 rounded-2xl px-4 text-right transition',
        active
          ? 'bg-emerald-50 text-emerald-600'
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
}

export function Sidebar({
  className = '',
  mobile = false,
  onClose,
}: SidebarProps) {
  return (
    <aside
      className={cn(
        'flex flex-col bg-white',
        mobile ? 'h-full w-full' : 'sticky top-0',
        className,
      )}
    >
      <div className="flex h-full flex-col overflow-y-auto px-5 py-6 lg:px-6 lg:py-8">
        <div className="mb-6 flex items-center justify-between gap-3 lg:mb-10">
          <div className="flex items-center gap-3">
            <LogoMark className="h-11 w-11 lg:h-12 lg:w-12" />
            <div className="text-[28px] font-black tracking-[-0.03em] text-text lg:text-[30px]">
              همدنگ
            </div>
          </div>

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
              label={item.label}
              icon={item.icon}
              active={item.active}
            />
          ))}
        </nav>

        <div className="my-8 h-px bg-border" />

        <nav className="space-y-2">
          {secondaryNavItems.map((item) => (
            <SidebarItem
              key={item.id}
              label={item.label}
              icon={item.icon}
            />
          ))}
        </nav>

        <div className="mt-auto pt-8 text-right text-xs text-slate-400">
          Hamdong UI v0.2
        </div>
      </div>
    </aside>
  );
}