import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Bell, Check } from 'lucide-react';
import { IconButton } from '@/components/ui/IconButton';
import { cn } from '@/lib/cn';
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  unreadCount,
} from '@/hooks/queries';

/**
 * In-system notification bell — surfaces events from case-management.md §17.
 * Clicking the bell opens a small panel listing the latest 5 events.
 *
 * Phase A: backed by the API via TanStack Query (no more caseStore).
 */
export function NotificationsBell() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const { data: notifications = [] } = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();

  const unread = unreadCount(notifications);
  const visible = notifications.slice(0, 5);

  return (
    <div className="relative">
      <IconButton
        size="md"
        variant="subtle"
        label={t('common.notifications')}
        onClick={() => setOpen((v) => !v)}
        icon={
          <span className="relative">
            <Bell className="h-5 w-5" />
            {unread > 0 && (
              <span
                className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-error text-error-on text-[10px] font-semibold inline-flex items-center justify-center"
                aria-label={`${unread} unread`}
              >
                {unread}
              </span>
            )}
          </span>
        }
      />
      {open && (
        <>
          {/* Click-catcher to dismiss */}
          <button
            type="button"
            aria-label="Close"
            className="fixed inset-0 z-20 cursor-default"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-80 max-w-[90vw] z-30 rounded-lg bg-white border border-outline-soft shadow-floating">
            <div className="flex items-center justify-between px-4 py-3 border-b border-outline-soft">
              <h4 className="text-title-lg text-ink">
                {t('caseMgmt.notifications.title')}
              </h4>
              {unread > 0 && (
                <button
                  type="button"
                  onClick={() => markAll.mutate()}
                  className="inline-flex items-center gap-1 text-caption text-primary-600 hover:underline"
                >
                  <Check className="h-3 w-3" />
                  {t('caseMgmt.notifications.markAllRead')}
                </button>
              )}
            </div>
            <ul className="max-h-80 overflow-y-auto">
              {visible.length === 0 && (
                <li className="px-4 py-6 text-center text-body-md text-ink-muted">
                  {t('caseMgmt.notifications.empty')}
                </li>
              )}
              {visible.map((n) => (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() => {
                      if (!n.read) markRead.mutate(n.id);
                      setOpen(false);
                      navigate(`/cases/${n.caseId}`);
                    }}
                    className={cn(
                      'w-full text-left px-4 py-3 hover:bg-surface-container-low flex items-start gap-3',
                      !n.read && 'bg-primary-50/40',
                    )}
                  >
                    <span
                      className={cn(
                        'h-2 w-2 rounded-full mt-2 shrink-0',
                        n.read ? 'bg-outline' : 'bg-primary-500',
                      )}
                    />
                    <span className="min-w-0">
                      <p className="text-body-md text-ink">{t(n.messageKey)}</p>
                      <p className="text-caption font-mono text-ink-muted mt-0.5">
                        {new Date(n.at).toLocaleString()}
                      </p>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
