import { useEffect, useId, useRef, useState } from 'react';
import {
  Archive,
  ArrowLeft,
  Coffee,
  House,
  Loader2,
  MoreVertical,
  Plane,
  ReceiptText,
  Users,
  X,
} from 'lucide-react';
import { MoneyWithWords, formatMoneyNumber, normalizeMoneyAmount } from '../lib/money';
import type { Group } from '../types';

function GroupIllustration({
  type,
  mobile = false,
}: {
  type: Group['illustration'];
  mobile?: boolean;
}) {
  const Icon = type === 'trip' ? Plane : type === 'home' ? House : Coffee;

  return (
    <span
      className={[
        'group-card-artwork',
        `group-card-artwork--${type}`,
        mobile ? 'group-card-artwork--mobile' : '',
      ].join(' ')}
      aria-hidden="true"
    >
      <Icon className="h-6 w-6" strokeWidth={2.25} />
    </span>
  );
}

function MobileBalance({
  amount,
  tone,
  archived,
  loading,
}: {
  amount: string;
  tone: Group['tone'];
  archived: boolean;
  loading: boolean;
}) {
  const numericAmount = normalizeMoneyAmount(amount);
  const isBalanced = numericAmount === 0;
  const isDebt = !isBalanced && tone === 'negative';
  const label = archived ? 'آرشیو' : isBalanced ? 'تسویه' : isDebt ? 'بدهکار' : 'طلبکار';

  if (loading) {
    return (
      <span className="group-card-row-balance flex w-[76px] shrink-0 justify-end text-muted" role="status">
        <Loader2 className="h-4 w-4 animate-spin" />
      </span>
    );
  }

  return (
    <span className="group-card-row-balance w-[92px] shrink-0 text-left">
      {isBalanced ? (
        <span className="block text-xs font-extrabold text-slate-500">تسویه</span>
      ) : (
        <span
          className={[
            'whitespace-nowrap text-[11px] font-extrabold',
            isDebt ? 'text-rose-600' : 'text-emerald-600',
          ].join(' ')}
        >
          {formatMoneyNumber(numericAmount)}
        </span>
      )}
      <span
        className={[
          'mt-1 block text-[10px] font-bold',
          archived ? 'text-amber-600' : isDebt ? 'text-rose-500' : 'text-emerald-600',
        ].join(' ')}
      >
        {label}
      </span>
    </span>
  );
}

function getRoleLabel(role?: string): string | null {
  const normalizedRole = String(role || '').toUpperCase();

  if (normalizedRole === 'OWNER') return 'مالک گروه';
  if (normalizedRole === 'ADMIN') return 'مدیر گروه';

  return null;
}

function getCleanMembersLabel(label?: string) {
  return String(label || '۱ عضو')
    .replace(/\s*•\s*فعال/g, '')
    .replace(/\s*•\s*آرشیو شده/g, '')
    .trim();
}

function AmountText({
  amount,
  tone,
  archived,
  loading,
}: {
  amount: string;
  tone: Group['tone'];
  archived: boolean;
  loading: boolean;
}) {
  const numericAmount = normalizeMoneyAmount(amount);
  const isBalanced = numericAmount === 0;
  const isDebt = !isBalanced && tone === 'negative';
  const isCredit = !isBalanced && tone === 'positive';
  const label = archived
    ? 'مانده‌ی این گروه'
    : isDebt
      ? 'شما باید پرداخت کنید'
      : isCredit
        ? 'شما باید دریافت کنید'
        : 'این گروه تسویه شده';

  return (
    <div
      className={[
        'group-card-amount',
        isDebt ? 'group-card-amount--debt' : isCredit ? 'group-card-amount--credit' : 'group-card-amount--settled',
      ].join(' ')}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-extrabold">{label}</span>
        <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/75">
          <ReceiptText className="h-4 w-4" />
        </span>
      </div>

      {loading ? (
        <div
          className="mt-3 flex h-7 items-center gap-2 text-sm font-extrabold opacity-75"
          role="status"
        >
          <Loader2 className="h-4 w-4 animate-spin" />
          در حال محاسبه حساب
        </div>
      ) : (
        <MoneyWithWords
          amount={numericAmount}
          className="mt-2"
          valueClassName="text-[20px] font-extrabold tracking-[-0.02em]"
          showText={false}
        />
      )}
    </div>
  );
}

interface GroupCardProps {
  group: Group;
  balanceLoading?: boolean;
  isLastMobile?: boolean;
  onOpen?: (group: Group) => void;
  onDelete?: (group: Group) => void;
}

export function GroupCard({
  group,
  balanceLoading = false,
  isLastMobile = false,
  onOpen,
  onDelete,
}: GroupCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuId = useId();
  const mobileMenuId = useId();
  const menuRef = useRef<HTMLDivElement>(null);
  const mobileMenuRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const mobileMenuButtonRef = useRef<HTMLButtonElement>(null);
  const archived = group.status === 'ARCHIVED';
  const cleanMembersLabel = getCleanMembersLabel(group.membersLabel);
  const roleLabel = getRoleLabel(group.role);
  const canManageGroup = ['OWNER', 'ADMIN'].includes(String(group.role || '').toUpperCase());

  useEffect(() => {
    if (!menuOpen) return;

    const closeOnOutsideClick = (event: PointerEvent) => {
      const target = event.target as Node;

      if (
        !menuRef.current?.contains(target) &&
        !mobileMenuRef.current?.contains(target)
      ) {
        setMenuOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenuOpen(false);
        window.requestAnimationFrame(() => {
          const visibleButton = mobileMenuButtonRef.current?.offsetParent
            ? mobileMenuButtonRef.current
            : menuButtonRef.current;
          visibleButton?.focus();
        });
      }
    };

    document.addEventListener('pointerdown', closeOnOutsideClick);
    document.addEventListener('keydown', closeOnEscape);

    return () => {
      document.removeEventListener('pointerdown', closeOnOutsideClick);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [menuOpen]);

  const handleOpen = () => {
    setMenuOpen(false);
    onOpen?.(group);
  };

  const handleDelete = () => {
    setMenuOpen(false);
    onDelete?.(group);
  };

  return (
    <>
      <article
        className={[
          'group-card-row relative flex min-h-[82px] items-center px-3 py-2 lg:hidden',
          isLastMobile ? 'group-card-row--last' : '',
        ].join(' ')}
        dir="rtl"
      >
        <button
          type="button"
          onClick={handleOpen}
          className="group-card-row-main flex min-w-0 flex-1 items-center gap-3 rounded-2xl text-right"
          aria-label={`ورود به گروه ${group.name}`}
        >
          <GroupIllustration type={group.illustration} mobile />

          <span className="min-w-0 flex-1">
            <span className="flex min-w-0 items-center gap-2">
              <span className="truncate text-[15px] font-extrabold text-text">{group.name}</span>
              {archived ? (
                <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-extrabold text-amber-700">
                  آرشیو
                </span>
              ) : null}
            </span>
            <span className="mt-1 flex items-center gap-1.5 text-xs font-bold text-muted">
              <Users className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{cleanMembersLabel}</span>
            </span>
          </span>

          <MobileBalance
            amount={group.amount}
            tone={group.tone}
            archived={archived}
            loading={balanceLoading}
          />
        </button>

        {!archived && onDelete && canManageGroup ? (
          <div ref={mobileMenuRef} className="relative mr-1 shrink-0">
            <button
              ref={mobileMenuButtonRef}
              type="button"
              onClick={() => setMenuOpen((prev) => !prev)}
              className="group-card-row-menu-button flex h-10 w-8 items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              aria-label={`مدیریت گروه ${group.name}`}
              aria-expanded={menuOpen}
              aria-controls={menuOpen ? mobileMenuId : undefined}
            >
              {menuOpen ? <X className="h-4 w-4" /> : <MoreVertical className="h-4 w-4" />}
            </button>

            {menuOpen ? (
              <div
                id={mobileMenuId}
                aria-label="عملیات مدیریت گروه"
                className="group-card-menu absolute left-0 top-11 z-30 w-[190px] overflow-hidden rounded-2xl border p-2 text-right"
              >
                <button
                  type="button"
                  onClick={handleDelete}
                  className="flex h-11 w-full items-center justify-between rounded-xl px-3 text-sm font-extrabold text-amber-700 transition hover:bg-amber-50"
                >
                  انتقال به آرشیو
                  <Archive className="h-4 w-4" />
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </article>

    <article
      className={[
        'group-card-clean relative hidden min-h-[212px] flex-col overflow-visible rounded-3xl border p-4 text-right transition duration-200 sm:p-5 lg:flex',
        archived ? 'group-card-clean--archived' : 'group-card-clean--active',
      ].join(' ')}
      dir="rtl"
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 text-right">
          {archived || roleLabel ? (
            <div className="mb-2 flex flex-wrap items-center gap-2">
              {archived ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-extrabold text-amber-700">
                  <Archive className="h-3.5 w-3.5" />
                  آرشیو شده
                </span>
              ) : null}

              {roleLabel ? (
                <span className="group-card-role-pill inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-extrabold">
                  {roleLabel}
                </span>
              ) : null}
            </div>
          ) : null}

          <h2 className="line-clamp-1 text-[20px] font-extrabold leading-8 text-text">
            {group.name}
          </h2>

          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs font-bold text-muted">
            <span className="group-card-meta-pill inline-flex items-center gap-1.5 rounded-full px-2.5 py-1">
              <Users className="h-3.5 w-3.5" />
              {cleanMembersLabel}
            </span>
          </div>
        </div>

        <GroupIllustration type={group.illustration} />
      </div>

      <div className="mt-auto space-y-3">
        <AmountText
          amount={group.amount}
          tone={group.tone}
          archived={archived}
          loading={balanceLoading}
        />

        <div className="relative flex items-center gap-2">
          <button
            type="button"
            onClick={handleOpen}
            className="group-card-open-button inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-2xl px-4 text-sm font-extrabold transition"
            aria-label={`ورود به گروه ${group.name}`}
          >
            مشاهده گروه
            <ArrowLeft className="h-4 w-4" />
          </button>

          {!archived && onDelete && canManageGroup ? (
            <div ref={menuRef} className="relative shrink-0">
              <button
                ref={menuButtonRef}
                type="button"
                onClick={() => setMenuOpen((prev) => !prev)}
                className="group-card-menu-button flex h-11 w-11 items-center justify-center rounded-2xl border text-slate-500 transition hover:text-slate-800"
                aria-label={`مدیریت گروه ${group.name}`}
                aria-expanded={menuOpen}
                aria-controls={menuOpen ? menuId : undefined}
              >
                {menuOpen ? <X className="h-5 w-5" /> : <MoreVertical className="h-5 w-5" />}
              </button>

              {menuOpen ? (
                <div
                  id={menuId}
                  aria-label="عملیات مدیریت گروه"
                  className="group-card-menu absolute bottom-[52px] left-0 z-30 w-[210px] overflow-hidden rounded-2xl border p-2 text-right"
                >
                  <button
                    type="button"
                    onClick={handleDelete}
                    className="flex h-11 w-full items-center justify-between rounded-xl px-3 text-sm font-extrabold text-amber-700 transition hover:bg-amber-50"
                  >
                    انتقال به آرشیو
                    <Archive className="h-4 w-4" />
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </article>
    </>
  );
}
