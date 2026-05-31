import { CloudUpload, PlusCircle, UserPlus, UserRound, Users } from 'lucide-react';
import { Button } from './ui/Button';
import { Card } from './ui/Card';

interface CreateGroupFormProps {
  onStartWizard?: () => void;
}

export function CreateGroupForm({ onStartWizard }: CreateGroupFormProps) {
  return (
    <Card variant="tint" className="p-6 md:p-8">
      <div className="mb-8 flex items-center justify-start gap-3">
        <h2 className="text-[24px] font-bold leading-tight text-text">تشکیل گروه جدید</h2>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
          <Users className="h-5 w-5" strokeWidth={1.8} />
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_296px]">
        <div className="min-w-0 space-y-6 text-right">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              نام گروه <span className="text-rose-500">*</span>
            </label>
            <input type="text" className="form-input" placeholder="مثال: سفر شمال" />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">تصویر گروه</label>

            <button
              type="button"
              className="flex h-[120px] w-full flex-col items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-white text-center transition hover:border-emerald-300 hover:bg-emerald-50/30"
            >
              <CloudUpload className="mb-2 h-8 w-8 text-emerald-600" strokeWidth={1.8} />
              <span className="text-base font-medium text-slate-700">برای آپلود کلیک کنید</span>
              <span className="mt-1 text-[13px] text-slate-400">حداکثر ۲ مگابایت، JPG, PNG</span>
            </button>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              توضیحات (اختیاری)
            </label>
            <input
              type="text"
              className="form-input"
              placeholder="مثال: هزینه‌های مربوط به سفر شمال در خرداد ۱۴۰۳"
            />
          </div>

          <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:items-center sm:justify-between">
            <Button variant="secondary" className="h-12 min-w-[160px] px-8 text-base font-semibold">
              انصراف
            </Button>

            <Button
              className="h-12 min-w-[220px] px-8 text-base font-semibold"
              onClick={onStartWizard}
            >
              ایجاد گروه
            </Button>
          </div>
        </div>

        <Card variant="default" className="p-4 sm:p-5">
          <div className="flex h-full flex-col items-center justify-center rounded-3xl border border-dashed border-border px-5 py-7 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
              <UserPlus className="h-8 w-8" strokeWidth={1.8} />
            </div>

            <h3 className="text-[22px] font-bold leading-tight text-text">افزودن اعضا</h3>
            <p className="mt-3 max-w-[220px] text-sm leading-7 text-muted">
              اعضای گروه را از شماره تلفن یا مخاطبین خود اضافه کنید.
            </p>

            <Button
              variant="secondary"
              className="mt-6 h-12 w-full text-[15px] font-semibold"
            >
              <UserRound className="h-4 w-4 text-slate-500" />
              انتخاب از مخاطبین
            </Button>

            <div className="my-5 flex w-full items-center gap-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-sm text-slate-400">یا</span>
              <div className="h-px flex-1 bg-border" />
            </div>

            <div className="relative w-full">
              <input className="form-input pr-4 pl-12" placeholder="شماره موبایل را وارد کنید" />
              <button
                type="button"
                className="absolute left-3 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-emerald-600"
              >
                <PlusCircle className="h-4 w-4" />
              </button>
            </div>
          </div>
        </Card>
      </div>
    </Card>
  );
}
