import type { InputHTMLAttributes } from 'react';
import {
  AlertCircle,
  CloudUpload,
  FileText,
  Home,
  Plane,
  UtensilsCrossed,
} from 'lucide-react';

export type GroupTypeValue = '' | 'travel' | 'food' | 'home' | 'other';

export interface GroupInfoValues {
  name: string;
  groupType: GroupTypeValue;
  description: string;
}

export interface GroupInfoErrors {
  name?: string;
  groupType?: string;
  form?: string;
}

interface GroupInfoStepProps {
  values: GroupInfoValues;
  errors?: GroupInfoErrors;
  onChange: <K extends keyof GroupInfoValues>(
    field: K,
    value: GroupInfoValues[K],
  ) => void;
}

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

const groupTypeOptions: Array<{
  value: Exclude<GroupTypeValue, ''>;
  label: string;
  icon: typeof Plane;
}> = [
  { value: 'travel', label: 'سفر', icon: Plane },
  { value: 'food', label: 'غذا و رستوران', icon: UtensilsCrossed },
  { value: 'home', label: 'خانه و زندگی', icon: Home },
  { value: 'other', label: 'سایر', icon: FileText },
];

function FieldLabel({ children }: { children: string }) {
  return <label className="mb-2 block text-sm font-semibold text-text">{children}</label>;
}

function FieldError({ message }: { message: string }) {
  return (
    <div className="mt-2 flex items-start gap-2 text-right text-sm font-medium text-rose-600 dark:text-rose-300">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={1.8} />
      <span>{message}</span>
    </div>
  );
}

function SoftInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        'h-12 w-full rounded-[16px] border border-border bg-white px-4 text-sm text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 dark:bg-slate-900/80 dark:text-slate-100 dark:placeholder:text-slate-500',
        props.className,
      )}
    />
  );
}

export function GroupInfoStep({
  values,
  errors,
  onChange,
}: GroupInfoStepProps) {
  return (
    <div className="create-group-info-step space-y-8">
      <div className="border-b border-border/80 pb-6 text-right">
        <h2 className="text-[28px] font-bold tracking-[-0.03em] text-text">
          اطلاعات گروه
        </h2>
        <p className="mt-2 text-sm text-muted">
          فقط اطلاعات پایه گروه را وارد کن. هزینه‌ها بعد از ساخت گروه ثبت می‌شوند.
        </p>
      </div>

      {errors?.form ? (
        <div className="rounded-[18px] border border-rose-200 bg-rose-50 px-4 py-3 text-right dark:border-rose-500/30 dark:bg-rose-500/10">
          <div className="flex items-start gap-2 text-sm font-medium text-rose-700 dark:text-rose-200">
            <AlertCircle className="mt-0.5 h-4.5 w-4.5 shrink-0" strokeWidth={1.8} />
            <span>{errors.form}</span>
          </div>
        </div>
      ) : null}

      <div className="w-full space-y-6">
        <div className="w-full">
          <FieldLabel>نام گروه</FieldLabel>
          <SoftInput
            dir="rtl"
            value={values.name}
            onChange={(event) => onChange('name', event.target.value)}
            placeholder="مثال: سفر شمال تابستان ۱۴۰۳"
            aria-invalid={Boolean(errors?.name)}
            className={errors?.name ? 'border-rose-300 focus:border-rose-400 focus:ring-rose-500/10 dark:border-rose-500/40' : ''}
          />
          {errors?.name ? <FieldError message={errors.name} /> : null}
        </div>

        <div className="w-full">
          <FieldLabel>نوع گروه</FieldLabel>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            {groupTypeOptions.map((option) => {
              const Icon = option.icon;
              const selected = values.groupType === option.value;

              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => onChange('groupType', option.value)}
                  aria-pressed={selected}
                  className={cn(
                    'flex h-[52px] w-full items-center justify-center gap-2 rounded-[16px] border px-4 text-sm font-medium transition-all',
                    selected
                      ? 'border-emerald-500 bg-emerald-50 text-emerald-700 shadow-[0_8px_24px_rgba(0,168,107,0.08)] dark:bg-emerald-500/15 dark:text-emerald-300'
                      : 'border-border bg-white text-slate-700 hover:border-emerald-300 hover:text-emerald-700 dark:bg-slate-900/80 dark:text-slate-200 dark:hover:text-emerald-300',
                    errors?.groupType && !selected
                      ? 'border-rose-300 dark:border-rose-500/40'
                      : '',
                  )}
                >
                  <Icon className="h-4.5 w-4.5 shrink-0" strokeWidth={1.9} />
                  <span className="whitespace-nowrap text-center leading-5">
                    {option.label}
                  </span>
                </button>
              );
            })}
          </div>
          {errors?.groupType ? <FieldError message={errors.groupType} /> : null}
        </div>

        <div className="grid w-full gap-6 xl:grid-cols-2">
          <div className="w-full">
            <div className="mb-2 flex items-center justify-between">
              <FieldLabel>توضیحات (اختیاری)</FieldLabel>
              <span className="text-xs text-slate-400 dark:text-slate-500">
                {values.description.length}/300
              </span>
            </div>

            <textarea
              dir="rtl"
              value={values.description}
              onChange={(event) =>
                onChange('description', event.target.value.slice(0, 300))
              }
              placeholder="مثال: سفر ۴ روزه به شمال، اقامت در ویلا..."
              className="min-h-[156px] w-full resize-none rounded-[18px] border border-border bg-white px-4 py-3 text-sm leading-7 text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 dark:bg-slate-900/80 dark:text-slate-100 dark:placeholder:text-slate-500"
            />
          </div>

          <div className="w-full">
            <FieldLabel>تصویر گروه</FieldLabel>
            <button
              type="button"
              className="create-group-upload-card flex min-h-[156px] w-full flex-col items-center justify-center rounded-[20px] border border-dashed border-emerald-300 bg-emerald-50/30 px-6 text-center transition hover:bg-emerald-50 dark:border-emerald-500/35 dark:bg-emerald-500/10 dark:hover:bg-emerald-500/15"
            >
              <CloudUpload className="mb-3 h-9 w-9 text-emerald-600" strokeWidth={1.8} />
              <span className="text-base font-semibold text-text">
                برای آپلود کلیک کنید
              </span>
              <span className="mt-2 text-sm text-muted">
                حداکثر ۵ مگابایت JPG, PNG
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
