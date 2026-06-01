# Hamdong Groups Dashboard

نسخه‌ی به‌روزشده‌ی اولین صفحه فرانت‌اند پروژه **همدنگ** با تمرکز روی **RTL واقعی برای داشبورد فارسی**.

## Tech Stack

- React
- TypeScript
- Vite
- Tailwind CSS
- lucide-react
- Vazirmatn
- RTL / Persian UI

## Install

```bash
npm install
```

## Run

```bash
npm run dev
```

## Build

```bash
npm run build
```

## File Structure

```text
hamdong-groups-page/
├── package.json
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── tailwind.config.js
├── postcss.config.js
├── README.md
├── AI_HANDOFF_PROMPT.md
├── public/
│   └── reference/
│       └── groups-dashboard.png
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── data/
    │   └── mockData.ts
    ├── types/
    │   └── index.ts
    └── components/
        ├── Sidebar.tsx
        ├── TopBar.tsx
        ├── GroupCard.tsx
        ├── CreateGroupForm.tsx
        ├── AccountSummary.tsx
        ├── RecentMembers.tsx
        ├── RecentActivities.tsx
        └── ui/
            ├── Card.tsx
            └── Button.tsx
```

## What Changed

- سایدبار به **سمت راست** منتقل شد و رفتار **sticky / h-screen** گرفت.
- ساختار کلی صفحه برای RTL واقعی بازچینی شد:
  - سایدبار سمت راست
  - محتوای اصلی در میانه
  - پنل اطلاعات در سمت چپ
- هدر از نظر RTL اصلاح شد و بخش کاربر در سمت راست قرار گرفت.
- فونت پروژه به **Vazirmatn** تغییر کرد.
- ابعاد تایپوگرافی، کارت‌ها، دکمه‌ها و فواصل بر اساس سیستم 8px هماهنگ‌تر شد.
- فرم «تشکیل گروه جدید» از نظر RTL و spacing بازتنظیم شد.

## Notes

- تصویر مرجع داخل مسیر `public/reference/groups-dashboard.png` قرار دارد.
- این ساختار برای توسعه صفحه‌های بعدی پروژه در همین سبک آماده است.
