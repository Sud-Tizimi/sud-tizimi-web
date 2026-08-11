import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  CheckCircle2,
  Download,
  Edit3,
  FileAudio,
  Headphones,
  Loader2,
  Mic,
  Radio,
  Save,
  Square,
  UploadCloud,
  Volume2,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge, Button, Card, CardHeader, CardTitle } from '@/components/ui';
import { cn } from '@/lib/cn';
import { getMicrophoneIssue, getUserMediaOrThrow, toMicrophoneIssue, type MicrophoneIssue } from '@/lib/microphone';
import type { ASRSegment, ASRTranscriptionResponse, ASRWord } from '@/types/domain';

const API_BASE: string = (import.meta.env.VITE_API_URL as string | undefined) || '';

type Mode = 'upload' | 'live' | 'local';
type Provider = 'openrouter' | 'aistudio';
type JobState = 'idle' | 'running' | 'done' | 'error';
type WordTooltipState = {
  key: string;
  word: ASRWord;
  x: number;
  y: number;
  canPlay: boolean;
  onPlay: () => void;
} | null;

const PALETTE = [
  { text: 'text-primary-700', bg: 'bg-primary-50', border: 'border-primary-200', dot: 'bg-primary-500' },
  { text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', dot: 'bg-amber-500' },
  { text: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-200', dot: 'bg-rose-500' },
  { text: 'text-sky-700', bg: 'bg-sky-50', border: 'border-sky-200', dot: 'bg-sky-500' },
  { text: 'text-violet-700', bg: 'bg-violet-50', border: 'border-violet-200', dot: 'bg-violet-500' },
  { text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', dot: 'bg-emerald-500' },
];

export function Sessions() {
  const { t } = useTranslation();
  const [mode, setMode] = useState<Mode>('upload');
  const [uploadProvider, setUploadProvider] = useState<Provider>('openrouter');
  const [liveProvider, setLiveProvider] = useState<Provider>('openrouter');
  const [file, setFile] = useState<File | null>(null);
  const [localFile, setLocalFile] = useState<File | null>(null);
  const [language, setLanguage] = useState('');
  const [speakers, setSpeakers] = useState('');
  const [liveLanguage, setLiveLanguage] = useState('Uzbek');
  const [localLanguage, setLocalLanguage] = useState('Uzbek');
  const [localTimestamp, setLocalTimestamp] = useState(true);
  const [localDiarize, setLocalDiarize] = useState(false);
  const [state, setState] = useState<JobState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ASRTranscriptionResponse | null>(null);
  const [editing, setEditing] = useState(false);
  const [editRows, setEditRows] = useState<ASRSegment[]>([]);
  const [localHealth, setLocalHealth] = useState<Record<string, unknown> | null>(null);
  const [localLanguages, setLocalLanguages] = useState<string[]>(['Uzbek', 'English', 'Russian']);
  const [recording, setRecording] = useState(false);
  const [recordSecs, setRecordSecs] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [audioBuffer, setAudioBuffer] = useState<AudioBuffer | null>(null);
  const [activeWordKey, setActiveWordKey] = useState<string | null>(null);
  const [wordTooltip, setWordTooltip] = useState<WordTooltipState>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<AudioBufferSourceNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const rafRef = useRef<number | null>(null);
  const tooltipTimerRef = useRef<number | null>(null);

  const visibleSegments = editing ? editRows : result?.segments ?? [];
  const stats = useMemo(() => computeStats(result), [result]);
  const liveRecordingIssue = getMicrophoneIssue();
  const liveRecordingError = liveRecordingIssue ? describeMicrophoneIssue(t, liveRecordingIssue) : null;

  useEffect(() => {
    void loadLocalMeta();
    return () => cleanupMedia();
  }, []);

  async function loadLocalMeta() {
    try {
      const [healthRes, langRes] = await Promise.all([
        fetch(`${API_BASE}/api/asr/local/health`),
        fetch(`${API_BASE}/api/asr/local/languages`),
      ]);
      if (healthRes.ok) setLocalHealth(await healthRes.json());
      if (langRes.ok) {
        const data = await langRes.json();
        const langs = normalizeLanguages(data);
        if (langs.length) setLocalLanguages(langs);
      }
    } catch {
      setLocalHealth({ status: 'offline' });
    }
  }

  async function setPlayableFile(next: File, local = false) {
    if (local) setLocalFile(next);
    else setFile(next);
    const buffer = await next.arrayBuffer();
    const ctx = getAudioContext();
    try {
      setAudioBuffer(await ctx.decodeAudioData(buffer.slice(0)));
    } catch {
      setAudioBuffer(null);
    }
  }

  async function runTranscribe(targetFile: File, provider: string, lang: string, opts?: { speakers?: string; diarize?: boolean }) {
    setState('running');
    setError(null);
    setEditing(false);
    setResult(null);
    setWordTooltip(null);
    const form = new FormData();
    form.append('audio', targetFile, targetFile.name);
    form.append('provider', provider);
    if (lang.trim()) form.append('language', lang.trim());
    if (opts?.speakers?.trim()) form.append('speakers', opts.speakers.trim());
    form.append('diarize', opts?.diarize ? 'true' : 'false');

    try {
      const response = await fetch(`${API_BASE}/api/asr/transcribe`, { method: 'POST', body: form });
      if (!response.ok) throw new Error(await response.text());
      const data = (await response.json()) as ASRTranscriptionResponse;
      setResult(data);
      setEditRows(data.segments);
      setState('done');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'ASR failed');
      setState('error');
    }
  }

  async function startRecording() {
    cleanupMedia();
    setResult(null);
    setError(null);
    setState('idle');
    chunksRef.current = [];
    try {
      const stream = await getUserMediaOrThrow({ audio: true });
      streamRef.current = stream;
      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.start(1000);
      setRecording(true);
      setRecordSecs(0);
      startMeter(stream);
    } catch (e) {
      cleanupMedia();
      setRecording(false);
      setError(describeMicrophoneIssue(t, toMicrophoneIssue(e)));
      setState('error');
    }
  }

  async function stopRecording() {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      await new Promise<void>((resolve) => {
        recorder.onstop = () => resolve();
        recorder.stop();
      });
    }
    const blob = new Blob(chunksRef.current, { type: chunksRef.current[0]?.type || 'audio/webm' });
    const recorded = new File([blob], 'live-session.webm', { type: blob.type || 'audio/webm' });
    cleanupMedia();
    setRecording(false);
    await setPlayableFile(recorded);
    await runTranscribe(recorded, liveProvider, liveLanguage, { diarize: true });
  }

  function cleanupMedia() {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
    setAudioLevel(0);
  }

  function startMeter(stream: MediaStream) {
    const ctx = getAudioContext();
    const src = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    src.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);
    const startedAt = Date.now();
    const loop = () => {
      analyser.getByteFrequencyData(data);
      const avg = data.reduce((sum, value) => sum + value, 0) / data.length;
      setAudioLevel(Math.min(100, Math.round((avg / 128) * 100)));
      setRecordSecs(Math.floor((Date.now() - startedAt) / 1000));
      rafRef.current = requestAnimationFrame(loop);
    };
    loop();
  }

  function getAudioContext() {
    if (!audioContextRef.current) audioContextRef.current = new AudioContext();
    return audioContextRef.current;
  }

  function playRange(start: number, end: number, key: string) {
    if (!audioBuffer) return;
    sourceRef.current?.stop();
    const ctx = getAudioContext();
    const src = ctx.createBufferSource();
    src.buffer = audioBuffer;
    src.connect(ctx.destination);
    const duration = Math.max(0.12, end - start);
    src.start(0, Math.max(0, start - 0.08), duration + 0.16);
    sourceRef.current = src;
    setActiveWordKey(key);
    setWordTooltip(null);
    window.setTimeout(() => setActiveWordKey(null), Math.ceil((duration + 0.16) * 1000));
  }

  function showWordTooltip(next: NonNullable<WordTooltipState>) {
    if (tooltipTimerRef.current !== null) {
      window.clearTimeout(tooltipTimerRef.current);
      tooltipTimerRef.current = null;
    }
    setWordTooltip(next);
  }

  function hideWordTooltip() {
    if (tooltipTimerRef.current !== null) window.clearTimeout(tooltipTimerRef.current);
    tooltipTimerRef.current = window.setTimeout(() => setWordTooltip(null), 220);
  }

  async function exportDocx() {
    if (!visibleSegments.length) return;
    const payload = {
      meta: {
        language: result?.language ?? '',
        duration: result?.duration ?? '',
        speakersCount: result?.speakersCount ?? '',
      },
      segments: visibleSegments.map((seg) => ({
        speaker: seg.speaker,
        time: `${seg.start} - ${seg.end}`,
        text: seg.text || segmentText(seg.words),
      })),
    };
    const response = await fetch(`${API_BASE}/api/asr/export/docx`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = t('asr.downloadFilename');
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="p-6 md:p-8 max-w-screen-2xl">
      <PageHeader title={t('asr.title')} subtitle={t('asr.subtitle')} />

      <div className="grid grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)] gap-5 items-start">
        <Card padding="none" className="overflow-hidden xl:sticky xl:top-20">
          <div className="grid grid-cols-3 border-b border-outline-soft bg-surface">
            <TabButton active={mode === 'upload'} onClick={() => setMode('upload')} icon={<UploadCloud className="h-4 w-4" />} label={t('asr.modeUpload')} />
            <TabButton active={mode === 'live'} onClick={() => setMode('live')} icon={<Mic className="h-4 w-4" />} label={t('asr.modeLive')} />
            <TabButton active={mode === 'local'} onClick={() => setMode('local')} icon={<Headphones className="h-4 w-4" />} label={t('asr.modeLocal')} />
          </div>

          <div className="p-4">
            {mode === 'upload' && (
              <div className="space-y-4">
                <DropZone file={file} title={t('asr.uploadDropzone')} subtitle={t('asr.uploadDropzoneSub')} onFile={(next) => void setPlayableFile(next)} />
                <ProviderSwitch value={uploadProvider} onChange={setUploadProvider} />
                <div className="grid grid-cols-[1fr_90px] gap-3">
                  <Field label={t('asr.languageLabel')}>
                    <input className={inputClass} value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="Uzbek, English..." />
                  </Field>
                  <Field label={t('asr.speakersLabel')}>
                    <input className={inputClass} value={speakers} onChange={(e) => setSpeakers(e.target.value)} placeholder={t('asr.speakersPlaceholder')} type="number" min={1} max={10} />
                  </Field>
                </div>
                <Button fullWidth disabled={!file || state === 'running'} leftIcon={state === 'running' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radio className="h-4 w-4" />} onClick={() => file && void runTranscribe(file, uploadProvider, language, { speakers, diarize: true })}>
                  {t('asr.analyze')}
                </Button>
              </div>
            )}

            {mode === 'live' && (
              <div className="space-y-4">
                <ProviderSwitch value={liveProvider} onChange={setLiveProvider} />
                <Field label={t('asr.languageLabel')}>
                  <input className={inputClass} value={liveLanguage} onChange={(e) => setLiveLanguage(e.target.value)} placeholder="Uzbek, English..." />
                </Field>
                {liveRecordingError && (
                  <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-body-md text-amber-800">
                    {liveRecordingError}
                  </div>
                )}
                <div className="rounded-lg border border-outline-soft bg-surface-container-low p-5 text-center">
                  <div className={cn('mx-auto h-16 w-16 rounded-full border inline-flex items-center justify-center mb-3', recording ? 'bg-error-container border-error text-error animate-pulse-dot' : 'bg-white border-outline-soft text-ink-muted')}>
                    {recording ? <Square className="h-6 w-6 fill-current" /> : <Mic className="h-7 w-7" />}
                  </div>
                  <AudioBars level={audioLevel} />
                  <p className="text-headline-md font-mono tabular-nums mt-3">{formatDuration(recordSecs)}</p>
                  <p className="text-body-md text-ink-muted mt-1">{t('asr.liveStopHint')}</p>
                  <div className="flex justify-center gap-3 mt-5">
                    {!recording ? (
                      <Button size="lg" disabled={Boolean(liveRecordingIssue)} leftIcon={<Mic className="h-4 w-4" />} onClick={() => void startRecording()}>{t('asr.liveStart')}</Button>
                    ) : (
                      <Button size="lg" variant="danger" leftIcon={<Square className="h-4 w-4 fill-current" />} onClick={() => void stopRecording()}>{t('asr.liveStop')}</Button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {mode === 'local' && (
              <div className="space-y-4">
                <LocalStatus health={localHealth} />
                <DropZone file={localFile} title={t('asr.localFileTitle')} subtitle={t('asr.localFileSub')} onFile={(next) => void setPlayableFile(next, true)} />
                <Field label={t('asr.languageLabel')}>
                  <select className={inputClass} value={localLanguage} onChange={(e) => setLocalLanguage(e.target.value)}>
                    {localLanguages.map((lang) => <option key={lang} value={lang}>{lang}</option>)}
                  </select>
                </Field>
                <div className="flex flex-wrap gap-4">
                  <label className="inline-flex items-center gap-2 text-body-md text-ink cursor-pointer">
                    <input className="accent-primary-500" type="checkbox" checked={localTimestamp} onChange={(e) => setLocalTimestamp(e.target.checked)} />
                    {t('asr.optionTimestamp')}
                  </label>
                  <label className="inline-flex items-center gap-2 text-body-md text-ink cursor-pointer">
                    <input className="accent-primary-500" type="checkbox" checked={localDiarize} onChange={(e) => setLocalDiarize(e.target.checked)} />
                    {t('asr.optionDiarization')}
                  </label>
                </div>
                <Button fullWidth disabled={!localFile || state === 'running'} leftIcon={state === 'running' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Headphones className="h-4 w-4" />} onClick={() => localFile && void runTranscribe(localFile, 'local', localLanguage, { diarize: localDiarize || localTimestamp })}>
                  {t('asr.analyze')}
                </Button>
              </div>
            )}

            {error && (
              <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 flex gap-2 text-body-md text-error">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span className="break-words">{error}</span>
              </div>
            )}
          </div>
        </Card>

        <main className="space-y-4 min-w-0">
          {!result && state !== 'running' && (
            <Card padding="lg" className="min-h-[520px] flex flex-col items-center justify-center text-center">
              <div className="h-14 w-14 rounded-full bg-surface-container text-ink-muted inline-flex items-center justify-center mb-4">
                <FileAudio className="h-7 w-7" />
              </div>
              <h2 className="text-headline-md text-ink">{t('asr.resultsEmptyTitle')}</h2>
              <p className="text-body-lg text-ink-muted mt-2">{t('asr.resultsEmptyBody')}</p>
            </Card>
          )}

          {state === 'running' && (
            <Card padding="none" className="overflow-hidden">
              <div className="flex items-center gap-3 px-5 py-4 bg-primary-50 border-b border-primary-200">
                <Loader2 className="h-5 w-5 text-primary-500 animate-spin shrink-0" />
                <div className="min-w-0">
                  <p className="text-title-lg font-semibold text-primary-700">{t('asr.status.finalProcessingTitle')}</p>
                  <p className="text-body-md text-primary-600 mt-0.5">{t('asr.status.finalProcessingBody')}</p>
                </div>
              </div>
              <div className="min-h-[260px] flex flex-col items-center justify-center text-center px-5 py-8">
                <Loader2 className="h-8 w-8 text-primary-500 animate-spin mb-4" />
                <h2 className="text-headline-md text-ink">{t('asr.processingTitle')}</h2>
                <p className="text-body-md text-ink-muted mt-2">{t('asr.processingBody')}</p>
              </div>
            </Card>
          )}

          {state === 'done' && result && (
            <Card padding="none" className="overflow-hidden">
              <div className="flex items-center gap-3 px-5 py-4 bg-emerald-50 border-b border-emerald-200">
                <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
                <div className="min-w-0">
                  <p className="text-title-lg font-semibold text-emerald-700">{t('asr.status.finalDoneTitle')}</p>
                  <p className="text-body-md text-emerald-600 mt-0.5">
                    {t('asr.status.finalDoneBody', { provider: result.provider ?? '-', model: result.model ?? '-', seconds: result.processingTimeS ?? 0 })}
                  </p>
                </div>
              </div>
            </Card>
          )}

          {state === 'error' && error && (
            <Card padding="none" className="overflow-hidden">
              <div className="flex items-center gap-3 px-5 py-4 bg-red-50 border-b border-red-200">
                <AlertCircle className="h-5 w-5 text-error shrink-0" />
                <div className="min-w-0">
                  <p className="text-title-lg font-semibold text-error">{t('asr.status.finalErrorTitle')}</p>
                  <p className="text-body-md text-error mt-0.5 break-words">{error}</p>
                </div>
              </div>
            </Card>
          )}

          {result && (
            <>
              <StatsBar stats={stats} result={result} />
              <Card padding="none" className="overflow-visible">
                <CardHeader className="mb-0 border-b border-outline-soft bg-white px-5 py-3">
                  <div className="flex flex-wrap items-center gap-3 min-w-0">
                    <CardTitle>{t('asr.transcriptTitle')}</CardTitle>
                    <SpeakerLegend segments={visibleSegments} />
                    <div className="flex gap-1">
                      <ConfidenceBadge label={t('asr.legend.low')} className="bg-red-50 border-red-200 text-error" />
                      <ConfidenceBadge label={t('asr.legend.mid')} className="bg-amber-50 border-amber-200 text-amber-700" />
                      <ConfidenceBadge label={t('asr.legend.high')} className="bg-emerald-50 border-emerald-200 text-emerald-600" />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant={editing ? 'primary' : 'secondary'} leftIcon={editing ? <Save className="h-4 w-4" /> : <Edit3 className="h-4 w-4" />} onClick={() => setEditing(!editing)}>
                      {editing ? t('asr.save') : t('asr.edit')}
                    </Button>
                    <Button size="sm" variant="secondary" leftIcon={<Download className="h-4 w-4" />} onClick={() => void exportDocx()}>
                      {t('asr.downloadDocx')}
                    </Button>
                  </div>
                </CardHeader>
                <TranscriptTable
                  segments={visibleSegments}
                  editing={editing}
                  onEdit={(next) => setEditRows(next)}
                  activeWordKey={activeWordKey}
                  canPlay={Boolean(audioBuffer)}
                  onPlay={playRange}
                  onWordHover={showWordTooltip}
                  onWordLeave={hideWordTooltip}
                />
              </Card>
            </>
          )}
        </main>
      </div>
      <FloatingWordTooltip
        tooltip={wordTooltip}
        onMouseEnter={() => {
          if (tooltipTimerRef.current !== null) window.clearTimeout(tooltipTimerRef.current);
        }}
        onMouseLeave={hideWordTooltip}
      />
    </div>
  );
}

function describeMicrophoneIssue(t: (key: string) => string, issue: MicrophoneIssue): string {
  switch (issue) {
    case 'secure_context_required':
      return t('asr.errors.secureContext');
    case 'media_devices_unavailable':
      return t('asr.errors.unsupported');
    case 'media_recorder_unavailable':
      return t('asr.errors.recorderUnsupported');
    case 'microphone_permission_denied':
      return t('asr.errors.permissionDenied');
    case 'microphone_not_found':
      return t('asr.errors.deviceMissing');
    case 'microphone_in_use':
      return t('asr.errors.deviceBusy');
    default:
      return t('asr.errors.unavailable');
  }
}

const inputClass = 'h-10 w-full rounded-md border border-outline-soft bg-surface px-3 text-body-md text-ink outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15';

function TabButton({ active, icon, label, onClick }: { active: boolean; icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className={cn('h-12 inline-flex items-center justify-center gap-2 border-b-2 text-body-md font-medium transition-colors', active ? 'border-primary-500 bg-white text-primary-600' : 'border-transparent text-ink-muted hover:bg-surface-container-low hover:text-ink')}>
      {icon}
      <span className="truncate">{label}</span>
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-mono text-ink-muted">{label}</span>
      {children}
    </label>
  );
}

function ProviderSwitch({ value, onChange }: { value: Provider; onChange: (value: Provider) => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-3">
      <span className="text-mono text-ink-muted">{t('asr.provider')}</span>
      <div className="inline-flex rounded-md border border-outline-soft bg-surface-container p-0.5">
        {(['openrouter', 'aistudio'] as Provider[]).map((provider) => (
          <button key={provider} type="button" onClick={() => onChange(provider)} className={cn('h-8 px-3 rounded text-caption font-medium transition-colors', value === provider ? 'bg-white text-primary-600 shadow-soft' : 'text-ink-muted hover:text-ink')}>
            {provider === 'openrouter' ? t('asr.providerOpenRouter') : t('asr.providerAiStudio')}
          </button>
        ))}
      </div>
    </div>
  );
}

function DropZone({ file, title, subtitle, onFile }: { file: File | null; title: string; subtitle: string; onFile: (file: File) => void }) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [drag, setDrag] = useState(false);
  return (
    <button
      type="button"
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        const next = e.dataTransfer.files[0];
        if (next) onFile(next);
      }}
      className={cn('w-full rounded-lg border-2 border-dashed p-7 text-center transition-colors', drag || file ? 'border-primary-500 bg-primary-50' : 'border-outline-soft bg-white hover:bg-surface-container-low')}
    >
      <UploadCloud className="mx-auto h-8 w-8 text-primary-500 mb-3" />
      <p className="text-body-md font-semibold text-ink">{file ? file.name : title}</p>
      <p className="text-caption text-ink-muted mt-1">{subtitle}</p>
      <p className="text-mono text-ink-muted mt-3">{t('asr.uploadFormats')}</p>
      <input ref={inputRef} type="file" accept="audio/*" hidden onChange={(e) => { const next = e.target.files?.[0]; if (next) onFile(next); }} />
    </button>
  );
}

function LocalStatus({ health }: { health: Record<string, unknown> | null }) {
  const { t } = useTranslation();
  const ok = health && String(health.status || health.state || '').toLowerCase() !== 'offline';
  return (
    <div className="flex flex-wrap gap-2">
      <Badge variant={ok ? 'success' : 'error'}>{ok ? t('asr.health.online') : t('asr.health.checking')}</Badge>
      <Badge variant="neutral">{t('asr.health.device')}: {String(health?.device || health?.runtime || '-')}</Badge>
      <Badge variant="neutral">{t('asr.health.diarization')}: {String(health?.diarization || health?.diarize || '-')}</Badge>
    </div>
  );
}

function AudioBars({ level }: { level: number }) {
  return (
    <div className="flex items-end justify-center gap-0.5 h-7">
      {Array.from({ length: 16 }).map((_, i) => {
        const lit = i < Math.round((level / 100) * 16);
        return <span key={i} className={cn('w-1 rounded-sm transition-all duration-75', lit ? (i > 12 ? 'bg-error' : i > 8 ? 'bg-amber-500' : 'bg-emerald-500') : 'bg-outline-soft')} style={{ height: `${25 + i * 4}%` }} />;
      })}
    </div>
  );
}

function StatsBar({ stats, result }: { stats: ReturnType<typeof computeStats>; result: ASRTranscriptionResponse }) {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
      <Stat label={t('asr.stats.speakers')} value={result.speakersCount} />
      <Stat label={t('asr.stats.words')} value={stats.words} />
      <Stat label={t('asr.stats.lowConfidence')} value={stats.low} danger />
      <Stat label={t('asr.stats.language')} value={result.language} />
      <Stat label={t('asr.stats.duration')} value={result.duration} />
      <Stat label={t('asr.stats.apiTime')} value={`${result.processingTimeS}s`} />
    </div>
  );
}

function Stat({ label, value, danger }: { label: string; value: string | number; danger?: boolean }) {
  return (
    <Card padding="sm" className="text-center">
      <strong className={cn('block text-headline-md font-mono tabular-nums', danger ? 'text-error' : 'text-primary-500')}>{value}</strong>
      <span className="text-mono text-ink-muted">{label}</span>
    </Card>
  );
}

function SpeakerLegend({ segments }: { segments: ASRSegment[] }) {
  const speakers = [...new Set(segments.map((s) => s.speaker))];
  return (
    <div className="flex flex-wrap gap-2">
      {speakers.map((speaker, index) => {
        const palette = PALETTE[index % PALETTE.length];
        return (
          <span key={speaker} className="inline-flex items-center gap-1.5 text-caption font-medium text-ink-muted">
            <span className={cn('h-2 w-2 rounded-full', palette.dot)} />
            {speaker}
          </span>
        );
      })}
    </div>
  );
}

function ConfidenceBadge({ label, className }: { label: string; className: string }) {
  return <span className={cn('inline-flex h-6 items-center rounded-full border px-2 text-caption font-mono font-semibold tabular-nums', className)}>{label}</span>;
}

function TranscriptTable({
  segments,
  editing,
  onEdit,
  activeWordKey,
  canPlay,
  onPlay,
  onWordHover,
  onWordLeave,
}: {
  segments: ASRSegment[];
  editing: boolean;
  onEdit: (segments: ASRSegment[]) => void;
  activeWordKey: string | null;
  canPlay: boolean;
  onPlay: (start: number, end: number, key: string) => void;
  onWordHover: (tooltip: NonNullable<WordTooltipState>) => void;
  onWordLeave: () => void;
}) {
  const { t } = useTranslation();
  function updateSegment(index: number, patch: Partial<ASRSegment>) {
    onEdit(segments.map((seg, i) => (i === index ? { ...seg, ...patch } : seg)));
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-surface-container-low border-y border-outline-soft">
          <tr>
            <th className="text-mono text-ink-muted h-10 px-4 text-left">{t('asr.columns.speaker')}</th>
            <th className="text-mono text-ink-muted h-10 px-4 text-left">{t('asr.columns.time')}</th>
            <th className="text-mono text-ink-muted h-10 px-4 text-left">{t('asr.columns.transcript')}</th>
            <th className="text-mono text-ink-muted h-10 px-4 text-left">{t('asr.columns.confidence')}</th>
          </tr>
        </thead>
        <tbody>
          {segments.map((seg, index) => {
            const palette = PALETTE[index % PALETTE.length];
            const avg = segmentConfidence(seg);
            return (
              <tr key={`${seg.id}-${index}`} className="border-b border-outline-soft last:border-0 align-top">
                <td className="px-4 py-4 w-36">
                  {editing ? (
                    <input className={cn(inputClass, 'h-8')} value={seg.speaker} onChange={(e) => updateSegment(index, { speaker: e.target.value })} />
                  ) : (
                    <span className={cn('inline-flex h-7 items-center rounded-full border px-2.5 text-caption font-semibold', palette.bg, palette.text, palette.border)}>{seg.speaker}</span>
                  )}
                </td>
                <td className="px-4 py-4 w-44 font-mono text-caption text-ink-muted tabular-nums">{seg.start} - {seg.end}</td>
                <td className="px-4 py-4 min-w-[360px] text-body-lg text-ink leading-8">
                  {editing ? (
                    <textarea className={cn(inputClass, 'h-24 py-2')} value={seg.text || segmentText(seg.words)} onChange={(e) => updateSegment(index, { text: e.target.value })} />
                  ) : (
                    <WordLine
                      seg={seg}
                      rowIndex={index}
                      activeWordKey={activeWordKey}
                      canPlay={canPlay}
                      onPlay={onPlay}
                      onWordHover={onWordHover}
                      onWordLeave={onWordLeave}
                    />
                  )}
                </td>
                <td className="px-4 py-4 w-28">
                  <ConfidenceMini value={avg} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function WordLine({
  seg,
  rowIndex,
  activeWordKey,
  canPlay,
  onPlay,
  onWordHover,
  onWordLeave,
}: {
  seg: ASRSegment;
  rowIndex: number;
  activeWordKey: string | null;
  canPlay: boolean;
  onPlay: (start: number, end: number, key: string) => void;
  onWordHover: (tooltip: NonNullable<WordTooltipState>) => void;
  onWordLeave: () => void;
}) {
  if (!seg.words.length) return <>{seg.text}</>;
  return (
    <>
      {seg.words.map((word, index) => {
        const key = `${rowIndex}-${index}`;
        const start = timestampToSeconds(word.start);
        const end = timestampToSeconds(word.end);
        return (
          <span key={key} className="inline-block">
            <button
              type="button"
              className={cn(
                'rounded px-0.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
                confidenceClass(word.confidence),
                activeWordKey === key && 'bg-primary-500 text-white',
              )}
              onMouseEnter={(event) => {
                const rect = event.currentTarget.getBoundingClientRect();
                onWordHover({
                  key,
                  word,
                  x: rect.left + rect.width / 2,
                  y: rect.top,
                  canPlay,
                  onPlay: () => onPlay(start, end, key),
                });
              }}
              onMouseLeave={onWordLeave}
              onFocus={(event) => {
                const rect = event.currentTarget.getBoundingClientRect();
                onWordHover({
                  key,
                  word,
                  x: rect.left + rect.width / 2,
                  y: rect.top,
                  canPlay,
                  onPlay: () => onPlay(start, end, key),
                });
              }}
              onBlur={onWordLeave}
              onClick={() => canPlay && onPlay(start, end, key)}
            >
              {word.word}
            </button>{' '}
          </span>
        );
      })}
    </>
  );
}

function FloatingWordTooltip({
  tooltip,
  onMouseEnter,
  onMouseLeave,
}: {
  tooltip: WordTooltipState;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}) {
  const { t } = useTranslation();
  if (!tooltip) return null;
  const pct = Math.round(tooltip.word.confidence * 100);
  const tooltipWidth = 260;
  const tooltipHeight = 172;
  const left = Math.min(Math.max(tooltip.x, 150), window.innerWidth - 150);
  const top = Math.min(
    Math.max(tooltip.y - tooltipHeight - 12, 96),
    window.innerHeight - tooltipHeight - 16,
  );
  return (
    <div
      className="fixed z-[9999] rounded-lg bg-navy-700 p-3 text-white shadow-floating"
      style={{ left, top, width: tooltipWidth, transform: 'translateX(-50%)' }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="block text-mono text-white/50">{t('asr.tooltip.confidenceLabel')}</span>
          <span className="block truncate text-body-md font-semibold mt-1">{tooltip.word.word}</span>
        </div>
        <span className="font-mono text-body-md tabular-nums text-white">{pct}%</span>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <span className="h-1.5 flex-1 rounded-full bg-white/15 overflow-hidden">
          <span
            className={cn('block h-full rounded-full', pct < 50 ? 'bg-error' : pct < 70 ? 'bg-amber-500' : 'bg-emerald-500')}
            style={{ width: `${pct}%` }}
          />
        </span>
      </div>
      <div className="mt-2 text-caption font-mono text-white/60 tabular-nums">
        {tooltip.word.start} - {tooltip.word.end}
      </div>
      <button
        type="button"
        disabled={!tooltip.canPlay}
        onClick={tooltip.onPlay}
        className="mt-3 inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-md bg-primary-500 px-2 text-caption font-semibold text-white transition-colors hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Volume2 className="h-3.5 w-3.5" />
        {t('asr.tooltip.playWord')}
      </button>
    </div>
  );
}

function ConfidenceMini({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="h-1.5 flex-1 rounded-full bg-outline-soft overflow-hidden min-w-10">
        <span className={cn('block h-full rounded-full', pct < 50 ? 'bg-error' : pct < 70 ? 'bg-amber-500' : 'bg-emerald-500')} style={{ width: `${pct}%` }} />
      </span>
      <span className="text-caption font-mono tabular-nums text-ink-muted">{pct}%</span>
    </div>
  );
}

function computeStats(result: ASRTranscriptionResponse | null) {
  const words = result?.segments.flatMap((seg) => seg.words) ?? [];
  return {
    words: words.length,
    low: words.filter((word) => word.confidence < 0.5).length,
  };
}

function normalizeLanguages(data: unknown): string[] {
  if (Array.isArray(data)) return data.map(String);
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>;
    const raw = obj.languages || obj.supported_languages || obj.supportedLanguages;
    if (Array.isArray(raw)) return raw.map(String);
  }
  return [];
}

function segmentText(words: ASRWord[]) {
  return words.map((word) => word.word).join(' ');
}

function segmentConfidence(seg: ASRSegment) {
  if (!seg.words.length) return 1;
  return seg.words.reduce((sum, word) => sum + word.confidence, 0) / seg.words.length;
}

function confidenceClass(value: number) {
  if (value < 0.5) return 'bg-red-50 border-b-2 border-red-400';
  if (value < 0.7) return 'bg-amber-50 border-b-2 border-amber-400';
  return 'hover:bg-surface-container';
}

function timestampToSeconds(ts: string) {
  const parts = String(ts).replace(',', '.').split(':').map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return 0;
}

function formatDuration(total: number) {
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function pickMimeType() {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) ?? '';
}
