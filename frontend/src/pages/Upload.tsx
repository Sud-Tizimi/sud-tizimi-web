/**
 * Upload page — Phase B.
 *
 * Drag-and-drop uploader with an optional "Attach to case" picker. When
 * the picker is empty, uploaded files become orphans and show up under
 * /documents; when a case is selected, the upload is attached in the
 * same round-trip.
 *
 * Auth: any logged-in user. The "All documents" tab in /documents is
 * judge-only.
 */
import { type DragEvent, useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import {
  Upload as UploadIcon,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Plus,
  ChevronRight,
  X,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  Button,
  EmptyState,
  Badge,
} from '@/components/ui';
import { cn } from '@/lib/cn';
import { useCases, useDocuments, useUploadDocument } from '@/hooks/queries';
import type { CaseDocument } from '@/types/domain';

const ALLOWED_EXT = ['pdf', 'docx', 'jpg', 'jpeg', 'png'] as const;
const MAX_BYTES = 25 * 1024 * 1024;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function pickFileType(name: string): 'pdf' | 'docx' | 'jpg' | 'png' | null {
  const ext = name.toLowerCase().split('.').pop() ?? '';
  if (ext === 'pdf') return 'pdf';
  if (ext === 'docx') return 'docx';
  if (ext === 'jpg' || ext === 'jpeg') return 'jpg';
  if (ext === 'png') return 'png';
  return null;
}

export function Upload() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: cases = [] } = useCases();
  const { data: recent = [] } = useDocuments('mine');
  const uploadMut = useUploadDocument();

  const [caseId, setCaseId] = useState<string>('');
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const [queuedFiles, setQueuedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      setError(null);
      const arr = Array.from(files);
      let rejected = 0;
      let tooLarge = 0;
      const accepted: File[] = [];

      for (const f of arr) {
        const ext = f.name.toLowerCase().split('.').pop() ?? '';
        if (!ALLOWED_EXT.includes(ext as (typeof ALLOWED_EXT)[number])) {
          rejected += 1;
          continue;
        }
        if (f.size > MAX_BYTES) {
          tooLarge += 1;
          continue;
        }
        if (pickFileType(f.name) === null) {
          rejected += 1;
          continue;
        }
        accepted.push(f);
      }

      if (accepted.length > 0) {
        setQueuedFiles((current) => {
          const seen = new Set(current.map(fileKey));
          const next = [...current];
          for (const file of accepted) {
            const key = fileKey(file);
            if (seen.has(key)) continue;
            seen.add(key);
            next.push(file);
          }
          return next;
        });
      }

      if (rejected > 0) {
        setError(t('upload.errors.badType'));
      } else if (tooLarge > 0) {
        setError(t('upload.errors.tooLarge'));
      }
    },
    [t],
  );

  const uploadQueuedFiles = useCallback(async () => {
    if (queuedFiles.length === 0 || busy > 0) return;

    setError(null);
    setToast(null);
    setBusy(queuedFiles.length);

    const uploaded = new Set<string>();
    let failed = 0;

    for (const file of queuedFiles) {
      try {
        await uploadMut.mutateAsync({ file, caseId: caseId || null });
        uploaded.add(fileKey(file));
      } catch {
        failed += 1;
      } finally {
        setBusy((b) => Math.max(0, b - 1));
      }
    }

    if (uploaded.size > 0) {
      setQueuedFiles((current) => current.filter((file) => !uploaded.has(fileKey(file))));
      setToast(t('upload.successCount', { count: uploaded.size }));
      setTimeout(() => setToast(null), 3000);
    }
    if (failed > 0) {
      setError(t('upload.errors.uploadFailed'));
    }
  }, [busy, caseId, queuedFiles, t, uploadMut]);

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) {
      addFiles(e.dataTransfer.files);
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-screen-xl">
      <PageHeader
        title={t('upload.title')}
        subtitle={t('upload.subtitle')}
        actions={
          <Button
            variant="secondary"
            size="md"
            onClick={() => navigate('/documents')}
          >
            {t('documents.title')}
            <ChevronRight className="h-4 w-4" />
          </Button>
        }
      />

      <Card padding="lg" className="mb-6">
        <CardHeader>
          <div>
            <CardTitle>{t('upload.title')}</CardTitle>
            <CardDescription>{t('upload.subtitle')}</CardDescription>
          </div>
        </CardHeader>

        {/* Case picker */}
        <div className="mb-4">
          <label className="text-caption font-medium text-ink mb-1.5 block">
            {t('upload.field.case')}
          </label>
          <select
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
            className="h-10 px-3 rounded-md border border-outline-soft bg-white text-body-md text-ink focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15 transition-colors w-full md:max-w-md"
          >
            <option value="">{t('upload.field.case.none')}</option>
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.caseNumber} — {c.citizenName}
              </option>
            ))}
          </select>
        </div>

        {/* Dropzone */}
        <div
          onDragEnter={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragOver={(e) => e.preventDefault()}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={cn(
            'rounded-md border-2 border-dashed transition-colors p-8 text-center',
            dragging
              ? 'border-primary-500 bg-primary-50/50'
              : 'border-outline-soft bg-surface-container-low',
          )}
        >
          <div className="inline-flex items-center justify-center h-12 w-12 rounded-md bg-primary-50 text-primary-500 mb-3">
            <UploadIcon className="h-6 w-6" />
          </div>
          <p className="text-body-lg text-ink mb-1">
            {dragging
              ? t('upload.dropzone.active')
              : t('upload.dropzone')}
          </p>
          <p className="text-caption text-ink-muted mb-4">
            PDF, DOCX, JPG, PNG — up to 25 MB per file
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.jpg,.jpeg,.png"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files) addFiles(e.target.files);
              e.target.value = '';
            }}
          />
          <Button
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={() => fileInputRef.current?.click()}
            disabled={busy > 0}
          >
            {busy > 0 ? t('upload.uploading', { count: busy }) : t('upload.field.addFiles')}
          </Button>
        </div>

        {queuedFiles.length > 0 && (
          <div className="mt-5 rounded-md border border-outline-soft bg-white overflow-hidden">
            <div className="px-4 py-3 border-b border-outline-soft flex items-center justify-between gap-3">
              <div>
                <p className="text-body-md font-medium text-ink">
                  {t('upload.queue.title', { count: queuedFiles.length })}
                </p>
                <p className="text-caption text-ink-muted">
                  {t('upload.queue.description')}
                </p>
              </div>
              <Button
                size="sm"
                variant="secondary"
                onClick={uploadQueuedFiles}
                disabled={busy > 0 || queuedFiles.length === 0}
              >
                {busy > 0 ? t('upload.uploading', { count: busy }) : t('upload.field.submit')}
              </Button>
            </div>
            <ul className="divide-y divide-outline-soft">
              {queuedFiles.map((file) => (
                <li key={fileKey(file)} className="px-4 py-3 flex items-center gap-3">
                  <div className="h-9 w-9 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center shrink-0">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-body-md font-medium text-ink truncate">{file.name}</p>
                    <p className="text-caption font-mono text-ink-muted">
                      {(pickFileType(file.name) ?? '').toUpperCase()} · {formatBytes(file.size)}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="h-8 w-8 rounded-md inline-flex items-center justify-center text-ink-muted hover:text-error hover:bg-red-50 transition-colors disabled:opacity-50"
                    onClick={() =>
                      setQueuedFiles((current) =>
                        current.filter((item) => fileKey(item) !== fileKey(file)),
                      )
                    }
                    disabled={busy > 0}
                    aria-label={t('upload.queue.remove')}
                  >
                    <X className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 flex items-start gap-2 text-body-md text-error"
          >
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {toast && (
          <div
            role="status"
            className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 flex items-start gap-2 text-body-md text-emerald-600"
          >
            <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
            <p>{toast}</p>
          </div>
        )}
      </Card>

      {/* Recent uploads */}
      <Card padding="none">
        <CardHeader className="px-6 pt-6">
          <div>
            <CardTitle>{t('upload.recent')}</CardTitle>
            <CardDescription>
              {recent.length} {t('upload.recent').toLowerCase()}
            </CardDescription>
          </div>
        </CardHeader>
        {recent.length === 0 ? (
          <EmptyState
            className="py-12"
            icon={<FileText className="h-5 w-5" />}
            title={t('documents.empty.title')}
            description={t('documents.empty.body')}
          />
        ) : (
          <ul className="flex flex-col divide-y divide-outline-soft -mx-6">
            {recent.slice(0, 10).map((doc) => (
              <RecentRow key={doc.id} doc={doc} />
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function fileKey(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function RecentRow({ doc }: { doc: CaseDocument }) {
  const { t } = useTranslation();
  return (
    <li className="flex items-center gap-4 px-6 py-3 hover:bg-surface-container-low">
      <div className="h-9 w-9 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center shrink-0">
        <FileText className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-body-md font-medium text-ink truncate">{doc.fileName}</p>
        <p className="text-caption font-mono text-ink-muted">
          {(doc.fileType as string).toUpperCase()} · {formatBytes(doc.size)} ·{' '}
          {t(`documentType.${doc.detectedType}`)} ({doc.aiConfidence}%) ·{' '}
          {format(new Date(doc.uploadedAt), 'yyyy-MM-dd HH:mm')}
        </p>
      </div>
      {doc.caseId ? (
        <Link
          to={`/cases/${doc.caseId}`}
          className="text-caption text-primary-600 hover:underline"
        >
          {t('documents.status.attached', { caseNumber: '…' })}
        </Link>
      ) : (
        <Badge variant="warning">{t('documents.status.orphan')}</Badge>
      )}
    </li>
  );
}
