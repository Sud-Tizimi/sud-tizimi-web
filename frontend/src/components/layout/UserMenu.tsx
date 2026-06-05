/**
 * User menu — avatar (initials), full name, role/court badge, Logout.
 *
 * Two visual variants:
 * - ``variant="sidebar"`` (default) — used in the Sidebar footer. Full
 *   info: name, court, role, dropdown menu on click.
 * - ``variant="topbar"`` — compact, no card chrome, used in the TopBar.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LogOut, ChevronDown } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/cn';

interface Props {
  variant?: 'sidebar' | 'topbar';
  className?: string;
}

function initials(name: string | undefined | null): string {
  if (!name) return '?';
  const parts = name.replace(/^Hon\.\s*/i, '').trim().split(/\s+/);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function UserMenu({ variant = 'sidebar', className }: Props) {
  const { user, role, clear } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  const onLogout = () => {
    clear();
    setOpen(false);
    navigate('/login', { replace: true });
  };

  if (variant === 'topbar') {
    return (
      <div className={cn('relative', className)}>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-2 rounded-md px-2 py-1 hover:bg-surface-container-low transition-colors"
          aria-haspopup="menu"
          aria-expanded={open}
        >
          <div className="h-7 w-7 rounded-full bg-primary-500 text-white inline-flex items-center justify-center text-caption font-semibold">
            {initials(user.fullName)}
          </div>
          <span className="text-body-md text-ink font-medium hidden md:inline">
            {user.fullName}
          </span>
          <ChevronDown className="h-3.5 w-3.5 text-ink-muted" />
        </button>
        {open && (
          <>
            <button
              type="button"
              className="fixed inset-0 z-10"
              onClick={() => setOpen(false)}
              aria-label="dismiss menu"
            />
            <div className="absolute right-0 mt-2 w-56 rounded-md bg-white border border-outline-soft shadow-floating z-20">
              <div className="px-3 py-2 border-b border-outline-soft">
                <p className="text-body-md font-medium text-ink truncate">{user.fullName}</p>
                <p className="text-caption text-ink-muted truncate">{user.email}</p>
                <p className="text-caption text-ink-muted uppercase tracking-wide mt-1">
                  {role}
                </p>
              </div>
              <button
                type="button"
                onClick={onLogout}
                className="w-full text-left px-3 py-2 text-body-md text-ink hover:bg-surface-container-low flex items-center gap-2"
              >
                <LogOut className="h-4 w-4 text-ink-muted" />
                {t('common.logout')}
              </button>
            </div>
          </>
        )}
      </div>
    );
  }

  // Sidebar variant — full info, no chevron.
  return (
    <div className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 rounded-md p-2 hover:bg-white/5 transition-colors text-left"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <div className="h-9 w-9 rounded-full bg-primary-500 text-white inline-flex items-center justify-center text-body-md font-semibold shrink-0">
          {initials(user.fullName)}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-body-md font-medium text-white truncate">{user.fullName}</p>
          {user.court ? (
            <p className="text-caption text-white/60 truncate">{user.court}</p>
          ) : null}
          <p className="text-caption text-white/40 uppercase tracking-wide">
            {role}
          </p>
        </div>
        <ChevronDown className="h-3.5 w-3.5 text-white/50 shrink-0" />
      </button>
      {open && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
            aria-label="dismiss menu"
          />
          <div className="absolute left-0 right-0 bottom-full mb-1 mx-2 rounded-md bg-white border border-outline-soft shadow-floating z-20">
            <div className="px-3 py-2 border-b border-outline-soft">
              <p className="text-caption text-ink-muted">{user.email}</p>
            </div>
            <button
              type="button"
              onClick={onLogout}
              className="w-full text-left px-3 py-2 text-body-md text-ink hover:bg-surface-container-low flex items-center gap-2"
            >
              <LogOut className="h-4 w-4 text-ink-muted" />
              {t('common.logout')}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
