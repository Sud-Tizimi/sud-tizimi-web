import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center py-12 px-6 gap-3',
        className,
      )}
    >
      {icon && (
        <div className="h-12 w-12 rounded-full bg-surface-container text-ink-muted inline-flex items-center justify-center mb-1">
          {icon}
        </div>
      )}
      <h4 className="text-title-lg text-ink">{title}</h4>
      {description && <p className="text-body-md text-ink-muted max-w-sm">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
