import { useTranslation } from 'react-i18next';
import { FileText, Download, Eye, Sparkles, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import { isEnabled } from '@/lib/featureFlags';
import { useAnalyzeDocument } from '@/hooks/queries';
import type { CaseDocument } from '@/types/domain';

interface Props {
  document: CaseDocument | null;
  /** Used by the "Analyze" button so the mutation can invalidate
   * the case-level AI panel after a successful run. Optional — the
   * button stays available even when not provided. */
  caseId?: string | null;
  /** Phase A: there is no real download yet. Hidden in Phase A; the
   * button is rendered but disabled. Phase B will wire it to
   * `/api/documents/{id}/download`. */
  downloadDisabled?: boolean;
}

/**
 * Document preview pane. Phase A renders the same mock surface as CP1 but
 * receives the document via prop instead of reading it from the (now
 * removed) caseStore. The download button is disabled because no real file
 * is on disk in Phase A.
 */
export function DocumentPreview({ document, caseId, downloadDisabled = true }: Props) {
  const { t } = useTranslation();
  const analyzeMut = useAnalyzeDocument();
  const showAnalyze = isEnabled('aiAnalysis') && !!document;

  if (!document) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center py-16 px-6 rounded-md border border-dashed border-outline-soft bg-surface-container-low">
        <div className="h-12 w-12 rounded-full bg-primary-50 text-primary-500 inline-flex items-center justify-center mb-3">
          <Eye className="h-5 w-5" />
        </div>
        <p className="text-title-lg text-ink mb-1">
          {t('caseMgmt.detail.documents.previewEmpty')}
        </p>
        <p className="text-body-md text-ink-muted max-w-sm">
          {t('caseMgmt.detail.documents.previewPlaceholder')}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-outline-soft bg-white">
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-8 w-8 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center shrink-0">
            <FileText className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="text-body-md font-medium text-ink truncate">{document.fileName}</p>
            <p className="text-caption font-mono text-ink-muted">
              {(document.fileType as string).toUpperCase()} · {document.detectedTypeLabel}
            </p>
          </div>
        </div>
        <Button
          size="sm"
          variant="secondary"
          leftIcon={<Download className="h-4 w-4" />}
          disabled={downloadDisabled}
        >
          Download
        </Button>
        {showAnalyze && (
          <Button
            size="sm"
            variant="secondary"
            leftIcon={
              analyzeMut.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )
            }
            disabled={analyzeMut.isPending}
            onClick={() =>
              document &&
              analyzeMut.mutate({ documentId: document.id, caseId: caseId ?? null })
            }
          >
            {t('aiAnalysis.buttonShort')}
          </Button>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 bg-surface-container-low p-6 overflow-auto">
        <PreviewSurface doc={document} />
      </div>
    </div>
  );
}

function PreviewSurface({ doc }: { doc: CaseDocument }) {
  const { t } = useTranslation();

  // For PDF/DOCX we show a "page 1" mock surface.
  if (doc.fileType === 'pdf' || doc.fileType === 'docx') {
    return (
      <div className="mx-auto max-w-3xl bg-white border border-outline-soft rounded-md shadow-soft p-10 min-h-[640px]">
        <div className="border-b border-outline-soft pb-4 mb-6">
          <p className="text-mono text-ink-muted">{doc.detectedTypeLabel.toUpperCase()}</p>
          <h3 className="text-headline-md text-ink mt-1">{doc.fileName.replace(/\.[^.]+$/, '')}</h3>
        </div>
        <div className="space-y-3">
          <PreviewLine widthClass="w-full" />
          <PreviewLine widthClass="w-11/12" />
          <PreviewLine widthClass="w-10/12" />
          <PreviewLine widthClass="w-full" />
          <div className="h-3" />
          <PreviewLine widthClass="w-9/12" />
          <PreviewLine widthClass="w-full" />
          <PreviewLine widthClass="w-8/12" />
          <div className="h-3" />
          <PreviewLine widthClass="w-full" />
          <PreviewLine widthClass="w-10/12" />
          <PreviewLine widthClass="w-9/12" />
          <PreviewLine widthClass="w-11/12" />
        </div>
        <div className="mt-8 flex items-center justify-center">
          <p className="text-caption italic text-ink-muted">
            {t('caseMgmt.detail.documents.previewPlaceholder')}
          </p>
        </div>
      </div>
    );
  }

  // Image
  if (doc.fileType === 'jpg' || doc.fileType === 'png') {
    return (
      <div className="mx-auto max-w-3xl bg-white border border-outline-soft rounded-md shadow-soft p-6 min-h-[640px] flex items-center justify-center">
        <div className="w-full max-w-md aspect-[3/4] rounded-md bg-gradient-to-br from-surface-container-low to-surface-container border border-outline-soft flex items-center justify-center">
          <div className="text-center">
            <FileText className="h-10 w-10 text-ink-muted mx-auto mb-2" />
            <p className="text-body-md text-ink-muted">{doc.fileName}</p>
            <p className="text-caption text-ink-muted/70 mt-1">
              {t('caseMgmt.detail.documents.previewPlaceholder')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl bg-white border border-outline-soft rounded-md shadow-soft p-10 min-h-[640px] flex items-center justify-center">
      <p className="text-body-md text-ink-muted">
        {t('caseMgmt.detail.documents.previewUnsupported')}
      </p>
    </div>
  );
}

function PreviewLine({ widthClass }: { widthClass: string }) {
  return <div className={cn('h-3 rounded bg-outline-soft/70', widthClass)} />;
}
