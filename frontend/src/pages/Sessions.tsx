import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  Play,
  Square,
  Radio,
  Mic,
  MicOff,
  Volume2,
  ArrowLeft,
  Gavel,
  User,
  Activity,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardHeader, CardTitle, Badge, Button, EmptyState } from '@/components/ui';
import { useSessionStore } from '@/stores/sessionStore';
import { useMockSttStream } from '@/lib/mockStt';
import { MOCK_RECENT_SESSIONS, DEMO_SPEAKERS } from '@/lib/mock-data';
import { formatDuration, formatMinutes } from '@/lib/format';
import { ROLE_STYLES, ROLE_LABEL } from '@/lib/speakerStyles';
import { cn } from '@/lib/cn';

export function Sessions() {
  const { t } = useTranslation();
  const lifecycle = useSessionStore((s) => s.lifecycle);
  const currentCase = useSessionStore((s) => s.currentCase);
  const elapsedSec = useSessionStore((s) => s.elapsedSec);
  const transcript = useSessionStore((s) => s.transcript);
  const speakers = useSessionStore((s) => s.speakers);
  const audioLevel = useSessionStore((s) => s.audioLevel);
  const isMuted = useSessionStore((s) => s.isMuted);
  const isLive = lifecycle === 'live' || lifecycle === 'starting';
  const isStopping = lifecycle === 'stopping';

  // Drive mock STT while session is in flight
  useMockSttStream(isLive);

  // Tick elapsed time
  useEffect(() => {
    if (lifecycle !== 'live') return;
    const id = setInterval(() => useSessionStore.getState().tick(), 1000);
    return () => clearInterval(id);
  }, [lifecycle]);

  // Lifecycle transitions: starting -> live, stopping -> idle
  useEffect(() => {
    if (lifecycle === 'starting') {
      const id = setTimeout(() => useSessionStore.getState().goLive(), 800);
      return () => clearTimeout(id);
    }
    if (lifecycle === 'stopping') {
      const id = setTimeout(() => useSessionStore.getState().reset(), 1200);
      return () => clearTimeout(id);
    }
  }, [lifecycle]);

  const handleStart = () => {
    const seed = MOCK_RECENT_SESSIONS.find((s) => s.status === 'live')!;
    useSessionStore.getState().start({
      caseNumber: seed.caseNumber,
      title: seed.title,
      judge: seed.judge,
    });
    // Pre-seed known speakers
    for (const sp of DEMO_SPEAKERS) {
      useSessionStore.getState().registerSpeaker(sp.id, sp.label, sp.role);
    }
  };

  const handleStop = () => {
    useSessionStore.getState().stop();
  };

  return (
    <div className="p-6 md:p-8 max-w-screen-2xl">
      <PageHeader
        title={t('nav.sessions')}
        subtitle={isLive
          ? currentCase
            ? `${currentCase.caseNumber} · ${currentCase.judge}`
            : 'Starting…'
          : 'Real-time transcription and speaker identification'}
      />

      {isLive ? (
        <LiveSessionView
          caseTitle={currentCase?.title ?? ''}
          caseNumber={currentCase?.caseNumber ?? ''}
          elapsedSec={elapsedSec}
          transcript={transcript}
          speakers={speakers}
          lifecycle={lifecycle}
        />
      ) : isStopping ? (
        <StoppingView />
      ) : (
        <IdleView onStart={handleStart} />
      )}

      {/* === Control bar === always visible, varies by state === */}
      <Card padding="md" className="mt-6 sticky bottom-4 z-10">
        <ControlBar
          isLive={isLive}
          isStopping={isStopping}
          isMuted={isMuted}
          audioLevel={audioLevel}
          onStart={handleStart}
          onStop={handleStop}
          onToggleMute={() => useSessionStore.getState().setMuted(!isMuted)}
        />
      </Card>

      {/* Recent sessions — visible in idle state for context */}
      {!isLive && !isStopping && <RecentSessionsCard className="mt-6" />}
    </div>
  );
}

// ============================================================================
// View: Live (transcript + speakers)
// ============================================================================

function LiveSessionView({
  caseTitle,
  caseNumber,
  elapsedSec,
  transcript,
  speakers,
  lifecycle,
}: {
  caseTitle: string;
  caseNumber: string;
  elapsedSec: number;
  transcript: ReturnType<typeof useSessionStore.getState>['transcript'];
  speakers: ReturnType<typeof useSessionStore.getState>['speakers'];
  lifecycle: 'idle' | 'starting' | 'live' | 'stopping' | 'stopped';
}) {
  return (
    <Card padding="none" className="overflow-hidden">
      {/* Status bar */}
      <div className="flex items-center justify-between gap-4 px-5 py-3 bg-error-container border-b border-red-200">
        <div className="flex items-center gap-3 min-w-0">
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full rounded-full bg-error opacity-60 animate-ping" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-error" />
          </span>
          <span className="text-mono text-error">LIVE</span>
          <span className="text-body-md text-ink font-medium truncate">{caseTitle}</span>
        </div>
        <div className="flex items-center gap-3 text-body-md text-ink-muted shrink-0">
          <span className="font-mono text-ink-muted">{caseNumber}</span>
          <span className="h-4 w-px bg-outline-soft" />
          <span className="font-mono tabular-nums text-ink">
            {lifecycle === 'starting' ? '00:00:00' : formatDuration(elapsedSec)}
          </span>
        </div>
      </div>

      {/* Body: transcript (main) + speaker list (right) */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] divide-y lg:divide-y-0 lg:divide-x divide-outline-soft">
        <TranscriptFeed entries={transcript} speakers={speakers} />
        <SpeakerList speakers={speakers} />
      </div>
    </Card>
  );
}

// ============================================================================
// Transcript
// ============================================================================

function TranscriptFeed({
  entries,
  speakers,
}: {
  entries: ReturnType<typeof useSessionStore.getState>['transcript'];
  speakers: ReturnType<typeof useSessionStore.getState>['speakers'];
}) {
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll to bottom when new entries appear (if user hasn't scrolled up)
  useEffect(() => {
    if (!autoScroll) return;
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [entries, autoScroll]);

  const onScroll = () => {
    const el = scrollerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setAutoScroll(distanceFromBottom < 40);
  };

  return (
    <div className="relative min-h-[480px] lg:min-h-[560px] flex flex-col">
      <div
        ref={scrollerRef}
        onScroll={onScroll}
        className="flex-1 overflow-y-auto p-5"
      >
        {entries.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center py-16">
            <div className="h-12 w-12 rounded-full bg-primary-50 text-primary-500 inline-flex items-center justify-center mb-3">
              <Activity className="h-5 w-5" />
            </div>
            <p className="text-title-lg text-ink">Listening…</p>
            <p className="text-body-md text-ink-muted mt-1">
              Waiting for the first utterance.
            </p>
          </div>
        ) : (
          <ol className="flex flex-col gap-4">
            {entries.map((entry) => {
              const sp = speakers.find((s) => s.id === entry.speakerId);
              const style = ROLE_STYLES[sp?.role ?? 'unknown'];
              return (
                <li key={entry.id} className="flex gap-3 group">
                  <div className="shrink-0 pt-1">
                    <span className={cn('block h-2 w-2 rounded-full', style.accent)} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1.5 h-6 px-2 rounded text-caption font-medium',
                          style.bg,
                          style.text,
                        )}
                      >
                        {sp?.label ?? entry.speakerId}
                      </span>
                      <span className="text-caption font-mono text-ink-muted tabular-nums">
                        {formatAtMs(entry.atMs)}
                      </span>
                      {!entry.isFinal && (
                        <span className="text-caption italic text-ink-muted">· listening…</span>
                      )}
                    </div>
                    <p
                      className={cn(
                        'text-body-lg text-ink leading-relaxed',
                        !entry.isFinal && 'opacity-60 italic',
                      )}
                    >
                      {entry.text}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>

      {/* Scroll affordance when user has scrolled up */}
      {!autoScroll && entries.length > 0 && (
        <button
          type="button"
          onClick={() => {
            setAutoScroll(true);
            const el = scrollerRef.current;
            if (el) el.scrollTop = el.scrollHeight;
          }}
          className="absolute bottom-4 right-4 inline-flex items-center gap-1.5 h-8 px-3 rounded-full bg-white border border-outline-soft shadow-floating text-caption font-medium text-ink hover:bg-surface-container-low"
        >
          ↓ Latest
        </button>
      )}
    </div>
  );
}

function formatAtMs(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// ============================================================================
// Speaker list
// ============================================================================

function SpeakerList({
  speakers,
}: {
  speakers: ReturnType<typeof useSessionStore.getState>['speakers'];
}) {
  return (
    <div className="bg-surface-container-lowest">
      <div className="px-5 py-3 border-b border-outline-soft flex items-center justify-between">
        <h3 className="text-mono text-ink-muted">Speaker Identification</h3>
        <span className="text-caption text-ink-muted">{speakers.length} detected</span>
      </div>

      <ul className="p-3 flex flex-col gap-2">
        {speakers.length === 0 && (
          <li className="text-body-md text-ink-muted px-2 py-6 text-center">
            Speakers will appear as they speak.
          </li>
        )}
        {speakers.map((sp) => {
          const style = ROLE_STYLES[sp.role];
          return (
            <li
              key={sp.id}
              className={cn(
                'flex items-center gap-3 p-3 rounded-md border transition-colors',
                sp.isSpeaking ? cn(style.bg, style.border) : 'bg-white border-outline-soft',
              )}
            >
              <div
                className={cn(
                  'h-9 w-9 rounded-full inline-flex items-center justify-center shrink-0',
                  sp.isSpeaking ? style.bg : 'bg-surface-container',
                  sp.isSpeaking ? style.text : 'text-ink-muted',
                )}
              >
                <User className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-body-md font-medium text-ink truncate">{sp.label}</p>
                <p className={cn('text-caption uppercase tracking-wide', style.text)}>
                  {ROLE_LABEL[sp.role]}
                </p>
              </div>
              {sp.isSpeaking && <SpeakingIndicator accentClass={style.accent} />}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SpeakingIndicator({ accentClass }: { accentClass: string }) {
  return (
    <span className="flex items-end gap-0.5 h-5 shrink-0">
      <span className={cn('w-0.5 rounded-full animate-pulse-dot', accentClass)} style={{ height: '40%' }} />
      <span
        className={cn('w-0.5 rounded-full animate-pulse-dot', accentClass)}
        style={{ height: '100%', animationDelay: '120ms' }}
      />
      <span
        className={cn('w-0.5 rounded-full animate-pulse-dot', accentClass)}
        style={{ height: '60%', animationDelay: '240ms' }}
      />
    </span>
  );
}

// ============================================================================
// Control bar
// ============================================================================

function ControlBar({
  isLive,
  isStopping,
  isMuted,
  audioLevel,
  onStart,
  onStop,
  onToggleMute,
}: {
  isLive: boolean;
  isStopping: boolean;
  isMuted: boolean;
  audioLevel: number;
  onStart: () => void;
  onStop: () => void;
  onToggleMute: () => void;
}) {
  return (
    <div className="flex items-center gap-4">
      <AudioMeter level={audioLevel} muted={isMuted || !isLive} />

      <div className="flex-1" />

      <Button
        variant="secondary"
        size="md"
        leftIcon={isMuted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        onClick={onToggleMute}
        disabled={!isLive}
      >
        {isMuted ? 'Unmute' : 'Mute'}
      </Button>

      {!isLive ? (
        <Button
          size="lg"
          leftIcon={<Play className="h-5 w-5 fill-current" />}
          onClick={onStart}
          disabled={isStopping}
        >
          {isStopping ? 'Stopping…' : 'Start Session'}
        </Button>
      ) : (
        <Button
          size="lg"
          variant="danger"
          leftIcon={<Square className="h-4 w-4 fill-current" />}
          onClick={onStop}
        >
          Stop Session
        </Button>
      )}
    </div>
  );
}

function AudioMeter({ level, muted }: { level: number; muted: boolean }) {
  // 24 bars, level (0-100) → count of lit bars
  const BARS = 24;
  const lit = muted ? 0 : Math.round((level / 100) * BARS);
  return (
    <div
      className="flex items-center gap-2"
      title={muted ? 'Microphone muted' : `Input level: ${Math.round(level)}%`}
    >
      <Volume2 className="h-4 w-4 text-ink-muted" />
      <div className="flex items-end gap-0.5 h-7">
        {Array.from({ length: BARS }).map((_, i) => {
          const on = i < lit;
          const color =
            i < 16 ? 'bg-emerald-500' : i < 21 ? 'bg-amber-500' : 'bg-error';
          return (
            <span
              key={i}
              className={cn('w-1 rounded-sm transition-all duration-75', on ? color : 'bg-outline-soft')}
              style={{ height: `${30 + (i / BARS) * 70}%` }}
            />
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// Idle + Stopping views
// ============================================================================

function IdleView({ onStart }: { onStart: () => void }) {
  const navigate = useNavigate();
  return (
    <Card padding="lg" className="text-center">
      <div className="mx-auto h-14 w-14 rounded-full bg-primary-50 text-primary-500 inline-flex items-center justify-center mb-4">
        <Radio className="h-7 w-7" />
      </div>
      <h2 className="text-headline-md text-ink mb-2">No active session</h2>
      <p className="text-body-lg text-ink-muted max-w-md mx-auto mb-6">
        Press Start Session to begin real-time speech capture, transcription and
        speaker identification.
      </p>
      <div className="flex items-center justify-center gap-3">
        <Button variant="ghost" leftIcon={<ArrowLeft className="h-4 w-4" />} onClick={() => navigate('/dashboard')}>
          Back to Dashboard
        </Button>
        <Button size="lg" leftIcon={<Play className="h-5 w-5 fill-current" />} onClick={onStart}>
          Start Session
        </Button>
      </div>
    </Card>
  );
}

function StoppingView() {
  return (
    <Card padding="lg" className="text-center">
      <div className="mx-auto h-14 w-14 rounded-full bg-surface-container text-ink-muted inline-flex items-center justify-center mb-4">
        <Square className="h-6 w-6" />
      </div>
      <h2 className="text-headline-md text-ink mb-2">Session stopped</h2>
      <p className="text-body-lg text-ink-muted max-w-md mx-auto">
        Saving transcript and preparing session summary…
      </p>
    </Card>
  );
}

// ============================================================================
// Recent sessions (idle context)
// ============================================================================

function RecentSessionsCard({ className }: { className?: string }) {
  const { t } = useTranslation();
  const past = MOCK_RECENT_SESSIONS.filter((s) => s.status !== 'live').slice(0, 3);

  return (
    <Card padding="md" className={className}>
      <CardHeader>
        <CardTitle>{t('dashboard.recentSessions')}</CardTitle>
      </CardHeader>
      {past.length === 0 ? (
        <EmptyState
          icon={<Gavel className="h-5 w-5" />}
          title="No prior sessions"
          description="Start a session to begin recording."
        />
      ) : (
        <ul className="flex flex-col divide-y divide-outline-soft -mx-6">
          {past.map((s) => (
            <li
              key={s.id}
              className="flex items-center gap-4 px-6 py-3 hover:bg-surface-container-low"
            >
              <div className="h-8 w-8 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center shrink-0">
                <Gavel className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-body-md font-medium text-ink truncate">{s.title}</p>
                <p className="text-caption font-mono text-ink-muted">
                  {s.caseNumber} · {formatMinutes(s.durationSec)}
                </p>
              </div>
              <Badge variant="success">{t('dashboard.completed')}</Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
