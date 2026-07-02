/**
 * Documents library page — Phase B.
 *
 * Shows the current user's uploads, with a judges-only "All documents"
 * tab. Filters by status (orphan / attached), category, and free-text
 * filename search. Row actions: download, attach to case, detach, delete.
 */
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import {
  FileText,
  Download,
  Trash2,
  Link2,
  Link2Off,
  Inbox,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  Button,
  Badge,
  EmptyState,
} from '@/components/ui';
import { cn } from '@/lib/cn';
import { useAuth } from '@/hooks/useAuth';
import {
  useAttachDocument,
  useCases,
  useDeleteDocument,
  useDetachDocument,
  useDocuments,
} from '@/hooks/queries';
import type { CaseDocument, DocumentCategory } from '@/types/domain';

const PILL_TEXT_CLASS = 'normal-case tracking-normal';

type Scope = 'mine' | 'all';
type StatusFilter = 'all' | 'orphan' | 'attached';

const CATEGORIES: DocumentCategory[] = [
  'procedural',
  'participant',
  'evidence',
  'court',
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export function Documents() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { role } = useAuth();

  const [scope, setScope] = useState<Scope>('mine');
  const [status, setStatus] = useState<StatusFilter>('all');
  const [category, setCategory] = useState<DocumentCategory | 'all'>('all');
  const [search, setSearch] = useState('');

  // Judges may toggle to "all". Assistants get 403 from the backend; we
  // simply clamp the toggle off.
  const isJudge = role === 'judge';
  const effectiveScope: Scope = isJudge ? scope : 'mine';

  const { data: docs = [], isLoading } = useDocuments(effectiveScope);
  const { data: cases = [] } = useCases();
  const attachMut = useAttachDocument();
  const detachMut = useDetachDocument();
  const deleteMut = useDeleteDocument();

  const caseById = useMemo(() => {
    const m = new Map<string, string>();
    for (const c of cases) m.set(c.id, c.caseNumber);
    return m;
  }, [cases]);

  const filtered = useMemo(() => {
    let next = docs;
    if (status === 'orphan') next = next.filter((d) => d.caseId == null);
    if (status === 'attached') next = next.filter((d) => d.caseId != null);
    if (category !== 'all') next = next.filter((d) => d.category === category);
    if (search.trim()) {
      const needle = search.toLowerCase();
      next = next.filter((d) => d.fileName.toLowerCase().includes(needle));
    }
    return next;
  }, [docs, status, category, search]);

  return (
    <div className="p-6 md:p-8 max-w-screen-2xl">
      <PageHeader
        title={t('documents.title')}
        subtitle={t('documents.subtitle')}
        actions={
          <Button leftIcon={<FileText className="h-4 w-4" />} onClick={() => navigate('/upload')}>
            {t('upload.title')}
          </Button>
        }
      />

      {/* Scope tabs (judges only) */}
      {isJudge && (
        <div className="flex items-center gap-2 mb-4">
          {(['mine', 'all'] as Scope[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setScope(s)}
              className={cn(
                'inline-flex items-center h-8 px-3 rounded-full border text-caption font-medium transition-colors',
                scope === s
                  ? 'bg-primary-500 text-white border-primary-500'
                  : 'bg-white text-ink-muted border-outline-soft hover:border-outline hover:text-ink',
              )}
            >
              {s === 'mine' ? t('documents.scope.mine') : t('documents.scope.all')}
            </button>
          ))}
        </div>
      )}

      {/* Filters */}
      <Card padding="md" className="mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('documents.filter.search')}
            className="h-9 px-3 rounded-md border border-outline-soft bg-white text-body-md text-ink placeholder:text-ink-muted focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15 transition-colors flex-1 min-w-[200px]"
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as StatusFilter)}
            className="h-9 px-3 rounded-md border border-outline-soft bg-white text-body-md text-ink focus:outline-none focus:border-primary-500"
          >
            <option value="all">{t('documents.filter.status')}: all</option>
            <option value="orphan">{t('documents.status.orphan')}</option>
            <option value="attached">{t('documents.filter.status')}: attached</option>
          </select>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as DocumentCategory | 'all')}
            className="h-9 px-3 rounded-md border border-outline-soft bg-white text-body-md text-ink focus:outline-none focus:border-primary-500"
          >
            <option value="all">{t('documents.filter.category')}: all</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {t(`documentCategory.${c}`)}
              </option>
            ))}
          </select>
        </div>
      </Card>

      <Card padding="none">
        <CardHeader className="px-6 pt-6">
          <div>
            <CardTitle>{t('documents.title')}</CardTitle>
            <CardDescription>
              {isLoading
                ? t('common.loading')
                : filtered.length === 1
                  ? `1 ${t('documents.subtitle').toLowerCase()}`
                  : `${filtered.length} ${t('documents.subtitle').toLowerCase()}`}
            </CardDescription>
          </div>
        </CardHeader>

        {filtered.length === 0 && !isLoading ? (
          <EmptyState
            className="py-16"
            icon={<Inbox className="h-5 w-5" />}
            title={t('documents.empty.title')}
            description={t('documents.empty.body')}
            action={
              <Button onClick={() => navigate('/upload')}>
                {t('upload.title')}
              </Button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-outline-soft">
                  <th className="text-left text-mono text-ink-muted h-10 px-6 font-medium">
                    {t('documents.column.fileName')}
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium hidden md:table-cell">
                    {t('documents.column.size')}
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium hidden lg:table-cell">
                    {t('documents.filter.category')}
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium">
                    {t('documents.column.status')}
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium hidden sm:table-cell">
                    {t('documents.column.uploadedAt')}
                  </th>
                  <th className="text-right text-mono text-ink-muted h-10 px-6 font-medium">
                    {/* actions */}
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d) => (
                  <DocumentRow
                    key={d.id}
                    doc={d}
                    caseNumberLabel={d.caseId ? caseById.get(d.caseId) ?? d.caseId : null}
                    onDownload={() => downloadFile(d.id, d.fileName)}
                    onAttach={(caseId) => attachMut.mutate({ id: d.id, caseId })}
                    onDetach={() => detachMut.mutate(d.id)}
                    onDelete={() => {
                      if (window.confirm(t('documents.delete.confirm'))) {
                        deleteMut.mutate(d.id);
                      }
                    }}
                    pending={
                      attachMut.isPending ||
                      detachMut.isPending ||
                      deleteMut.isPending
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function DocumentRow({
  doc,
  caseNumberLabel,
  onDownload,
  onAttach,
  onDetach,
  onDelete,
  pending,
}: {
  doc: CaseDocument;
  caseNumberLabel: string | null;
  onDownload: () => void;
  onAttach: (caseId: string) => void;
  onDetach: () => void;
  onDelete: () => void;
  pending: boolean;
}) {
  const { t } = useTranslation();
  const { data: cases = [] } = useCases();
  return (
    <tr
      className={cn(
        'border-b border-outline-soft last:border-0 hover:bg-surface-container-low transition-colors',
        pending && 'opacity-60',
      )}
    >
      <td className="px-6 py-4">
        <div className="flex items-start gap-3 min-w-0">
          <div className="h-9 w-9 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center shrink-0">
            <FileText className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="text-body-md font-medium text-ink truncate">{doc.fileName}</p>
            <p className="text-caption font-mono text-ink-muted">
              {(doc.fileType as string).toUpperCase()} ·{' '}
              {t(`documentType.${doc.detectedType}`)} · {doc.aiConfidence}%
              {doc.uploaderName ? ` · ${doc.uploaderName}` : ''}
            </p>
          </div>
        </div>
      </td>
      <td className="px-3 py-4 text-body-md text-ink font-mono tabular-nums hidden md:table-cell">
        {formatBytes(doc.size)}
      </td>
      <td className="px-3 py-4 hidden lg:table-cell">
        <Badge variant="info" className={cn(PILL_TEXT_CLASS, 'max-w-[180px] rounded-xl')}>
          {t(`documentCategory.${doc.category}`)}
        </Badge>
      </td>
      <td className="px-3 py-4">
        {doc.caseId ? (
          <Badge variant="success" className={cn(PILL_TEXT_CLASS, 'max-w-[180px] rounded-xl')}>
            {t('documents.status.attached', { caseNumber: caseNumberLabel ?? '…' })}
          </Badge>
        ) : (
          <Badge variant="warning" className={PILL_TEXT_CLASS}>
            {t('documents.status.orphan')}
          </Badge>
        )}
      </td>
      <td className="px-3 py-4 text-caption font-mono text-ink-muted hidden sm:table-cell">
        {format(new Date(doc.uploadedAt), 'yyyy-MM-dd HH:mm')}
      </td>
      <td className="px-6 py-4 text-right">
        <div className="flex items-center justify-end gap-1">
          <button
            type="button"
            onClick={onDownload}
            aria-label={t('documents.action.download')}
            title={t('documents.action.download')}
            className="h-8 w-8 rounded-md text-ink-muted hover:text-ink hover:bg-surface-container inline-flex items-center justify-center transition-colors"
          >
            <Download className="h-4 w-4" />
          </button>
          {doc.caseId ? (
            <button
              type="button"
              onClick={onDetach}
              aria-label={t('documents.action.detach')}
              title={t('documents.action.detach')}
              className="h-8 w-8 rounded-md text-ink-muted hover:text-ink hover:bg-surface-container inline-flex items-center justify-center transition-colors"
            >
              <Link2Off className="h-4 w-4" />
            </button>
          ) : (
            <AttachPicker
              cases={cases}
              onPick={(caseId) => onAttach(caseId)}
            />
          )}
          <button
            type="button"
            onClick={onDelete}
            aria-label={t('documents.action.delete')}
            title={t('documents.action.delete')}
            className="h-8 w-8 rounded-md text-ink-muted hover:text-error hover:bg-error-container/40 inline-flex items-center justify-center transition-colors"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}

function AttachPicker({
  cases,
  onPick,
}: {
  cases: Array<{ id: string; caseNumber: string; citizenName: string }>;
  onPick: (caseId: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <select
      defaultValue=""
      onChange={(e) => {
        if (e.target.value) {
          onPick(e.target.value);
          e.target.value = '';
        }
      }}
      aria-label={t('documents.action.attach')}
      title={t('documents.action.attach')}
      className="h-8 px-2 rounded-md border border-outline-soft bg-white text-caption text-ink focus:outline-none focus:border-primary-500"
    >
      <option value="" disabled>
        <Link2 className="h-4 w-4 inline mr-1" />
        {t('documents.action.attach')}
      </option>
      {cases.map((c) => (
        <option key={c.id} value={c.id}>
          {c.caseNumber} — {c.citizenName}
        </option>
      ))}
    </select>
  );
}

/** Open the document download in a new tab. We can't use a plain
 * ``<a href>`` because the auth header must be attached — so we
 * fetch with the bearer token, then navigate to a blob URL. */
function downloadFile(id: string, fileName: string) {
  // Read the token from the store directly (we're outside React).
  // The api wrapper already injects Authorization; we just need to
  // convert the response into a blob URL.
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
        // Soft fail — server may have returned 410 for seeded files.
        // We just don't pop a download dialog in that case.
        window.alert('Download failed (seeded files have no on-disk bytes).');
      });
  });
}
