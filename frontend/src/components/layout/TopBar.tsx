import { useTranslation } from 'react-i18next';
import { Search, HelpCircle, Activity } from 'lucide-react';
import { IconButton } from '@/components/ui/IconButton';
import { Badge } from '@/components/ui/Badge';
import { UserMenu } from './UserMenu';
import { NotificationsBell } from './NotificationsBell';
import { cn } from '@/lib/cn';

const LANGS: Array<{ code: 'en' | 'uz' | 'ru'; label: string }> = [
  { code: 'en', label: 'EN' },
  { code: 'uz', label: 'UZ' },
  { code: 'ru', label: 'RU' },
];

interface TopBarProps {
  systemOnline: boolean;
  uptimeHours: number;
}

export function TopBar({ systemOnline, uptimeHours }: TopBarProps) {
  const { t, i18n } = useTranslation();

  const setLang = (code: 'en' | 'uz' | 'ru') => {
    void i18n.changeLanguage(code);
    localStorage.setItem('sud-lang', code);
  };

  return (
    <header className="h-16 bg-white border-b border-outline-soft px-6 flex items-center gap-4 sticky top-0 z-10">
      {/* Search — disabled in CP1 (no global search yet) */}
      <div className="flex-1 max-w-xl relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-muted pointer-events-none" />
        <input
          type="search"
          placeholder={t('common.search') + '…'}
          className="w-full h-10 pl-9 pr-3 rounded-md border border-outline-soft bg-surface text-body-md text-ink placeholder:text-ink-muted focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15 transition-colors"
          aria-label={t('common.search')}
          disabled
        />
      </div>

      <div className="flex-1" />

      {/* System status pill — CP1 MVP-relevant */}
      <div
        className={cn(
          'hidden md:inline-flex items-center gap-2 h-9 px-3 rounded-md border text-body-md',
          systemOnline
            ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
            : 'bg-error-container border-red-200 text-error',
        )}
        title={`Uptime ${uptimeHours.toFixed(1)} h`}
      >
        <Activity className="h-4 w-4" />
        <span className="font-medium">{t('system.status')}</span>
        <Badge variant={systemOnline ? 'success' : 'error'} dot>
          {systemOnline ? t('system.online') : t('system.offline')}
        </Badge>
      </div>

      {/* Language switcher */}
      <div className="hidden md:inline-flex items-center bg-surface-container rounded-md p-0.5">
        {LANGS.map(({ code, label }) => (
          <button
            key={code}
            type="button"
            onClick={() => setLang(code)}
            className={cn(
              'h-8 px-2.5 rounded text-caption font-mono uppercase tracking-wide transition-colors',
              i18n.language === code
                ? 'bg-white text-ink shadow-soft'
                : 'text-ink-muted hover:text-ink',
            )}
            aria-label={`${t('common.language')}: ${label}`}
          >
            {label}
          </button>
        ))}
      </div>

      <UserMenu variant="topbar" className="hidden lg:inline-flex" />

      <NotificationsBell />

      <IconButton icon={<HelpCircle className="h-5 w-5" />} label="Help" />
    </header>
  );
}
