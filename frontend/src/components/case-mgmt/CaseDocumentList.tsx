import { useTranslation } from 'react-i18next';
import { FileText } from 'lucide-react';
import { EmptyState } from '@/components/ui/EmptyState';
import { cn } from '@/lib/cn';
import { isEnabled } from '@/lib/featureFlags';
import { useDocumentAnalysis } from '@/hooks/queries';
import type { CaseDocument } from '@/types/domain';

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

interface Props {
  caseId: string;
  documents: CaseDocument[];
  /** Currently selected document id (controlled by parent). Phase A: not used
   * because the detail page passes `documents=[]` — the component is
   * rendered as a "no docs yet" placeholder until Phase B ships the real
   * upload UI in /upload. */
  selectedId?: string | null;
  onSelect?: (id: string) => void;
}

/**
 * Read-only document list. Phase A: documents are empty in CaseDetail, so
 * this only renders the empty state. Phase B will replace this with a
 * full upload + delete UI on the /upload page; the same component will be
 * reused on CaseDetail in read-only mode.
 */
export function CaseDocumentList({ documents, selectedId, onSelect }: Props) {
  const { t } = useTranslation();

  if (documents.length === 0) {
    return (
      <EmptyState
        icon={<FileText className="h-5 w-5" />}
        title={t('caseMgmt.detail.documents.empty')}
        description={t('caseMgmt.detail.documents.emptyAssistant')}
      />
    );
  }

  return (
    <ul className="flex flex-col gap-2">
      {documents.map((doc) => (
        <DocumentItem
          key={doc.id}
          doc={doc}
          selected={doc.id === selectedId}
          onSelect={() => onSelect?.(doc.id)}
        />
      ))}
    </ul>
  );
}

function DocumentItem({
  doc,
  selected,
  onSelect,
}: {
  doc: CaseDocument;
  selected: boolean;
  onSelect: () => void;
}) {
  const { t } = useTranslation();
  const classifying = doc.aiConfidence === -1;
  // Per-document AI status badge. Disabled (returns null) when the feature
  // flag is off so we don't fire unnecessary network requests.
  const { data: aiRecords } = useDocumentAnalysis(
    isEnabled('aiAnalysis') ? doc.id : null,
  );
  const latestAi = aiRecords?.[0];

  return (
    <li>
      <div
        onClick={onSelect}
        className={cn(
          'rounded-md border p-3 transition-colors flex items-start gap-3 cursor-pointer',
          selected
            ? 'border-primary-500 bg-primary-50/30'
            : 'border-outline-soft bg-white hover:border-outline',
        )}
      >
        <div
          className={cn(
            'h-9 w-9 rounded-md inline-flex items-center justify-center shrink-0',
            selected ? 'bg-primary-500 text-white' : 'bg-primary-50 text-primary-500',
          )}
        >
          <FileText className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-body-md font-medium text-ink truncate">{doc.fileName}</p>
          <p className="text-caption font-mono text-ink-muted">
            {(doc.fileType as string).toUpperCase()} · {formatBytes(doc.size)}
          </p>
          {!classifying && (
            <p className="text-caption text-ink-muted inline-flex items-center gap-1 mt-1">
              {t('caseMgmt.detail.documents.upload.classDone', {
                type: t(`documentType.${doc.detectedType}`),
                confidence: doc.aiConfidence,
              })}
            </p>
          )}
          {isEnabled('aiAnalysis') && latestAi?.status === 'done' && (
            <p className="text-caption text-primary-600 inline-flex items-center gap-1 mt-1">
              <span className="h-1.5 w-1.5 rounded-full bg-primary-500" />
              {t('aiAnalysis.docBadgeAnalyzed')}
            </p>
          )}
        </div>
      </div>
    </li>
  );
}
