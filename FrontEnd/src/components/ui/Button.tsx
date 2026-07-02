import type { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'bg-primary-gradient text-white shadow-button hover:-translate-y-0.5 hover:shadow-button focus-visible:ring-primary/25',
  secondary: 'border border-border bg-surface text-text shadow-sm hover:border-border-strong hover:bg-surface-soft focus-visible:ring-primary/20',
  ghost: 'border border-transparent bg-transparent text-muted hover:bg-surface-soft hover:text-text focus-visible:ring-primary/20',
};

export function Button({
  variant = 'primary',
  children,
  className = '',
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-2xl px-5 transition focus-visible:outline-none focus-visible:ring-4 disabled:cursor-not-allowed disabled:opacity-60 ${variantClasses[variant]} ${className}`.trim()}
      {...props}
    >
      {children}
    </button>
  );
}
