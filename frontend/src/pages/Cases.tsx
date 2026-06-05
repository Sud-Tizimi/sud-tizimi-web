import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { format, formatDistanceToNow } from 'date-fns';
import { Scale, FileSignature, Gavel, Plus, Inbox, Pencil, Trash } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardDescription, Button, Badge, EmptyState, IconButton } from '@/components/ui';
import { useCases, useDeleteCase, useJudges, useAssistants } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import { CASE_STATUS_BADGE } from '@/lib/caseStyles';
import { cn } from '@/lib/cn';
import type { Case, CaseStatus } from '@/types/domain';

type StatusFilter = 'all' | CaseStatus;

const STATUS_FILTER_KEYS: Record<StatusFilter, string> = {
  all: 'caseMgmt.list.filterAll',
  draft: 'caseStatus.draft',
  uploaded: 'caseStatus.uploaded',
  under_review: 'caseStatus.under_review',
  approved: 'caseStatus.approved',
  returned: 'caseStatus.returned',
};

export function Cases() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { role, user } = useAuth();
  const userId = user?.id ?? '';
  const { data: cases = [], isLoading } = useCases();
  const { data: judges = [] } = useJudges();
  const { data: assistants = [] } = useAssistants();
  const deleteMut = useDeleteCase();
  const [filter, setFilter] = useState<StatusFilter>('all');

  // Server already scopes (judges see their assigned, assistants see their own),
  // so we don't re-filter by user id — we just apply the status chip filter.
  const filtered = useMemo(() => {
    let next = cases;
    if (filter !== 'all') {
      next = next.filter((c) => c.status === filter);
    }
    return next;
  }, [cases, filter]);

  // Doc count per case — Phase A doesn't expose /api/cases/{id}/documents
  // yet. We show the seeded 12 docs distributed as in the mock for the demo;
  // Phase B will replace this with a real count.
  const docCount = (caseId: string) => SEEDED_DOC_COUNTS[caseId] ?? 0;

  const filterOptions: StatusFilter[] = [
    'all',
    'draft',
    'uploaded',
    'under_review',
    'returned',
    'approved',
  ];

  const judgeName = (id: string) => judges.find((j) => j.id === id)?.fullName ?? id;
  const assistantName = (id: string) =>
    assistants.find((a) => a.id === id)?.fullName ?? id;

  return (
    <div className="p-6 md:p-8 max-w-screen-2xl">
      <PageHeader
        title={t('caseMgmt.list.title')}
        subtitle={t('caseMgmt.list.subtitle')}
        actions={
          role === 'assistant' ? (
            <Button
              size="md"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => navigate('/cases/new')}
            >
              {t('caseMgmt.list.newCase')}
            </Button>
          ) : null
        }
      />

      {/* Status filter chips */}
      <div className="flex flex-wrap items-center gap-2 mb-6">
        <span className="text-mono text-ink-muted mr-2">
          {t('caseMgmt.list.filterStatus')}
        </span>
        {filterOptions.map((opt) => {
          const active = filter === opt;
          return (
            <button
              key={opt}
              type="button"
              onClick={() => setFilter(opt)}
              className={cn(
                'inline-flex items-center h-8 px-3 rounded-full border text-caption font-medium transition-colors',
                active
                  ? 'bg-primary-500 text-white border-primary-500'
                  : 'bg-white text-ink-muted border-outline-soft hover:border-outline hover:text-ink',
              )}
            >
              {t(STATUS_FILTER_KEYS[opt])}
            </button>
          );
        })}
      </div>

      <Card padding="none">
        <CardHeader className="px-6 pt-6">
          <div>
            <CardTitle>{t('caseMgmt.list.filterMine')}</CardTitle>
            <CardDescription>
              {isLoading
                ? t('common.loading')
                : filtered.length === 1
                  ? `1 ${t('caseMgmt.list.subtitle').toLowerCase()}`
                  : `${filtered.length} ${t('caseMgmt.list.subtitle').toLowerCase()}`}
            </CardDescription>
          </div>
        </CardHeader>

        {filtered.length === 0 && !isLoading ? (
          <EmptyState
            className="py-16"
            icon={<Inbox className="h-5 w-5" />}
            title={
              role === 'judge' ? t('caseMgmt.list.emptyJudge') : t('caseMgmt.list.emptyAssistant')
            }
            description={t('caseMgmt.list.subtitle')}
            action={
              role === 'assistant' ? (
                <Button
                  size="md"
                  leftIcon={<Plus className="h-4 w-4" />}
                  onClick={() => navigate('/cases/new')}
                >
                  {t('caseMgmt.list.newCase')}
                </Button>
              ) : undefined
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-outline-soft">
                  <th className="text-left text-mono text-ink-muted h-10 px-6 font-medium">
                    {t('caseMgmt.list.columns.case')}
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium hidden sm:table-cell">
                    {t('caseMgmt.list.columns.citizen')}
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium hidden md:table-cell">
                    {role === 'judge'
                      ? t('caseMgmt.list.columns.assistant')
                      : t('caseMgmt.list.columns.judge')}
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium hidden lg:table-cell">
                    {t('caseMgmt.list.columns.documents')}
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium">
                    {t('caseMgmt.list.columns.status')}
                  </th>
                  <th className="text-right text-mono text-ink-muted h-10 px-6 font-medium hidden sm:table-cell">
                    {t('caseMgmt.list.columns.updated')}
                  </th>
                  {role === 'assistant' && (
                    <th className="text-right text-mono text-ink-muted h-10 px-3 font-medium">
                      {/* actions — no header label */}
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <CaseRow
                    key={c.id}
                    caseItem={c}
                    documentsCount={docCount(c.id)}
                    role={role}
                    judgeLabel={
                      role === 'assistant' ? judgeName(c.assignedJudgeId) : undefined
                    }
                    assistantLabel={
                      role === 'judge' ? assistantName(c.assistantId) : undefined
                    }
                    onOpen={() => navigate(`/cases/${c.id}`)}
                    onEdit={
                      role === 'assistant' &&
                      (c.status === 'draft' || c.status === 'returned') &&
                      c.assistantId === userId
                        ? () => navigate(`/cases/${c.id}/edit`)
                        : undefined
                    }
                    onDelete={
                      role === 'assistant' && c.status === 'draft' && c.assistantId === userId
                        ? () => {
                            if (window.confirm(t('caseMgmt.list.deleteConfirm'))) {
                              deleteMut.mutate(c.id);
                            }
                          }
                        : undefined
                    }
                    deleting={deleteMut.isPending && deleteMut.variables === c.id}
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

function CaseRow({
  caseItem,
  documentsCount,
  role,
  judgeLabel,
  assistantLabel,
  onOpen,
  onEdit,
  onDelete,
  deleting,
}: {
  caseItem: Case;
  documentsCount: number;
  role: 'judge' | 'assistant' | undefined;
  judgeLabel?: string;
  assistantLabel?: string;
  onOpen: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  deleting?: boolean;
}) {
  const { t } = useTranslation();
  const status = caseItem.status;
  const badge = CASE_STATUS_BADGE[status];

  return (
    <tr
      onClick={onOpen}
      className="border-b border-outline-soft last:border-0 hover:bg-surface-container-low transition-colors cursor-pointer"
    >
      <td className="px-6 py-4">
        <div className="flex items-start gap-3 min-w-0">
          <div
            className={cn(
              'h-9 w-9 rounded-md inline-flex items-center justify-center shrink-0',
              status === 'under_review' || status === 'returned'
                ? 'bg-amber-50 text-amber-700'
                : 'bg-primary-50 text-primary-500',
            )}
          >
            <Scale className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="text-body-md font-medium text-ink truncate">{caseItem.citizenName}</p>
            <p className="text-caption font-mono text-ink-muted">{caseItem.caseNumber}</p>
          </div>
        </div>
      </td>
      <td className="px-3 py-4 text-body-md text-ink-muted hidden sm:table-cell">
        <p className="line-clamp-2 max-w-xs">{caseItem.description}</p>
      </td>
      <td className="px-3 py-4 hidden md:table-cell">
        <div className="flex items-center gap-2 text-body-md text-ink-muted">
          {role === 'judge' ? (
            <FileSignature className="h-3.5 w-3.5 text-ink-muted shrink-0" />
          ) : (
            <Gavel className="h-3.5 w-3.5 text-ink-muted shrink-0" />
          )}
          <span className="truncate">
            {role === 'judge' ? assistantLabel : judgeLabel}
          </span>
        </div>
      </td>
      <td className="px-3 py-4 hidden lg:table-cell">
        <span className="text-body-md text-ink font-mono tabular-nums">
          {documentsCount}
        </span>
        <span className="text-caption text-ink-muted ml-1">
          {t('caseMgmt.list.columns.documents').toLowerCase()}
        </span>
      </td>
      <td className="px-3 py-4">
        <Badge variant={badge.variant}>{t(`caseStatus.${status}`)}</Badge>
      </td>
      <td className="px-6 py-4 text-right hidden sm:table-cell">
        <p className="text-body-md text-ink-muted">
          {formatDistanceToNow(new Date(caseItem.updatedAt), { addSuffix: true, locale: undefined })}
        </p>
        <p className="text-caption font-mono text-ink-muted/70">
          {format(new Date(caseItem.updatedAt), 'yyyy-MM-dd HH:mm', { locale: undefined })}
        </p>
      </td>
      {role === 'assistant' && (onEdit || onDelete) && (
        <td className="px-3 py-4">
          {/* ``e.stopPropagation`` is required because the row itself is
              clickable and would otherwise navigate to the detail page
              when the user just wanted to hit an action button. */}
          <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
            {onEdit && (
              <IconButton
                variant="ghost"
                size="sm"
                label={t('caseMgmt.list.rowEdit')}
                onClick={onEdit}
                icon={<Pencil className="h-4 w-4" />}
              />
            )}
            {onDelete && (
              <IconButton
                variant="ghost"
                size="sm"
                label={t('caseMgmt.list.rowDelete')}
                onClick={onDelete}
                disabled={deleting}
                icon={<Trash className="h-4 w-4 text-error" />}
              />
            )}
          </div>
        </td>
      )}
    </tr>
  );
}

// Mirrors the CASE_DOCUMENT_IDS distribution from the seed migration, so
// the dashboard / case-list shows realistic per-case counts. Replaced by a
// real ``/api/cases/{id}/documents`` call in Phase B.
const SEEDED_DOC_COUNTS: Record<string, number> = {
  'case-0241': 5,
  'case-0239': 1,
  'case-0235': 1,
  'case-0231': 2,
  'case-0228': 1,
  'case-0224': 2,
  'case-0219': 1,
  'case-0214': 0,
};
