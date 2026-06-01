# AI / Developer Handoff

این ریپو اولین صفحه پیاده‌سازی‌شده‌ی پروژه **همدنگ** است و در این نسخه، RTL واقعی داشبورد نیز اصلاح شده است.

## Current Status

- صفحه فعلی: **Groups Dashboard / گروه‌ها**
- استک: React + TypeScript + Vite + Tailwind CSS
- فونت: **Vazirmatn**
- طراحی: RTL، متن فارسی، کارت‌های سفید، پس‌زمینه خیلی روشن، مرزهای ظریف، گوشه‌های گرد، اکسنت سبز

## Keep These Rules For Future Pages

1. **Layout language ثابت بماند**
   - سایدبار همیشه **سمت راست**
   - هدر بالای بخش اصلی
   - پنل‌های کمکی در سمت چپ محتوای اصلی
   - RTL در کل اپ، نه فقط روی text-align

2. **Design language را تغییر ندهید**
   - پس‌زمینه روشن نزدیک به `#F8FAFC`
   - متن اصلی تیره
   - متن ثانویه خاکستری-آبی
   - مرزهای ظریف
   - سایه‌های نرم
   - گوشه‌های گرد
   - سبز به‌عنوان رنگ اصلی برند

3. **Component structure را حفظ کنید**
   - اجزای تکرارشونده reusable بمانند
   - داده‌های mock داخل `src/data`
   - typeها داخل `src/types`
   - UI primitives داخل `src/components/ui`

4. **Spacing و proportions**
   - سیستم فاصله‌گذاری 8px حفظ شود
   - title، cards، forms و panels هم‌خانواده بمانند
   - button height و input height در بازه Material-like حفظ شود

5. **Persian product feel**
   - ساختار و جایگذاری‌ها باید حس یک داشبورد ایرانی بدهند
   - سایدبار و ناحیه کاربر در هدر مطابق RTL واقعی باقی بمانند

در صفحه‌های بعدی همین layout skeleton، palette، spacing و component architecture ادامه پیدا کند.
