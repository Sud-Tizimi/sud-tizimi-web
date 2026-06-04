import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  LayoutDashboard,
  Scale,
  Radio,
  // CP2 FEATURE — ENABLE AFTER CHECKPOINT 1
  FileText,
  Sparkles,
  Bell,
  Settings as SettingsIcon,
  ShieldCheck,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { ENABLED_FEATURES } from '@/lib/featureFlags';

interface NavItem {
  to: string;
  labelKey: string;
  icon: typeof LayoutDashboard;
  flag: keyof typeof ENABLED_FEATURES;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard, flag: 'dashboard' },
  { to: '/cases', labelKey: 'nav.cases', icon: Scale, flag: 'cases' },
  { to: '/sessions', labelKey: 'nav.sessions', icon: Radio, flag: 'sessions' },

  // CP2 FEATURE — HIDDEN FOR MVP — ENABLE AFTER CHECKPOINT 1
  // { to: '/documents', labelKey: 'nav.documents', icon: FileText, flag: 'documents' },
  // { to: '/ai', labelKey: 'nav.ai', icon: Sparkles, flag: 'aiSummary' },
  // { to: '/notifications', labelKey: 'nav.notifications', icon: Bell, flag: 'notifications' },
  // { to: '/settings', labelKey: 'nav.settings', icon: SettingsIcon, flag: 'settings' },
];

export function Sidebar() {
  const { t } = useTranslation();

  const visibleItems = NAV_ITEMS.filter((item) => ENABLED_FEATURES[item.flag]);

  return (
    <aside className="hidden lg:flex w-sidebar shrink-0 flex-col bg-navy-700 text-white">
      {/* Logo */}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-white/5">
        <div className="h-9 w-9 rounded-md bg-primary-500 inline-flex items-center justify-center">
          <ShieldCheck className="h-5 w-5 text-white" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-body-lg font-semibold tracking-tight">{t('app.name')}</span>
          <span className="text-caption text-white/50 uppercase tracking-wider">{t('app.tagline')}</span>
        </div>
      </div>

      {/* Nav — CP1 only. CP2 items are commented above and restored on Checkpoint 2. */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        <ul className="flex flex-col gap-1">
          {visibleItems.map(({ to, labelKey, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/dashboard'}
                className={({ isActive }) =>
                  cn(
                    'group relative flex items-center gap-3 h-10 px-3 rounded-md text-body-md font-medium transition-colors',
                    isActive
                      ? 'bg-white/10 text-white'
                      : 'text-white/70 hover:text-white hover:bg-white/5',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r bg-primary-500" />
                    )}
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1">{t(labelKey)}</span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* User footer */}
      <div className="p-3 border-t border-white/5">
        <div className="flex items-center gap-3 px-2 py-2 rounded-md">
          <div className="h-9 w-9 rounded-full bg-primary-500/20 text-primary-100 inline-flex items-center justify-center text-body-md font-semibold">
            RK
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-body-md font-medium truncate">Rustam Karimov</p>
            <p className="text-caption text-white/50 truncate">Judge • Tashkent</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

// CP2 FEATURE — ENABLE AFTER CHECKPOINT 1
// `FileText`, `Sparkles`, `Bell`, `SettingsIcon` icons reserved for CP2 nav.
// Imported above to keep tree-shakable imports in one place.
void FileText;
void Sparkles;
void Bell;
void SettingsIcon;
