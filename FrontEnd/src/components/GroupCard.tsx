import { useState } from 'react';
import {
  Archive,
  ArrowLeft,
  ChevronLeft,
  Eye,
  MoreVertical,
  Trash2,
  Users,
  X,
} from 'lucide-react';
import { MoneyWithWords } from '../lib/money';
import type { Group } from '../types';

function GroupIllustration({ type }: { type: Group['illustration'] }) {
  if (type === 'trip') {
    return (
      <div className="relative h-[74px] w-[74px] shrink-0 overflow-hidden rounded-[26px] border border-sky-100 bg-sky-50 shadow-[inset_0_0_18px_rgba(14,165,233,0.12)]">
        <div className="absolute inset-x-0 top-0 h-[58%] bg-gradient-to-b from-sky-100 via-sky-50 to-white" />
        <div className="absolute inset-x-0 bottom-0 h-[34%] bg-gradient-to-r from-[#F4D9A5] via-[#F2CF8F] to-[#F7DFC0]" />
        <div className="absolute bottom-2 left-3 text-[23px]">🌴</div>
        <div className="absolute bottom-3 right-2 text-[23px]">🚐</div>
        <div className="absolute right-2 top-2 text-[16px]">☁️</div>
      </div>
    );
  }

  if (type === 'home') {
    return (
      <div className="relative h-[74px] w-[74px] shrink-0 overflow-hidden rounded-[26px] border border-orange-100 bg-orange-50 shadow-[inset_0_0_18px_rgba(249,115,22,0.10)]">
        <div className="absolute inset-x-0 bottom-0 h-[28%] bg-gradient-to-r from-lime-300 to-emerald-400" />
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 text-[29px]">🏢</div>
        <div className="absolute right-2 top-2 text-[16px]">☀️</div>
      </div>
    );
  }

  return (
    <div className="relative h-[74px] w-[74px] shrink-0 overflow-hidden rounded-[26px] border border-amber-100 bg-amber-50 shadow-[inset_0_0_18px_rgba(245,158,11,0.10)]">
      <div className="absolute inset-x-0 bottom-0 h-[24%] bg-[#E7C7A4]" />
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-[45%] text-[31px]">☕</div>
      <div className="absolute right-4 top-4 text-[14px]">✨</div>
    </div>
  );
}

function getRoleLabel(role?: string) {
  const normalizedRole = String(role || '').toUpperCase();

  if (normalizedRole === 'OWNER') return 'مالک گروه';
  if (normalizedRole === 'ADMIN') return 'مدیر گروه';
  if (normalizedRole === 'MEMBER') return 'عضو گروه';

  return 'عضو گروه';
}

function AmountText({ amount, tone }: { amount: string; tone: Group['tone'] }) {
  const isPositive = tone === 'positive';

  return (
    <div className="rounded-[20px] border border-slate-100 bg-slate-50/70 px-4 py-3 text-right">
      <div className="text-[11px] font-extrabold text-slate-500">
        {isPositive ? 'وضعیت حساب' : 'نیاز به تسویه'}
      </div>
      <MoneyWithWords
        amount={amount}
        className="mt-1"
        valueClassName={[
          'text-[19px] font-extrabold tracking-[-0.02em]',
          isPositive ? 'text-emerald-600' : 'text-rose-500',
        ].join(' ')}
        textClassName="mt-1 text-[11px] font-semibold leading-5 text-slate-500"
      />
    </div>
  );
}

interface GroupCardProps {
  group: Group;
  onOpen?: (group: Group) => void;
  onDelete?: (group: Group) => void;
}

export function GroupCard({ group, onOpen, onDelete }: GroupCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const archived = group.status === 'ARCHIVED';

  const handleOpen = () => {
    setMenuOpen(false);
    onOpen?.(group);
  };

  const handleDelete = () => {
    setMenuOpen(false);
    onDelete?.(group);
  };

  return (
    <article
      className={[
        'group relative flex min-h-[260px] flex-col overflow-visible rounded-[30px] border-2 bg-white p-4 text-right shadow-[0_18px_46px_rgba(15,23,42,0.075)] transition duration-200 hover:-translate-y-1 hover:shadow-[0_24px_60px_rgba(15,23,42,0.11)] sm:p-5',
        archived
          ? 'border-amber-200 bg-amber-50/45 hover:border-amber-300'
          : 'border-slate-200 hover:border-emerald-200',
      ].join(' ')}
      dir="rtl"
      role="button"
      tabIndex={0}
      onClick={handleOpen}
      onKeyDown={(event) => {
        if (event.key === 'Enter') {
          handleOpen();
        }
      }}
    >
      <div className="absolute left-4 top-4 z-20">
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            setMenuOpen((prev) => !prev);
          }}
          className="flex h-10 w-10 items-center justify-center rounded-[16px] border border-slate-100 bg-white text-slate-500 shadow-sm transition hover:border-slate-200 hover:bg-slate-50 hover:text-slate-800"
          aria-label="گزینه‌های گروه"
        >
          {menuOpen ? <X className="h-5 w-5" /> : <MoreVertical className="h-5 w-5" />}
        </button>

        {menuOpen ? (
          <div
            onClick={(event) => event.stopPropagation()}
            className="absolute left-0 top-12 z-30 w-[220px] overflow-hidden rounded-[24px] border border-slate-100 bg-white p-2 text-right shadow-[0_18px_55px_rgba(15,23,42,0.16)]"
          >
            <button
              type="button"
              onClick={handleOpen}
              className="flex h-11 w-full items-center justify-between rounded-[18px] px-3 text-sm font-extrabold text-slate-700 transition hover:bg-slate-50"
            >
              مشاهده جزئیات
              <Eye className="h-4 w-4" />
            </button>

            {!archived ? (
              <button
                type="button"
                onClick={handleDelete}
                className="mt-1 flex h-11 w-full items-center justify-between rounded-[18px] px-3 text-sm font-extrabold text-rose-600 transition hover:bg-rose-50"
              >
                حذف از لیست
                <Trash2 className="h-4 w-4" />
              </button>
            ) : (
              <div className="mt-1 flex h-11 w-full items-center justify-between rounded-[18px] bg-amber-50 px-3 text-sm font-extrabold text-amber-700">
                در آرشیو است
                <Archive className="h-4 w-4" />
              </div>
            )}
          </div>
        ) : null}
      </div>

      <div className="mb-5 flex items-start justify-between gap-4 pl-12">
        <div className="min-w-0 flex-1 text-right">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span
              className={[
                'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-extrabold',
                archived
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-emerald-50 text-emerald-700',
              ].join(' ')}
            >
              {archived ? <Archive className="h-3.5 w-3.5" /> : null}
              {archived ? 'آرشیو شده' : 'فعال'}
            </span>

            <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-extrabold text-slate-600">
              {getRoleLabel(group.role)}
            </span>
          </div>

          <h3 className="line-clamp-1 text-[20px] font-extrabold leading-8 text-text">
            {group.name}
          </h3>

          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs font-bold text-muted">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-50 px-2.5 py-1">
              <Users className="h-3.5 w-3.5" />
              {group.membersLabel}
            </span>
          </div>
        </div>

        <GroupIllustration type={group.illustration} />
      </div>

      {group.description ? (
        <p className="mb-4 line-clamp-2 rounded-[18px] bg-slate-50/75 px-3 py-2 text-xs font-semibold leading-6 text-slate-500">
          {group.description}
        </p>
      ) : null}

      <div className="mt-auto space-y-4">
        <AmountText amount={group.amount} tone={group.tone} />

        <div className="flex items-center justify-between gap-3">
          <span className="min-w-0 truncate text-xs font-bold text-muted">
            {group.statusLabel || 'برای دیدن هزینه‌ها وارد گروه شو'}
          </span>

          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              handleOpen();
            }}
            className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-[17px] bg-emerald-600 px-4 text-sm font-extrabold text-white shadow-[0_12px_26px_rgba(16,185,129,0.22)] transition hover:bg-emerald-700"
          >
            ورود به گروه
            <ArrowLeft className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="pointer-events-none absolute bottom-5 left-5 hidden h-8 w-8 items-center justify-center rounded-full bg-slate-50 text-slate-400 transition group-hover:bg-emerald-50 group-hover:text-emerald-600 sm:flex">
        <ChevronLeft className="h-4 w-4" />
      </div>
    </article>
  );
}