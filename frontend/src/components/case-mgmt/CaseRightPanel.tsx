import { useTranslation } from 'react-i18next';
import { format } from 'date-fns';
import {
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Upload,
  FilePlus2,
  FileX2,
  Send,
  ThumbsUp,
  CornerUpLeft,
  FileSignature,
  Scale,
  History,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { CASE_STATUS_BADGE } from '@/lib/caseStyles';
import { cn } from '@/lib/cn';
import type { ActivityEvent, ActivityType, CaseDocument, Case } from '@/types/domain';

const ACTIVITY_ICON: Record<ActivityType, React.ComponentType<{ className?: string }>> = {
  case_created: FilePlus2,
  documents_uploaded: Upload,
  documents_classified: Sparkles,
  case_submitted: Send,
  case_approved: ThumbsUp,
  case_returned: CornerUpLeft,
  document_added: FilePlus2,
  document_removed: FileX2,
};

interface Props {
  caseItem: Case;
  selectedDoc: CaseDocument | null;
  /** Phase A: timeline is fed from a TanStack Query hook in the parent. */
  activity?: ActivityEvent[];
}

export function CaseRightPanel({ caseItem, selectedDoc, activity = [] }: Props) {
  const { t } = useTranslation();
  const status = caseItem.status;
  const badge = CASE_STATUS_BADGE[status];

  return (
    <div className="flex flex-col gap-6">
      {/* Status */}
      <section>
        <p className="text-mono text-ink-muted mb-2">
          {t('caseMgmt.detail.status.label')}
        </p>
        <div className="rounded-md border border-outline-soft bg-white p-4 flex items-center gap-3">
          <span
            className={cn(
              'h-2.5 w-2.5 rounded-full',
              status === 'approved' && 'bg-emerald-500',
              status === 'returned' && 'bg-error',
              status === 'under_review' && 'bg-amber-500',
              status === 'uploaded' && 'bg-primary-500',
              status === 'draft' && 'bg-outline',
            )}
          />
          <Badge variant={badge.variant}>{t(`caseStatus.${status}`)}</Badge>
        </div>
        {caseItem.returnReason && status === 'returned' && (
          <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3">
            <div className="flex items-center gap-2 mb-1">
              <AlertCircle className="h-3.5 w-3.5 text-error" />
              <p className="text-mono text-error">RETURN REASON</p>
            </div>
            <p className="text-body-md text-ink">{caseItem.returnReason}</p>
          </div>
        )}
      </section>

      {/* AI classification */}
      <section>
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="h-3.5 w-3.5 text-primary-500" />
          <p className="text-mono text-ink-muted">
            {t('caseMgmt.detail.documents.aiPanelTitle')}
          </p>
        </div>
        {selectedDoc ? (
          selectedDoc.aiConfidence === -1 ? (
            <div className="rounded-md border border-outline-soft bg-white p-4">
              <p className="text-body-md text-ink-muted">
                {t('caseMgmt.detail.documents.upload.classPending')}
              </p>
            </div>
          ) : (
            <div className="rounded-md border border-outline-soft bg-white p-4 space-y-3">
              <Row label={t('caseMgmt.detail.documents.aiDetected')}>
                <span className="text-body-md font-medium text-ink">
                  {t(`documentType.${selectedDoc.detectedType}`)}
                </span>
              </Row>
              <Row label={t('caseMgmt.detail.documents.aiCategory')}>
                <span className="inline-flex items-center h-6 px-2 rounded text-caption font-medium bg-primary-50 text-primary-700">
                  {t(`documentCategory.${selectedDoc.category}`)}
                </span>
              </Row>
              <div className="pt-3 border-t border-outline-soft">
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-mono text-ink-muted">
                    {t('caseMgmt.detail.documents.aiConfidence')}
                  </p>
                  <span className="text-body-md font-mono tabular-nums text-ink">
                    {selectedDoc.aiConfidence}%
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-outline-soft overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all',
                      selectedDoc.aiConfidence >= 90
                        ? 'bg-emerald-500'
                        : selectedDoc.aiConfidence >= 80
                          ? 'bg-amber-500'
                          : 'bg-error',
                    )}
                    style={{ width: `${Math.max(0, selectedDoc.aiConfidence)}%` }}
                  />
                </div>
              </div>
            </div>
          )
        ) : (
          <div className="rounded-md border border-dashed border-outline-soft bg-surface-container-low p-4">
            <p className="text-body-md text-ink-muted">
              {t('caseMgmt.detail.documents.previewEmpty')}
            </p>
          </div>
        )}
      </section>

      {/* Timeline */}
      <section>
        <div className="flex items-center gap-2 mb-2">
          <History className="h-3.5 w-3.5 text-ink-muted" />
          <p className="text-mono text-ink-muted">
            {t('caseMgmt.detail.timeline.title')}
          </p>
        </div>
        {activity.length === 0 ? (
          <div className="rounded-md border border-dashed border-outline-soft bg-surface-container-low p-4">
            <p className="text-body-md text-ink-muted">
              {t('caseMgmt.detail.timeline.empty')}
            </p>
          </div>
        ) : (
          <ol className="flex flex-col">
            {activity.map((evt, i) => (
              <ActivityItem
                key={evt.id}
                evt={evt}
                isLast={i === activity.length - 1}
              />
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <p className="text-mono text-ink-muted">{label}</p>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

function ActivityItem({ evt, isLast }: { evt: ActivityEvent; isLast: boolean }) {
  const { t } = useTranslation();
  const Icon = ACTIVITY_ICON[evt.type] ?? CheckCircle2;
  const actorIcon = evt.actorRole === 'judge' ? Scale : FileSignature;
  const ActorIcon = actorIcon;
  return (
    <li className="flex gap-3 relative">
      <div className="flex flex-col items-center">
        <div
          className={cn(
            'h-7 w-7 rounded-full inline-flex items-center justify-center shrink-0',
            evt.type === 'case_approved' && 'bg-emerald-50 text-emerald-600',
            evt.type === 'case_returned' && 'bg-amber-50 text-amber-700',
            evt.type === 'case_submitted' && 'bg-primary-50 text-primary-600',
            evt.type === 'documents_classified' && 'bg-primary-50 text-primary-500',
            (evt.type === 'case_created' || evt.type === 'document_added') &&
              'bg-surface-container text-ink-muted',
            evt.type === 'documents_uploaded' && 'bg-primary-50 text-primary-500',
            evt.type === 'document_removed' && 'bg-error-container text-error',
          )}
        >
          <Icon className="h-3.5 w-3.5" />
        </div>
        {!isLast && <div className="w-px flex-1 bg-outline-soft my-1" />}
      </div>
      <div className="pb-4 min-w-0 flex-1">
        <p className="text-body-md text-ink">{t(evt.messageKey)}</p>
        {evt.meta && Object.keys(evt.meta).length > 0 && (
          <p className="text-caption text-ink-muted">
            {Object.entries(evt.meta)
              .map(([k, v]) => `${k}: ${v}`)
              .join(' · ')}
          </p>
        )}
        <div className="flex items-center gap-1.5 mt-1 text-caption text-ink-muted">
          <ActorIcon className="h-3 w-3" />
          <span className="truncate">{evt.actorName}</span>
          <span className="text-ink-muted/60">·</span>
          <span className="font-mono tabular-nums">
            {format(new Date(evt.at), 'yyyy-MM-dd HH:mm')}
          </span>
        </div>
      </div>
    </li>
  );
}
