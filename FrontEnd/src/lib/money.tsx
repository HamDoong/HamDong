import type { HTMLAttributes } from 'react';

export function toPersianNumber(value: string | number) {
  return String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);
}

function joinPersianParts(parts: string[]) {
  return parts.filter(Boolean).join(' و ');
}

const ones = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه'];
const teens = ['ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده'];
const tens = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود'];
const hundreds = ['', 'صد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد'];
const groups = ['', 'هزار', 'میلیون', 'میلیارد', 'تریلیون'];

function threeDigitToPersianWords(value: number) {
  const parts: string[] = [];
  const hundred = Math.floor(value / 100);
  const rest = value % 100;

  if (hundred) {
    parts.push(hundreds[hundred]);
  }

  if (rest >= 10 && rest < 20) {
    parts.push(teens[rest - 10]);
  } else {
    const ten = Math.floor(rest / 10);
    const one = rest % 10;

    if (ten) {
      parts.push(tens[ten]);
    }

    if (one) {
      parts.push(ones[one]);
    }
  }

  return joinPersianParts(parts);
}

export function numberToPersianWords(value: number | string | null | undefined) {
  const roundedValue = Math.abs(Math.round(Number(value ?? 0)));

  if (roundedValue === 0) return 'صفر';

  const parts: string[] = [];
  let remaining = roundedValue;
  let groupIndex = 0;

  while (remaining > 0) {
    const chunk = remaining % 1000;

    if (chunk) {
      const chunkText = threeDigitToPersianWords(chunk);
      const groupText = groups[groupIndex] || '';
      parts.unshift([chunkText, groupText].filter(Boolean).join(' '));
    }

    remaining = Math.floor(remaining / 1000);
    groupIndex += 1;
  }

  return joinPersianParts(parts);
}

function toEnglishDigits(value: string) {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)));
}

export function normalizeMoneyAmount(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return 0;

  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0;
  }

  const normalized = toEnglishDigits(String(value));
  const match = normalized.match(/[-+]?\d+(?:[.,]\d+)?/);

  if (!match) return 0;

  const numericValue = Number(match[0].replace(/,/g, '').replace(/٫/g, '.'));
  return Number.isFinite(numericValue) ? numericValue : 0;
}

export function formatMoneyNumber(
  value: number | string | null | undefined,
  options?: { currency?: string; signed?: boolean },
) {
  const amount = normalizeMoneyAmount(value);
  const rounded = Math.round(Math.abs(amount));
  const currency = options?.currency ?? 'تومان';
  const sign = options?.signed && amount < 0 ? '-' : options?.signed && amount > 0 ? '+' : '';
  const digits = toPersianNumber(rounded.toLocaleString('en-US'));
  return `${currency} \u2066${sign}${digits}\u2069`;
}

export function formatMoneyText(
  value: number | string | null | undefined,
  currency = 'تومان',
) {
  return `${currency} ${numberToPersianWords(value)}`;
}

export function formatSignedMoney(value: number | string | null | undefined, currency = 'تومان') {
  return formatMoneyNumber(value, { currency, signed: true });
}

interface MoneyWithWordsProps extends HTMLAttributes<HTMLDivElement> {
  amount: number | string | null | undefined;
  currency?: string;
  valueClassName?: string;
  textClassName?: string;
  signed?: boolean;
  showText?: boolean;
}

export function MoneyWithWords({
  amount,
  currency = 'تومان',
  className,
  valueClassName,
  textClassName,
  signed = false,
  showText = true,
  ...props
}: MoneyWithWordsProps) {
  const numericAmount = normalizeMoneyAmount(amount);
  const valueText = formatMoneyNumber(numericAmount, { currency, signed });
  const textValue = showText ? formatMoneyText(numericAmount, currency) : null;

  return (
    <div className={className} {...props}>
      <div className={valueClassName}>{valueText}</div>
      {showText && textValue ? <div className={textClassName}>{textValue}</div> : null}
    </div>
  );
}
