import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import {
  Activity,
  Play,
  ArrowRight,
  Radio,
  Gavel,
  Mic,
  AlertTriangle,
  Cpu,
  Headphones,
  Users,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardHeader, CardTitle, Badge, Button, EmptyState } from '@/components/ui';
import { MOCK_RECENT_SESSIONS, SYSTEM_STATUS, type HealthState } from '@/lib/mock-data';
import { useSessionStore } from '@/stores/sessionStore';
import { formatDuration } from '@/lib/format';
import { cn } from '@/lib/cn';

const HEALTH_BADGE: Record<HealthState, { variant: 'success' | 'warning' | 'error'; key: string }> = {
  online: { variant: 'success', key: 'system.online' },
  degraded: { variant: 'warning', key: 'system.degraded' },
  offline: { variant: 'error', key: 'system.offline' },
};

const HEALTH_ICON_BG: Record<HealthState, string> = {
  online: 'bg-emerald-100 text-emerald-500',
  degraded: 'bg-amber-50 text-amber-600',
  offline: 'bg-error-container text-error',
};

export function Dashboard() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  // Live session may be: in-flight via the store, OR represented in mock data
  const liveFromStore = useSessionStore((s) => (s.lifecycle === 'live' || s.lifecycle === 'starting' ? s.currentCase : null));
  const speakersInStore = useSessionStore((s) => s.speakers);
  const elapsed = useSessionStore((s) => s.elapsedSec);

  const mockLive = MOCK_RECENT_SESSIONS.find((s) => s.status === 'live');
  const isLive = Boolean(liveFromStore) || Boolean(mockLive);
  const liveCase = liveFromStore ?? mockLive;
  const speakerCount = speakersInStore.length > 0 ? speakersInStore.length : 3;

  const healthKey = HEALTH_BADGE[SYSTEM_STATUS.state];

  return (
    <div className="p-6 md:p-8 max-w-screen-2xl">
      <PageHeader
        title={t('dashboard.title')}
        subtitle={t('dashboard.subtitle')}
        actions={
          <Button
            size="lg"
            leftIcon={<Play className="h-5 w-5 fill-current" />}
            onClick={() => navigate('/sessions')}
          >
            {t('dashboard.startSession')}
          </Button>
        }
      />

      {/* === System Status === MVP-critical block === */}
      <Card padding="lg" className="mb-6">
        <div className="flex items-start gap-4 mb-6">
          <div
            className={cn(
              'h-12 w-12 rounded-lg inline-flex items-center justify-center shrink-0',
              HEALTH_ICON_BG[SYSTEM_STATUS.state],
            )}
          >
            {SYSTEM_STATUS.state === 'online' ? (
              <Activity className="h-6 w-6" />
            ) : (
              <AlertTriangle className="h-6 w-6" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h2 className="text-title-lg text-ink">{t('system.status')}</h2>
              <Badge variant={healthKey.variant} dot>
                {t(healthKey.key)}
              </Badge>
            </div>
            <p className="text-body-md text-ink-muted">{t('system.allSystems')}</p>
          </div>
        </div>

        {/* Subsystem statuses — exactly what goal.md asks for */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <SubsystemCard
            icon={<Cpu className="h-5 w-5" />}
            label="STT"
            value={t('system.online')}
            detail={SYSTEM_STATUS.sttEngine}
            metric={`${SYSTEM_STATUS.sttLatencyMs} ms`}
            metricLabel="latency"
            state={SYSTEM_STATUS.state}
          />
          <SubsystemCard
            icon={<Headphones className="h-5 w-5" />}
            label="Speaker Identification"
            value={t(`system.${SYSTEM_STATUS.speakerIdState}`)}
            detail={SYSTEM_STATUS.diarizationEngine}
            metric={isLive ? `${speakerCount} active` : '—'}
            metricLabel={isLive ? 'speakers' : 'awaiting session'}
            state={SYSTEM_STATUS.speakerIdState}
          />
          <SubsystemCard
            icon={<Users className="h-5 w-5" />}
            label={t('dashboard.activeSessions')}
            value={`${SYSTEM_STATUS.activeSessions}`}
            detail={isLive ? 'Including your live session' : 'No sessions running'}
            metric={isLive ? '1 live now' : 'Idle'}
            metricLabel="right now"
            state={isLive ? 'online' : 'offline'}
          />
        </div>
      </Card>

      {/* === Active Session banner (if any) === */}
      {liveCase && (
        <Card padding="md" className="mb-6 border-primary-200 bg-primary-50/30">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-start gap-4 min-w-0">
              <div className="h-11 w-11 rounded-md bg-error-container text-error inline-flex items-center justify-center shrink-0">
                <Mic className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <h3 className="text-title-lg text-ink truncate">{liveCase.title}</h3>
                  <Badge variant="live" dot>
                    {t('dashboard.live')}
                  </Badge>
                </div>
                <p className="text-caption font-mono text-ink-muted">
                  {liveCase.caseNumber} · {liveCase.judge}
                  {liveFromStore && (
                    <> · {speakerCount} speakers detected</>
                  )}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              {liveFromStore && (
                <div className="text-right">
                  <p className="text-mono text-ink-muted">Elapsed</p>
                  <p className="text-headline-md text-ink font-mono tabular-nums">
                    {formatDuration(elapsed)}
                  </p>
                </div>
              )}
              <Button
                size="lg"
                leftIcon={<Radio className="h-5 w-5" />}
                onClick={() => navigate('/sessions')}
              >
                Open Session
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* === Recent Sessions === minimal history, supports demo narrative === */}
      <Card padding="md">
        <CardHeader>
          <div>
            <CardTitle>{t('dashboard.recentSessions')}</CardTitle>
            <p className="text-body-md text-ink-muted mt-0.5">{t('dashboard.today')}</p>
          </div>
          <Button variant="ghost" size="sm" rightIcon={<ArrowRight className="h-4 w-4" />}>
            {t('dashboard.viewAll')}
          </Button>
        </CardHeader>

        <RecentSessionsTable locale={i18n.language} />
      </Card>
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

function SubsystemCard({
  icon,
  label,
  value,
  detail,
  metric,
  metricLabel,
  state,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
  metric: string;
  metricLabel: string;
  state: HealthState;
}) {
  return (
    <div className="rounded-md border border-outline-soft bg-white p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="h-8 w-8 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center">
          {icon}
        </span>
        <span className="text-mono text-ink-muted">{label}</span>
      </div>
      <div className="flex items-baseline gap-2 mb-1">
        <span className="text-title-lg text-ink font-semibold">{value}</span>
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            state === 'online' && 'bg-emerald-500',
            state === 'degraded' && 'bg-amber-500',
            state === 'offline' && 'bg-error',
          )}
        />
      </div>
      <p className="text-caption text-ink-muted mb-3">{detail}</p>
      <div className="pt-3 border-t border-outline-soft flex items-baseline justify-between">
        <span className="text-headline-md text-ink font-mono tabular-nums">{metric}</span>
        <span className="text-caption text-ink-muted">{metricLabel}</span>
      </div>
    </div>
  );
}

function RecentSessionsTable({ locale }: { locale: string }) {
  const { t } = useTranslation();
  const past = MOCK_RECENT_SESSIONS.filter((s) => s.status !== 'live');

  if (past.length === 0) {
    return (
      <EmptyState
        icon={<Gavel className="h-5 w-5" />}
        title={t('dashboard.noSessions')}
        description={t('dashboard.startFirst')}
      />
    );
  }

  return (
    <div className="overflow-x-auto -mx-6">
      <table className="w-full">
        <thead>
          <tr className="border-b border-outline-soft">
            <th className="text-left text-mono text-ink-muted h-10 px-6 font-medium">
              {t('dashboard.case')}
            </th>
            <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium hidden md:table-cell">
              {t('dashboard.started')}
            </th>
            <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium hidden sm:table-cell">
              {t('dashboard.duration')}
            </th>
            <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium">
              {t('dashboard.status')}
            </th>
          </tr>
        </thead>
        <tbody>
          {past.map((session) => (
            <tr
              key={session.id}
              className="border-b border-outline-soft last:border-0 hover:bg-surface-container-low transition-colors"
            >
              <td className="px-6 py-4">
                <div className="flex items-start gap-3">
                  <div className="h-9 w-9 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center shrink-0">
                    <Gavel className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-body-md font-medium text-ink truncate">
                      {session.title}
                    </p>
                    <p className="text-caption font-mono text-ink-muted">
                      {session.caseNumber} · {session.judge}
                    </p>
                  </div>
                </div>
              </td>
              <td className="px-3 py-4 text-body-md text-ink-muted hidden md:table-cell">
                {formatDistanceToNow(new Date(session.startedAt), { addSuffix: true })}{' '}
                <span className="text-caption text-ink-muted/70">
                  ({new Date(session.startedAt).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })})
                </span>
              </td>
              <td className="px-3 py-4 text-body-md text-ink font-mono tabular-nums hidden sm:table-cell">
                {formatDuration(session.durationSec)}
              </td>
              <td className="px-3 py-4">
                <Badge variant="success">{t('dashboard.completed')}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
