import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  fullWidth?: boolean;
}

const VARIANT_STYLES: Record<Variant, string> = {
  primary:
    'bg-primary-500 text-white border border-primary-500 hover:bg-primary-600 hover:border-primary-600 active:bg-primary-700 disabled:bg-primary-200 disabled:border-primary-200 disabled:cursor-not-allowed',
  secondary:
    'bg-white text-ink border border-outline-soft hover:border-outline hover:bg-surface-container-low disabled:opacity-50 disabled:cursor-not-allowed',
  ghost:
    'bg-transparent text-ink border border-transparent hover:bg-surface-container-low disabled:opacity-50 disabled:cursor-not-allowed',
  danger:
    'bg-error text-error-on border border-error hover:bg-error/90 disabled:opacity-50 disabled:cursor-not-allowed',
};

const SIZE_STYLES: Record<Size, string> = {
  sm: 'h-8 px-3 text-body-md gap-1.5 rounded',
  md: 'h-10 px-4 text-body-lg gap-2 rounded-lg',
  lg: 'h-12 px-6 text-body-lg gap-2 rounded-lg',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', leftIcon, rightIcon, fullWidth, className, children, ...rest }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
          VARIANT_STYLES[variant],
          SIZE_STYLES[size],
          fullWidth && 'w-full',
          className,
        )}
        {...rest}
      >
        {leftIcon && <span className="shrink-0">{leftIcon}</span>}
        {children}
        {rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </button>
    );
  },
);
Button.displayName = 'Button';
