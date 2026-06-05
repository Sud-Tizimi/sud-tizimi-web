import { useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  CheckCircle2,
  Copy,
  Download,
  FileSearch,
  Loader2,
  RotateCcw,
  ScanLine,
  UploadCloud,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  Badge,
  Button,
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
} from '@/components/ui';
import { cn } from '@/lib/cn';
import {
  useOcrEngine,
  useOcrProcessDocument,
  useOcrProcessImage,
  type OcrProcessResponse,
  type OcrResult,
} from '@/hooks/queries';

type JobStatus = 'completed' | 'processing' | 'failed';

interface OcrJob {
  id: string;
  fileName: string;
  status: JobStatus;
  date: string;
  engine: string;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024;
const IMAGE_TYPES = new Set(['png', 'jpg', 'jpeg', 'webp', 'tif', 'tiff', 'bmp']);
const SUPPORTED_TYPES = new Set([
  ...IMAGE_TYPES,
  'pdf',
  'docx',
  'xlsx',
  'pptx',
  'txt',
  'rtf',
]);

function getExtension(file: File): string {
  return file.name.split('.').pop()?.toLowerCase() ?? '';
}

function resultFromProcess(data: OcrProcessResponse | null): OcrResult[] {
  return data?.pages ?? [];
}

function downloadText(fileName: string, text: string): void {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${fileName.replace(/\.[^.]+$/, '') || 'ocr'}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

export function OcrProcessing() {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [lang, setLang] = useState('uzb+rus+eng');
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [imageResult, setImageResult] = useState<OcrResult | null>(null);
  const [docResult, setDocResult] = useState<OcrProcessResponse | null>(null);
  const [jobs, setJobs] = useState<OcrJob[]>([]);

  const engineQuery = useOcrEngine();
  const imageMutation = useOcrProcessImage();
  const documentMutation = useOcrProcessDocument();
  const isProcessing = imageMutation.isPending || documentMutation.isPending;
  const pages = imageResult ? [imageResult] : resultFromProcess(docResult);
  const combinedText = pages.map((page) => page.text).filter(Boolean).join('\n\n');
  const confidence = pages.length
    ? Math.round((pages.reduce((sum, page) => sum + page.confidence, 0) / pages.length) * 100)
    : 0;
  const wordCount = useMemo(
    () => combinedText.trim().split(/\s+/).filter(Boolean).length,
    [combinedText],
  );
  const activeEngine = pages[0]?.engine ?? engineQuery.data?.active_engine ?? 'ocr';

  function acceptFile(nextFile: File): void {
    const ext = getExtension(nextFile);
    if (nextFile.size > MAX_FILE_SIZE) {
      setError(t('ocr.errors.tooLarge'));
      return;
    }
    if (!SUPPORTED_TYPES.has(ext)) {
      setError(t('ocr.errors.badType'));
      return;
    }
    setFile(nextFile);
    setError(null);
    setCopied(false);
  }

  async function startProcessing(): Promise<void> {
    if (!file) return;
    const ext = getExtension(file);
    const jobId = `${file.name}-${Date.now()}`;
    const baseJob = {
      id: jobId,
      fileName: file.name,
      status: 'processing' as JobStatus,
      date: new Date().toLocaleString(),
      engine: activeEngine,
    };
    setJobs((prev) => [baseJob, ...prev].slice(0, 5));
    setError(null);
    setImageResult(null);
    setDocResult(null);

    try {
      if (IMAGE_TYPES.has(ext)) {
        const result = await imageMutation.mutateAsync({ file, lang });
        setImageResult(result);
        setJobs((prev) =>
          prev.map((job) =>
            job.id === jobId ? { ...job, status: 'completed', engine: result.engine } : job,
          ),
        );
      } else {
        const result = await documentMutation.mutateAsync({ file, lang });
        setDocResult(result);
        setJobs((prev) =>
          prev.map((job) =>
            job.id === jobId
              ? { ...job, status: 'completed', engine: result.pages[0]?.engine ?? result.parser }
              : job,
          ),
        );
      }
    } catch {
      setError(t('ocr.errors.processingFailed'));
      setJobs((prev) =>
        prev.map((job) => (job.id === jobId ? { ...job, status: 'failed' } : job)),
      );
    }
  }

  function reset(): void {
    setFile(null);
    setError(null);
    setCopied(false);
    setImageResult(null);
    setDocResult(null);
    imageMutation.reset();
    documentMutation.reset();
  }

  async function copyText(): Promise<void> {
    if (!combinedText) return;
    await navigator.clipboard.writeText(combinedText);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <div className="p-6 md:p-8 max-w-screen-2xl">
      <PageHeader
        title={t('ocr.title')}
        subtitle={t('ocr.subtitle')}
        actions={
          <Badge variant={engineQuery.data?.real_engine ? 'success' : 'warning'}>
            {engineQuery.data?.real_engine ? t('ocr.engineOnline') : t('ocr.engineOffline')}
          </Badge>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)_360px]">
        <Card padding="lg" className="min-h-[560px]">
          <CardHeader>
            <div>
              <CardTitle>{t('ocr.dropzone')}</CardTitle>
              <CardDescription>{t('ocr.formats')}</CardDescription>
            </div>
          </CardHeader>

          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const next = e.dataTransfer.files.item(0);
              if (next) acceptFile(next);
            }}
            className={cn(
              'w-full min-h-[220px] rounded-lg border-2 border-dashed border-outline-soft bg-court-50/60 px-6 text-center transition-colors',
              'hover:border-primary-500 hover:bg-primary-50 focus:outline-none focus:ring-2 focus:ring-primary-500/20',
            )}
          >
            <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-md bg-primary-500 text-white">
              <UploadCloud className="h-7 w-7" />
            </span>
            <span className="block text-title-lg text-ink">{file?.name ?? t('ocr.dropzoneSub')}</span>
            <span className="mt-2 block text-body-md text-ink-muted">{t('ocr.formats')}</span>
          </button>
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            accept=".pdf,.docx,.xlsx,.pptx,.txt,.rtf,.png,.jpg,.jpeg,.webp,.tif,.tiff,.bmp"
            onChange={(e) => {
              const next = e.target.files?.[0];
              if (next) acceptFile(next);
            }}
          />

          <label className="mt-5 block text-caption font-medium text-ink-muted">
            {t('ocr.language')}
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value)}
              className="mt-2 h-10 w-full rounded-md border border-outline-soft bg-white px-3 text-body-md text-ink focus:border-primary-500 focus:outline-none"
            >
              <option value="uzb+rus+eng">UZ + RU + EN</option>
              <option value="uzb">UZ</option>
              <option value="rus">RU</option>
              <option value="eng">EN</option>
            </select>
          </label>

          {error && (
            <div className="mt-4 flex gap-3 rounded-md border border-red-200 bg-red-50 p-3 text-body-md text-red-700">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="mt-5 flex flex-wrap gap-3">
            <Button
              leftIcon={isProcessing ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanLine className="h-4 w-4" />}
              disabled={!file || isProcessing}
              onClick={startProcessing}
            >
              {isProcessing ? t('ocr.controls.downloading') : t('ocr.controls.start')}
            </Button>
            <Button variant="secondary" leftIcon={<RotateCcw className="h-4 w-4" />} onClick={reset}>
              {t('ocr.controls.reset')}
            </Button>
          </div>
        </Card>

        <Card padding="none" className="min-h-[560px] overflow-hidden">
          <div className="border-b border-outline-soft px-6 py-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle>{t('ocr.result.title')}</CardTitle>
                <CardDescription>
                  {pages.length > 0
                    ? `${t('ocr.result.confidence', { percent: confidence })} · ${t('ocr.result.wordCount', { count: wordCount })}`
                    : t('ocr.empty.body')}
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" leftIcon={<Copy className="h-4 w-4" />} disabled={!combinedText} onClick={copyText}>
                  {copied ? t('ocr.result.copied') : t('ocr.result.copy')}
                </Button>
                <Button
                  variant="secondary"
                  leftIcon={<Download className="h-4 w-4" />}
                  disabled={!combinedText}
                  onClick={() => downloadText(file?.name ?? 'ocr', combinedText)}
                >
                  {t('ocr.result.download')}
                </Button>
              </div>
            </div>
          </div>

          {isProcessing ? (
            <div className="flex min-h-[420px] items-center justify-center text-indigo-700">
              <Loader2 className="mr-3 h-6 w-6 animate-spin" />
              <span className="text-title-lg">{t('ocr.status.processing')}</span>
            </div>
          ) : pages.length === 0 ? (
            <EmptyState
              className="min-h-[420px]"
              icon={<FileSearch className="h-5 w-5" />}
              title={t('ocr.empty.title')}
              description={t('ocr.empty.body')}
            />
          ) : (
            <div className="max-h-[520px] overflow-y-auto px-6 py-5">
              <div className="mb-4 flex items-center gap-2 text-emerald-700">
                <CheckCircle2 className="h-5 w-5" />
                <span className="text-body-md font-medium">{t('ocr.status.completed')}</span>
              </div>
              {pages.map((page, index) => (
                <section key={`${page.page_number}-${index}`} className="mb-5 last:mb-0">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <Badge variant="info">
                      {t('ocr.result.pageOf', { current: page.page_number || index + 1, total: pages.length })}
                    </Badge>
                    <span className="text-caption text-ink-muted">
                      {t('ocr.result.engine', { engine: page.engine })}
                    </span>
                  </div>
                  <pre className="whitespace-pre-wrap rounded-md bg-court-50 p-4 text-body-md leading-7 text-ink">
                    {page.text || t('ocr.result.noText')}
                  </pre>
                </section>
              ))}
            </div>
          )}
        </Card>

        <Card padding="none" className="min-h-[560px] overflow-hidden">
          <div className="border-b border-outline-soft px-6 py-5">
            <CardTitle>{t('ocr.history.title')}</CardTitle>
            <CardDescription>
              {t('ocr.engineBadge', { engine: activeEngine })}
            </CardDescription>
          </div>
          {jobs.length === 0 ? (
            <EmptyState
              className="min-h-[420px]"
              icon={<ScanLine className="h-5 w-5" />}
              title={t('ocr.history.title')}
              description={t('ocr.history.empty')}
            />
          ) : (
            <div className="divide-y divide-outline-soft">
              {jobs.map((job) => (
                <div key={job.id} className="px-6 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-body-md font-medium text-ink">{job.fileName}</p>
                      <p className="mt-1 text-caption text-ink-muted">{job.date}</p>
                    </div>
                    <JobBadge status={job.status} />
                  </div>
                  <p className="mt-2 text-caption text-ink-muted">
                    {t('ocr.history.columnEngine')}: {job.engine}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function JobBadge({ status }: { status: JobStatus }) {
  const { t } = useTranslation();
  if (status === 'processing') {
    return (
      <Badge variant="info">
        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
        {t('ocr.history.status.processing')}
      </Badge>
    );
  }
  if (status === 'failed') {
    return <Badge variant="error">{t('ocr.history.status.failed')}</Badge>;
  }
  return <Badge variant="success">{t('ocr.history.status.completed')}</Badge>;
}
