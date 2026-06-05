import { useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { format } from 'date-fns';
import {
  ArrowLeft,
  Send,
  CheckCircle2,
  Undo2,
  RotateCcw,
  FileText,
  FileSignature,
  Scale,
  Sparkles,
  Inbox,
  Trash2,
  Upload as UploadIcon,
  Plus,
  X,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardHeader, CardTitle, Button, EmptyState, Badge } from '@/components/ui';
import { CaseDocumentList } from '@/components/case-mgmt/CaseDocumentList';
import { DocumentPreview } from '@/components/case-mgmt/DocumentPreview';
import { CaseRightPanel } from '@/components/case-mgmt/CaseRightPanel';
import { CaseActionModal } from '@/components/case-mgmt/CaseActionModal';
import { useAuth } from '@/hooks/useAuth';
import {
  useApproveCase,
  useCase,
  useCaseDocuments,
  useDeleteDocument,
  useJudges,
  useReopenCase,
  useReturnCase,
  useSubmitCase,
  useUploadDocument,
  useAssistants,
  useActivity,
} from '@/hooks/queries';
import { CASE_STATUS_BADGE } from '@/lib/caseStyles';
import { cn } from '@/lib/cn';
import type { ActivityEvent } from '@/types/domain';

type Tab = 'documents' | 'timeline';

const ALLOWED_UPLOAD_EXT = ['pdf', 'docx', 'jpg', 'jpeg', 'png'] as const;
const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

export function CaseDetail() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { user, role } = useAuth();

  const { data: caseItem, isLoading: caseLoading, isError } = useCase(id ?? null);
  const { data: judges = [] } = useJudges();
  const { data: assistants = [] } = useAssistants();
  const { data: activity = [] } = useActivity(id ?? null);
  const { data: documents = [] } = useCaseDocuments(id ?? null);
  const deleteDocMut = useDeleteDocument();

  const submitMut = useSubmitCase(id ?? '');
  const approveMut = useApproveCase(id ?? '');
  const returnMut = useReturnCase(id ?? '');
  const reopenMut = useReopenCase(id ?? '');

  const [tab, setTab] = useState<Tab>('documents');
  const [modal, setModal] = useState<null | 'approve' | 'return'>(null);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  // Keep previewDoc in sync with the live `documents` array (TanStack Query
  // replaces the array on every refresh; we need the preview to follow the
  // same document, not a stale snapshot).
  const previewDoc = useMemo(
    () => (selectedDocId ? documents.find((d) => d.id === selectedDocId) ?? null : null),
    [selectedDocId, documents],
  );

  if (caseLoading) {
    return (
      <div className="p-6 md:p-8 max-w-screen-2xl">
        <EmptyState title={t('common.loading')} />
      </div>
    );
  }
  if (isError || !caseItem) {
    return (
      <div className="p-6 md:p-8 max-w-screen-2xl">
        <EmptyState
          icon={<Inbox className="h-5 w-5" />}
          title={t('common.noResults')}
          description={t('caseMgmt.list.subtitle')}
          action={
            <Button
              variant="secondary"
              leftIcon={<ArrowLeft className="h-4 w-4" />}
              onClick={() => navigate('/cases')}
            >
              {t('caseMgmt.detail.actions.backToList')}
            </Button>
          }
        />
      </div>
    );
  }

  const judge = judges.find((j) => j.id === caseItem.assignedJudgeId);
  const assistant = assistants.find((a) => a.id === caseItem.assistantId);

  // Permission gates
  const me = user?.id ?? '';
  const isAssistant = role === 'assistant';
  const isJudge = role === 'judge';
  const isAssistantOwner = isAssistant && caseItem.assistantId === me;
  const isJudgeOwner = isJudge && caseItem.assignedJudgeId === me;
  const canUploadDocuments = isAssistantOwner || isJudgeOwner;

  // Phase A: doc count is unknown on detail page (we only show seeded counts in
  // the list view). The submit guard ``documents.length > 0`` is satisfied by
  // the server's own state machine; on the client we keep the button enabled
  // for the same states as before.
  const canSubmit = isAssistantOwner && (caseItem.status === 'draft' || caseItem.status === 'returned');
  const canApprove = isJudgeOwner && caseItem.status === 'under_review';
  const canReturn = isJudgeOwner && (caseItem.status === 'under_review' || caseItem.status === 'approved');
  const canReopen = isJudgeOwner && (caseItem.status === 'returned' || caseItem.status === 'approved');

  const statusBadge = CASE_STATUS_BADGE[caseItem.status];

  return (
    <div className="p-6 md:p-8 max-w-screen-2xl">
      <PageHeader
        title={caseItem.citizenName}
        subtitle={`${caseItem.caseNumber} · ${t(`caseStatus.${caseItem.status}`)}`}
        actions={
          <div className="flex items-center gap-3 flex-wrap">
            <Button
              variant="ghost"
              size="md"
              leftIcon={<ArrowLeft className="h-4 w-4" />}
              onClick={() => navigate('/cases')}
            >
              {t('caseMgmt.detail.actions.backToList')}
            </Button>
            {canSubmit && (
              <Button
                size="md"
                leftIcon={<Send className="h-4 w-4" />}
                onClick={() => submitMut.mutate()}
                disabled={submitMut.isPending}
              >
                {t('caseMgmt.detail.actions.submit')}
              </Button>
            )}
            {canReopen && (
              <Button
                variant="secondary"
                size="md"
                leftIcon={<RotateCcw className="h-4 w-4" />}
                onClick={() => reopenMut.mutate()}
                disabled={reopenMut.isPending}
              >
                {t('caseMgmt.detail.actions.reopen')}
              </Button>
            )}
            {canReturn && (
              <Button
                variant="secondary"
                size="md"
                leftIcon={<Undo2 className="h-4 w-4" />}
                onClick={() => setModal('return')}
              >
                {t('caseMgmt.detail.actions.return')}
              </Button>
            )}
            {canApprove && (
              <Button
                size="md"
                leftIcon={<CheckCircle2 className="h-4 w-4" />}
                onClick={() => setModal('approve')}
              >
                {t('caseMgmt.detail.actions.approve')}
              </Button>
            )}
          </div>
        }
      />

      {/* Status banner */}
      <div
        className={cn(
          'rounded-md border p-4 mb-6 flex items-center gap-3',
          caseItem.status === 'approved' && 'border-emerald-200 bg-emerald-50',
          caseItem.status === 'returned' && 'border-red-200 bg-red-50',
          caseItem.status === 'under_review' && 'border-amber-200 bg-amber-50',
          caseItem.status === 'uploaded' && 'border-primary-100 bg-primary-50/30',
          caseItem.status === 'draft' && 'border-outline-soft bg-surface-container-low',
        )}
      >
        <Badge variant={statusBadge.variant}>{t(`caseStatus.${caseItem.status}`)}</Badge>
        <p className="text-body-md text-ink">
          {t(
            caseItem.status === 'approved'
              ? 'caseMgmt.detail.approvedBanner'
              : caseItem.status === 'returned'
                ? 'caseMgmt.detail.returnedBanner'
                : caseItem.status === 'under_review'
                  ? 'caseMgmt.detail.underReviewBanner'
                  : 'caseMgmt.detail.draftBanner',
          )}
        </p>
      </div>

      {/* 3-pane layout */}
      <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr_360px] gap-6">
        {/* LEFT — case info + documents */}
        <div className="flex flex-col gap-6 min-w-0">
          <Card padding="md">
            <CardHeader>
              <CardTitle>{t('caseMgmt.detail.info.caseNumber')}</CardTitle>
              <span className="text-mono text-ink-muted">{caseItem.caseNumber}</span>
            </CardHeader>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-body-md">
              <Pair label={t('caseMgmt.detail.info.citizen')}>{caseItem.citizenName}</Pair>
              <Pair label={t('caseMgmt.detail.info.judge')}>
                <span className="inline-flex items-center gap-1.5">
                  <Scale className="h-3.5 w-3.5 text-ink-muted" />
                  <span className="truncate">{judge?.fullName ?? caseItem.assignedJudgeId}</span>
                </span>
              </Pair>
              <Pair label={t('caseMgmt.detail.info.assistant')}>
                <span className="inline-flex items-center gap-1.5">
                  <FileSignature className="h-3.5 w-3.5 text-ink-muted" />
                  <span className="truncate">{assistant?.fullName ?? caseItem.assistantId}</span>
                </span>
              </Pair>
              <Pair label={t('caseMgmt.detail.info.created')}>
                <span className="font-mono tabular-nums text-ink-muted">
                  {format(new Date(caseItem.createdAt), 'yyyy-MM-dd HH:mm')}
                </span>
              </Pair>
              <Pair label={t('caseMgmt.detail.info.updated')}>
                <span className="font-mono tabular-nums text-ink-muted">
                  {format(new Date(caseItem.updatedAt), 'yyyy-MM-dd HH:mm')}
                </span>
              </Pair>
              <Pair label={t('caseMgmt.detail.documents.title')}>
                <span className="font-mono tabular-nums text-ink">
                  {documents.length}
                </span>
              </Pair>
            </dl>
            {caseItem.returnReason && (
              <div className="mt-4 pt-4 border-t border-outline-soft">
                <p className="text-mono text-error mb-1">Return reason</p>
                <p className="text-body-md text-ink leading-relaxed">
                  {caseItem.returnReason}
                </p>
              </div>
            )}
            <div className="mt-4 pt-4 border-t border-outline-soft">
              <p className="text-mono text-ink-muted mb-1">
                {t('caseMgmt.detail.info.description')}
              </p>
              <p className="text-body-md text-ink leading-relaxed">
                {caseItem.description}
              </p>
            </div>
          </Card>

          <Card padding="md">
            <CardHeader>
              <div>
                <CardTitle className="inline-flex items-center gap-2">
                  <FileText className="h-4 w-4 text-ink-muted" />
                  {t('caseMgmt.detail.documents.title')}
                </CardTitle>
                <p className="text-body-md text-ink-muted mt-0.5">
                  {t('caseMgmt.detail.documents.count', { count: documents.length })}
                </p>
              </div>
            </CardHeader>

            <Tabs tab={tab} setTab={setTab} t={t} />

            {tab === 'documents' ? (
              <>
                {canUploadDocuments && (
                  <InlineUpload caseId={caseItem.id} />
                )}
                <div className="mt-3">
                  <CaseDocumentList
                    caseId={caseItem.id}
                    documents={documents}
                    selectedId={selectedDocId}
                    onSelect={setSelectedDocId}
                  />
                </div>
                {documents.length > 0 && (
                  <div className="mt-3 flex items-center justify-end gap-2">
                    {previewDoc && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => downloadFileForToken(previewDoc.id, previewDoc.fileName)}
                      >
                        Download
                      </Button>
                    )}
                    {previewDoc && isAssistantOwner && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          if (window.confirm(t('documents.delete.confirm'))) {
                            deleteDocMut.mutate(previewDoc.id);
                            setSelectedDocId(null);
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-error" />
                        {t('documents.action.delete')}
                      </Button>
                    )}
                  </div>
                )}
              </>
            ) : null}

            {tab === 'timeline' ? (
              <div className="xl:hidden">
                <CaseRightPanel
                  caseItem={caseItem}
                  selectedDoc={previewDoc}
                  activity={activity}
                />
              </div>
            ) : null}
          </Card>
        </div>

        {/* CENTER — preview */}
        <div className="min-w-0 min-h-[640px]">
          <Card padding="none" className="h-full flex flex-col">
            <CardHeader className="px-4 pt-4">
              <div>
                <CardTitle className="inline-flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary-500" />
                  {previewDoc
                    ? t('caseMgmt.detail.documents.aiPanelTitle')
                    : t('caseMgmt.detail.documents.previewEmpty')}
                </CardTitle>
                {previewDoc && (
                  <p className="text-caption font-mono text-ink-muted mt-0.5">
                    {previewDoc.fileName}
                  </p>
                )}
              </div>
            </CardHeader>
            <div className="flex-1 px-4 pb-4 min-h-0">
              <DocumentPreview document={previewDoc} />
            </div>
          </Card>
        </div>

        {/* RIGHT — AI + timeline */}
        <div className="min-w-0">
          <Card padding="md">
            <CaseRightPanel
              caseItem={caseItem}
              selectedDoc={previewDoc}
              activity={activity}
            />
          </Card>
        </div>
      </div>

      <CaseActionModal
        open={modal === 'approve'}
        variant="approve"
        onClose={() => setModal(null)}
        onConfirm={() => {
          approveMut.mutate();
          setModal(null);
        }}
      />
      <CaseActionModal
        open={modal === 'return'}
        variant="return"
        onClose={() => setModal(null)}
        onConfirm={(reason) => {
          returnMut.mutate(reason);
          setModal(null);
        }}
      />
    </div>
  );
}

function Pair({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-mono text-ink-muted">{label}</dt>
      <dd className="text-body-md text-ink mt-0.5 truncate">{children}</dd>
    </div>
  );
}

/** Inline download that attaches the bearer token. Mirrors the helper in
 * /pages/Documents.tsx; we duplicate it here to keep the two routes
 * independent. */
function downloadFileForToken(id: string, fileName: string) {
  import('@/stores/authStore').then(({ useAuthStore }) => {
    const token = useAuthStore.getState().token;
    if (!token) {
      window.location.assign('/login');
      return;
    }
    fetch(`/api/documents/${id}/download`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        if (!r.ok) throw new Error('download_failed');
        const blob = await r.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      })
      .catch(() => {
        window.alert('Download failed (seeded files have no on-disk bytes).');
      });
  });
}

function Tabs({
  tab,
  setTab,
  t,
}: {
  tab: Tab;
  setTab: (t: Tab) => void;
  t: (k: string) => string;
}) {
  return (
    <div className="flex items-center gap-1 mb-4 -mx-1 border-b border-outline-soft">
      {(['documents', 'timeline'] as Tab[]).map((tt) => {
        const active = tab === tt;
        return (
          <button
            key={tt}
            type="button"
            onClick={() => setTab(tt)}
            className={cn(
              'h-9 px-3 -mb-px border-b-2 text-caption font-medium transition-colors',
              active
                ? 'border-primary-500 text-ink'
                : 'border-transparent text-ink-muted hover:text-ink',
            )}
          >
            {t(`caseMgmt.detail.tabs.${tt}`)}
          </button>
        );
      })}
    </div>
  );
}

// Local ActivityEvent type re-export so the unused import doesn't trip
// TypeScript (we re-import the type via the queries hook already).
export type _CaseDetailActivityEvent = ActivityEvent;

// ---------------------------------------------------------------------------
// InlineUpload — case-scoped queue that posts files to /api/cases/{id}/documents.
// We render this above the doc list on the case detail page when the
// assistant owns the case and it's in a state that accepts new docs
// (draft / returned).
// ---------------------------------------------------------------------------
function InlineUpload({ caseId }: { caseId: string }) {
  const { t } = useTranslation();
  const uploadMut = useUploadDocument();
  const [busy, setBusy] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [queuedFiles, setQueuedFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const addFiles = (files: FileList | File[]) => {
    setErr(null);
    const accepted: File[] = [];
    let badType = false;
    let tooLarge = false;

    for (const file of Array.from(files)) {
      const ext = file.name.toLowerCase().split('.').pop() ?? '';
      if (!ALLOWED_UPLOAD_EXT.includes(ext as (typeof ALLOWED_UPLOAD_EXT)[number])) {
        badType = true;
        continue;
      }
      if (file.size > MAX_UPLOAD_BYTES) {
        tooLarge = true;
        continue;
      }
      accepted.push(file);
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

    if (badType) setErr(t('upload.errors.badType'));
    else if (tooLarge) setErr(t('upload.errors.tooLarge'));
  };

  const uploadQueue = async () => {
    if (queuedFiles.length === 0 || busy > 0) return;
    setErr(null);
    setBusy(queuedFiles.length);
    const uploaded = new Set<string>();
    let failed = 0;

    for (const file of queuedFiles) {
      try {
        await uploadMut.mutateAsync({ file, caseId });
        uploaded.add(fileKey(file));
      } catch {
        failed += 1;
      } finally {
        setBusy((count) => Math.max(0, count - 1));
      }
    }

    if (uploaded.size > 0) {
      setQueuedFiles((current) => current.filter((file) => !uploaded.has(fileKey(file))));
    }
    if (failed > 0) {
      setErr(t('upload.errors.uploadFailed'));
    }
  };

  return (
    <div className="rounded-md border border-outline-soft bg-surface-container-low p-3">
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.jpg,.jpeg,.png"
        multiple
        className="hidden"
        onChange={(e) => {
          const files = e.target.files;
          e.target.value = '';
          if (files?.length) addFiles(files);
        }}
      />
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-body-md font-medium text-ink inline-flex items-center gap-2">
            <UploadIcon className="h-4 w-4 text-primary-500" />
            {t('caseMgmt.detail.documents.upload.cta')}
          </p>
          <p className="text-caption text-ink-muted">
            PDF, DOCX, JPG, PNG — 25 MB
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            variant="secondary"
            leftIcon={<Plus className="h-4 w-4" />}
            disabled={busy > 0}
            onClick={() => inputRef.current?.click()}
          >
            {t('upload.field.addFiles')}
          </Button>
          {queuedFiles.length > 0 && (
            <Button size="sm" disabled={busy > 0} onClick={uploadQueue}>
              {busy > 0 ? t('upload.uploading', { count: busy }) : t('upload.field.submit')}
            </Button>
          )}
        </div>
      </div>
      {queuedFiles.length > 0 && (
        <ul className="mt-3 divide-y divide-outline-soft rounded-md border border-outline-soft bg-white overflow-hidden">
          {queuedFiles.map((file) => (
            <li key={fileKey(file)} className="flex items-center gap-3 px-3 py-2">
              <FileText className="h-4 w-4 text-primary-500 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-body-md font-medium text-ink truncate">{file.name}</p>
                <p className="text-caption font-mono text-ink-muted">
                  {formatBytes(file.size)}
                </p>
              </div>
              <button
                type="button"
                className="h-8 w-8 rounded-md inline-flex items-center justify-center text-ink-muted hover:text-error hover:bg-red-50 transition-colors disabled:opacity-50"
                aria-label={t('upload.queue.remove')}
                disabled={busy > 0}
                onClick={() =>
                  setQueuedFiles((current) =>
                    current.filter((item) => fileKey(item) !== fileKey(file)),
                  )
                }
              >
                <X className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
      {err && (
        <p className="text-caption text-error mt-2">{err}</p>
      )}
    </div>
  );
}

function fileKey(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}
