import { CloudUpload, PlusCircle, UserPlus, UserRound, Users } from 'lucide-react';
import { Button } from './ui/Button';
import { Card } from './ui/Card';

export function CreateGroupForm() {
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

          <div className="flex flex-wrap items-center justify-start gap-4 pt-2">
            <Button className="h-12 min-w-[196px] text-base font-semibold">ایجاد گروه</Button>
            <Button variant="secondary" className="h-12 min-w-[148px] text-base font-semibold">
              انصراف
            </Button>
          </div>
        </div>

        <Card className="w-full rounded-[22px] p-5">
          <div className="flex h-full min-h-[360px] flex-col items-center justify-center rounded-[18px] border border-dashed border-border px-5 py-8 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
              <UserPlus className="h-8 w-8" strokeWidth={1.8} />
            </div>

            <h3 className="text-[20px] font-bold text-text">افزودن اعضا</h3>

            <p className="mt-3 max-w-[220px] text-sm leading-7 text-muted">
              اعضای گروه را از شماره تلفن یا مخاطبین خود اضافه کنید.
            </p>

            <Button
              variant="secondary"
              className="mt-6 h-12 w-full rounded-2xl text-[15px] font-semibold"
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
              <input
                type="text"
                placeholder="شماره موبایل را وارد کنید"
                className="form-input pr-4 pl-12"
              />
              <button
                type="button"
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-emerald-600"
              >
                <PlusCircle className="h-5 w-5" strokeWidth={1.9} />
              </button>
            </div>
          </div>
        </Card>
      </div>
    </Card>
  );
}
