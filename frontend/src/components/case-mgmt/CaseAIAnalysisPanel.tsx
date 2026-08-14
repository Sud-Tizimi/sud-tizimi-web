/**
 * AI legal analysis panel — embedded in CaseRightPanel between the existing
 * "AI classification" section and the timeline. Phase 27 (SudAI-Law-UZ).
 *
 * Two views:
 *  - "Case-level" — factual-first synthesis and reasoning for the whole case.
 *  - "Document"   — runs / results for a specific document (only shown when
 *                   the user has selected a document in the left panel).
 *
 * The latest record drives the visible card. While a run is pending or
 * running, the corresponding useQuery has a 2s polling interval (see
 * useCaseAnalysis / useDocumentAnalysis in queries.ts) so the card flips
 * to the result without a manual refresh.
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Sparkles,
  Scale,
  BookOpen,
  AlertCircle,
  Loader2,
  FileSignature,
  Calendar,
  Paperclip,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import {
  useAnalyzeCase,
  useAnalyzeDocument,
  useCaseAnalysis,
  useDocumentAnalysis,
} from '@/hooks/queries';
import { isEnabled } from '@/lib/featureFlags';
import type {
  AIAnalysisRecord,
  AIAnalysisResult,
  AICaseAmountType,
  AICaseLegalDomain,
  CaseLegalCategory,
} from '@/types/domain';

interface Props {
  caseId: string;
  /** When a document is selected, we show a "Document" tab. */
  selectedDocumentId?: string | null;
  selectedDocumentName?: string | null;
}

type Tab = 'case' | 'document';

const CATEGORY_LABEL_KEY: Record<CaseLegalCategory, string> = {
  oilaviy_nizo: 'aiCategory.oilaviy_nizo',
  mehnat_nizosi: 'aiCategory.mehnat_nizosi',
  mamuriy_yoki_iqtisodiy_nizo: 'aiCategory.mamuriy_yoki_iqtisodiy_nizo',
  fuqarolik_ishi: 'aiCategory.fuqarolik_ishi',
  umumiy_huquqiy_murojaat: 'aiCategory.umumiy_huquqiy_murojaat',
};

const CASE_DOMAIN_LABEL_KEY: Record<AICaseLegalDomain, string> = {
  criminal_property: 'aiCaseDomain.criminal_property',
  civil_debt: 'aiCaseDomain.civil_debt',
  family: 'aiCaseDomain.family',
  labor: 'aiCaseDomain.labor',
  tax: 'aiCaseDomain.tax',
  administrative: 'aiCaseDomain.administrative',
  unknown: 'aiCaseDomain.unknown',
};

const AMOUNT_TYPE_LABEL_KEY: Record<AICaseAmountType, string> = {
  asset_value: 'aiAnalysis.amountType.assetValue',
  sale_price: 'aiAnalysis.amountType.salePrice',
  payment: 'aiAnalysis.amountType.payment',
  debt: 'aiAnalysis.amountType.debt',
  damage: 'aiAnalysis.amountType.damage',
  salary: 'aiAnalysis.amountType.salary',
  unknown: 'aiAnalysis.amountType.unknown',
};

export function CaseAIAnalysisPanel({
  caseId,
  selectedDocumentId,
  selectedDocumentName,
}: Props) {
  const { t } = useTranslation();
  const hasDocument = !!selectedDocumentId;
  const [tab, setTab] = useState<Tab>('case');

  if (!isEnabled('aiAnalysis')) return null;

  return (
    <section>
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="h-3.5 w-3.5 text-primary-500" />
        <p className="text-mono text-ink-muted">{t('aiAnalysis.panelTitle')}</p>
      </div>
      <p className="text-caption text-ink-muted mb-3 leading-relaxed">
        {t('aiAnalysis.panelSubtitle')}
      </p>

      {hasDocument && (
        <div className="inline-flex items-center bg-surface-container rounded-md p-0.5 mb-3">
          <TabButton active={tab === 'case'} onClick={() => setTab('case')}>
            {t('aiAnalysis.tabCaseLevel')}
          </TabButton>
          <TabButton active={tab === 'document'} onClick={() => setTab('document')}>
            {t('aiAnalysis.tabDocument')}
          </TabButton>
        </div>
      )}

      {tab === 'document' && hasDocument && selectedDocumentId ? (
        <DocumentResult
          documentId={selectedDocumentId}
          caseId={caseId}
          documentName={selectedDocumentName ?? null}
        />
      ) : (
        <CaseResult caseId={caseId} />
      )}
    </section>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'h-7 px-2.5 rounded text-caption font-medium transition-colors',
        active ? 'bg-white text-ink shadow-soft' : 'text-ink-muted hover:text-ink',
      )}
    >
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Case-level view
// ---------------------------------------------------------------------------

function CaseResult({ caseId }: { caseId: string }) {
  const { t } = useTranslation();
  const { data: records, isLoading } = useCaseAnalysis(caseId);
  const analyzeMut = useAnalyzeCase();
  const latest = records?.[0];

  return (
    <div className="rounded-md border border-outline-soft bg-white p-4">
      {isLoading ? (
        <LoadingRow />
      ) : !latest ? (
        <EmptyState onRun={() => analyzeMut.mutate(caseId)} running={analyzeMut.isPending} />
      ) : latest.status === 'running' || latest.status === 'pending' ? (
        <LoadingRow label={t('aiAnalysis.buttonAnalyzing')} />
      ) : latest.status === 'failed' ? (
        <ErrorBlock message={latest.errorMessage ?? t('aiAnalysis.errorFailed')} />
      ) : latest.result ? (
        <ResultCard record={latest} />
      ) : (
        <EmptyState onRun={() => analyzeMut.mutate(caseId)} running={analyzeMut.isPending} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Document-level view
// ---------------------------------------------------------------------------

function DocumentResult({
  documentId,
  caseId,
  documentName,
}: {
  documentId: string;
  caseId: string;
  documentName: string | null;
}) {
  const { t } = useTranslation();
  const { data: records, isLoading } = useDocumentAnalysis(documentId);
  const analyzeMut = useAnalyzeDocument();
  const latest = records?.[0];

  return (
    <div className="rounded-md border border-outline-soft bg-white p-4">
      {documentName && (
        <p className="text-caption font-mono text-ink-muted mb-2 truncate">{documentName}</p>
      )}
      {isLoading ? (
        <LoadingRow />
      ) : !latest ? (
        <EmptyState
          onRun={() => analyzeMut.mutate({ documentId, caseId })}
          running={analyzeMut.isPending}
        />
      ) : latest.status === 'running' || latest.status === 'pending' ? (
        <LoadingRow label={t('aiAnalysis.buttonAnalyzing')} />
      ) : latest.status === 'failed' ? (
        <ErrorBlock message={latest.errorMessage ?? t('aiAnalysis.errorFailed')} />
      ) : latest.result ? (
        <ResultCard record={latest} />
      ) : (
        <EmptyState
          onRun={() => analyzeMut.mutate({ documentId, caseId })}
          running={analyzeMut.isPending}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Result card
// ---------------------------------------------------------------------------

function ResultCard({ record }: { record: AIAnalysisRecord }) {
  const { t } = useTranslation();
  const result = record.result;
  if (!result) return null;

  const isCaseLevel = record.documentId == null;
  const classification = result.classification;
  const candidateDomains = isCaseLevel
    ? result.candidateLegalDomains?.length
      ? result.candidateLegalDomains
      : (result.factualSynthesis?.candidateLegalDomains ?? [])
    : [];
  const primaryDomain = candidateDomains[0];
  const confidence =
    result.confidencePercent ??
    Math.round((primaryDomain?.confidence ?? classification?.confidence ?? 0) * 100);
  const recommendation = result.humanReview;
  const sources = result.matchedSources ?? [];
  const objects = result.extractedObjects;
  const evidenceSummary = result.evidenceSummary?.length
    ? result.evidenceSummary
    : (result.factualSynthesis?.facts.map((fact) => fact.statement) ?? []);
  const timeline = result.timeline?.length
    ? result.timeline
    : (result.factualSynthesis?.timeline ?? []);
  const uncertainties = result.uncertainties?.length
    ? result.uncertainties
    : (result.factualSynthesis?.uncertainties ?? []);
  const typedAmounts = result.typedAmounts?.length
    ? result.typedAmounts
    : (result.factualSynthesis?.amounts ?? []);
  const hasInsufficientContext =
    result.findings?.some((finding) => finding.kind === 'insufficient_context') ?? false;
  const requiresManualSourceReview = isCaseLevel && sources.length === 0 && hasInsufficientContext;
  const showLegacyExtractedObjects = !isCaseLevel || !result.factualSynthesis;
  const isHumanReview = recommendation?.status === 'qoʻlda tekshirish kerak' || recommendation?.status === 'qo\'lda tekshirish kerak';

  return (
    <div className="space-y-4">
      {/* Sub-failure banner (case-level only) */}
      {result.subFailures && result.subFailures.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 flex items-start gap-2">
          <AlertCircle className="h-3.5 w-3.5 text-amber-700 mt-0.5 shrink-0" />
          <p className="text-caption text-amber-700">
            {t('aiAnalysis.partialFailures', { count: result.subFailures.length })}
          </p>
        </div>
      )}

      {/* Canonical case domain (legacy classification is the fallback). */}
      {(primaryDomain || classification) && (
        <div>
          <p className="text-mono text-ink-muted mb-1.5">
            {t(primaryDomain ? 'aiAnalysis.caseDomainTitle' : 'aiAnalysis.classificationTitle')}
          </p>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-title-lg text-ink font-semibold leading-tight">
                {primaryDomain
                  ? t(CASE_DOMAIN_LABEL_KEY[primaryDomain.domain])
                  : t(
                      CATEGORY_LABEL_KEY[classification!.mainCategory] ??
                        CATEGORY_LABEL_KEY.umumiy_huquqiy_murojaat,
                    )}
              </p>
              {(primaryDomain?.rationale || classification?.subCategory) && (
                <p className="text-caption text-ink-muted mt-0.5">
                  {primaryDomain?.rationale ?? classification?.subCategory}
                </p>
              )}
            </div>
            {recommendation && (
              <Badge variant={isHumanReview ? 'warning' : 'info'} dot>
                {isHumanReview
                  ? t('aiAnalysis.statusHumanReviewRequired')
                  : t('aiAnalysis.statusAwaitingReview')}
              </Badge>
            )}
          </div>
          {confidence > 0 && (
            <div className="mt-2">
              <div className="flex items-center justify-between mb-1">
                <p className="text-caption text-ink-muted">
                  {t('aiAnalysis.confidenceLabel', { percent: confidence })}
                </p>
              </div>
              <div className="h-1.5 rounded-full bg-outline-soft overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all',
                    confidence >= 90
                      ? 'bg-emerald-500'
                      : confidence >= 80
                        ? 'bg-amber-500'
                        : 'bg-error',
                  )}
                  style={{ width: `${Math.max(0, confidence)}%` }}
                />
              </div>
            </div>
          )}
          {candidateDomains.length > 1 && (
            <div className="mt-3">
              <p className="text-caption text-ink-muted mb-1.5">
                {t('aiAnalysis.candidateDomainsTitle')}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {candidateDomains.map((candidate) => (
                  <Badge key={candidate.domain} variant="neutral">
                    {t(CASE_DOMAIN_LABEL_KEY[candidate.domain])}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Factual-first case result. Document-level cards keep their old layout. */}
      {isCaseLevel && result.primaryConclusion && (
        <div>
          <p className="text-mono text-ink-muted mb-1.5">
            {t('aiAnalysis.primaryConclusionTitle')}
          </p>
          <p className="text-body-md text-ink leading-relaxed">{result.primaryConclusion}</p>
        </div>
      )}

      {isCaseLevel && evidenceSummary.length > 0 && (
        <div>
          <p className="text-mono text-ink-muted mb-1.5">
            {t('aiAnalysis.evidenceSummaryTitle')}
          </p>
          <ul className="list-disc pl-5 space-y-1 text-body-md text-ink">
            {evidenceSummary.map((statement, index) => (
              <li key={`${index}-${statement.slice(0, 40)}`} className="leading-relaxed">
                {statement}
              </li>
            ))}
          </ul>
        </div>
      )}

      {isCaseLevel && timeline.length > 0 && (
        <div>
          <p className="text-mono text-ink-muted mb-1.5">{t('aiAnalysis.timelineTitle')}</p>
          <ol className="space-y-2">
            {timeline.map((event) => (
              <li key={`${event.sequence}-${event.event}`} className="flex items-start gap-2">
                <span className="mt-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-surface-container text-caption font-mono text-ink-muted">
                  {event.sequence}
                </span>
                <p className="text-body-md text-ink leading-relaxed">{event.event}</p>
              </li>
            ))}
          </ol>
        </div>
      )}

      {isCaseLevel && typedAmounts.length > 0 && (
        <div>
          <p className="text-mono text-ink-muted mb-1.5">
            {t('aiAnalysis.typedAmountsTitle')}
          </p>
          <dl className="grid grid-cols-1 gap-y-2">
            {typedAmounts.map((amount, index) => (
              <div key={`${amount.amountType}-${amount.amount}-${index}`}>
                <dt className="text-caption text-ink-muted">
                  {t(AMOUNT_TYPE_LABEL_KEY[amount.amountType])}
                </dt>
                <dd className="text-body-md text-ink font-medium">{amount.amount}</dd>
                <dd className="text-caption text-ink-muted leading-relaxed">{amount.context}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {isCaseLevel && uncertainties.length > 0 && (
        <div>
          <p className="text-mono text-ink-muted mb-1.5">
            {t('aiAnalysis.uncertaintiesTitle')}
          </p>
          <ul className="list-disc pl-5 space-y-1 text-body-md text-ink-muted">
            {uncertainties.map((uncertainty, index) => (
              <li key={`${index}-${uncertainty.slice(0, 40)}`} className="leading-relaxed">
                {uncertainty}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendation text */}
      {requiresManualSourceReview ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 flex items-start gap-2">
          <AlertCircle className="h-3.5 w-3.5 text-amber-700 mt-0.5 shrink-0" />
          <div>
            <p className="text-body-md font-medium text-amber-800">
              {t('aiAnalysis.manualLegalSourcesRequired')}
            </p>
            {recommendation?.risk && (
              <p className="text-caption text-amber-700 mt-1 leading-relaxed">
                {recommendation.risk}
              </p>
            )}
          </div>
        </div>
      ) : recommendation ? (
        <div>
          <p className="text-mono text-ink-muted mb-1.5">{t('aiAnalysis.recommendationTitle')}</p>
          <p className="text-body-md text-ink leading-relaxed">{recommendation.recommendation}</p>
          {recommendation.risk && (
            <p className="text-caption text-ink-muted mt-1.5 leading-relaxed">
              {recommendation.risk}
            </p>
          )}
        </div>
      ) : null}

      {/* Matched legal sources */}
      {sources.length > 0 && (
        <div>
          <p className="text-mono text-ink-muted mb-1.5">{t('aiAnalysis.matchedSourcesTitle')}</p>
          <ul className="flex flex-col gap-2">
            {sources.map((src, i) => (
              <li
                key={`${src.law}-${src.article}-${i}`}
                className="rounded-md border border-outline-soft bg-surface-container-low p-3"
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <p className="text-caption font-mono text-ink inline-flex items-center gap-1.5">
                    <Scale className="h-3 w-3 text-primary-500 shrink-0" />
                    <span className="truncate">{src.law}</span>
                    <span className="text-ink-muted">·</span>
                    <span className="text-ink-muted shrink-0">{src.article}</span>
                  </p>
                  <Badge variant="info">
                    {t('aiAnalysis.matchedSourceRelevance', {
                      percent: Math.round((src.relevance ?? 0) * 100),
                    })}
                  </Badge>
                </div>
                <p className="text-body-md text-ink leading-relaxed line-clamp-4">{src.excerpt}</p>
                {src.sourceUrl && (
                  <a
                    href={src.sourceUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-caption text-primary-600 hover:text-primary-700 mt-1.5 inline-flex items-center gap-1"
                  >
                    <BookOpen className="h-3 w-3" />
                    lex.uz
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Extracted legal objects */}
      {showLegacyExtractedObjects && objects && hasAnyExtracted(objects) && (
        <div>
          <p className="text-mono text-ink-muted mb-1.5">{t('aiAnalysis.extractedTitle')}</p>
          <dl className="grid grid-cols-1 gap-y-1.5 text-body-md">
            {objects.claimant && (
              <ExtractedRow icon={FileSignature} label={t('aiAnalysis.extractedClaimant')} value={objects.claimant} />
            )}
            {objects.respondent && (
              <ExtractedRow icon={FileSignature} label={t('aiAnalysis.extractedRespondent')} value={objects.respondent} />
            )}
            {objects.claimSubject && (
              <ExtractedRow icon={BookOpen} label={t('aiAnalysis.extractedClaimSubject')} value={objects.claimSubject} />
            )}
            {objects.demandSummary && (
              <ExtractedRow icon={BookOpen} label={t('aiAnalysis.extractedDemand')} value={objects.demandSummary} />
            )}
            {objects.contractNumber && (
              <ExtractedRow icon={FileSignature} label={t('aiAnalysis.extractedContract')} value={objects.contractNumber} />
            )}
            {objects.debtAmount && (
              <ExtractedRow icon={FileSignature} label={t('aiAnalysis.extractedDebt')} value={objects.debtAmount} />
            )}
            {objects.dates.length > 0 && (
              <ExtractedRow
                icon={Calendar}
                label={t('aiAnalysis.extractedDates')}
                value={objects.dates.join(', ')}
              />
            )}
            {objects.attachments.length > 0 && (
              <ExtractedRow
                icon={Paperclip}
                label={t('aiAnalysis.extractedAttachments')}
                value={objects.attachments.join(', ')}
              />
            )}
          </dl>
        </div>
      )}

      {/* Explanation footer */}
      {result.explanation && (
        <div className="pt-3 border-t border-outline-soft">
          <p className="text-caption italic text-ink-muted leading-relaxed">
            {result.explanation}
          </p>
        </div>
      )}
    </div>
  );
}

function ExtractedRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-2">
      <Icon className="h-3.5 w-3.5 text-ink-muted mt-1 shrink-0" />
      <div className="min-w-0 flex-1">
        <dt className="text-caption text-ink-muted">{label}</dt>
        <dd className="text-body-md text-ink leading-snug break-words">{value}</dd>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// States
// ---------------------------------------------------------------------------

function LoadingRow({ label }: { label?: string }) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-2 py-1">
      <Loader2 className="h-4 w-4 animate-spin text-primary-500" />
      <p className="text-body-md text-ink-muted">{label ?? t('aiAnalysis.loading')}</p>
    </div>
  );
}

function EmptyState({ onRun, running }: { onRun: () => void; running: boolean }) {
  const { t } = useTranslation();
  return (
    <div className="text-center py-2">
      <div className="mx-auto h-10 w-10 rounded-full bg-primary-50 text-primary-500 inline-flex items-center justify-center mb-2">
        <Sparkles className="h-5 w-5" />
      </div>
      <p className="text-body-md text-ink-muted mb-3 max-w-xs mx-auto leading-relaxed">
        {t('aiAnalysis.empty')}
      </p>
      <Button
        size="sm"
        variant="secondary"
        leftIcon={running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        onClick={onRun}
        disabled={running}
      >
        {t('aiAnalysis.emptyAction')}
      </Button>
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  const { t } = useTranslation();
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-3 flex items-start gap-2">
      <AlertCircle className="h-3.5 w-3.5 text-error mt-0.5 shrink-0" />
      <div>
        <p className="text-body-md text-error font-medium">{t('aiAnalysis.errorFailed')}</p>
        <p className="text-caption text-error/80 mt-0.5">{message}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function hasAnyExtracted(objects: AIAnalysisResult['extractedObjects']): boolean {
  if (!objects) return false;
  return Boolean(
    objects.claimant ||
      objects.respondent ||
      objects.claimSubject ||
      objects.demandSummary ||
      objects.contractNumber ||
      objects.debtAmount ||
      (objects.dates && objects.dates.length > 0) ||
      (objects.attachments && objects.attachments.length > 0),
  );
}

// Convenience: render a small "Analyzed" badge for the document list.
export function AIAnalyzedBadge({
  record,
  className,
}: {
  record: AIAnalysisRecord | null | undefined;
  className?: string;
}) {
  const { t } = useTranslation();
  if (!isEnabled('aiAnalysis')) return null;
  if (!record) {
    return (
      <Badge variant="neutral" dot className={className}>
        {t('aiAnalysis.docBadgeNotAnalyzed')}
      </Badge>
    );
  }
  if (record.status === 'done') {
    return (
      <Badge variant="info" dot className={className}>
        {t('aiAnalysis.docBadgeAnalyzed')}
      </Badge>
    );
  }
  if (record.status === 'running' || record.status === 'pending') {
    return (
      <Badge variant="warning" dot className={className}>
        {t('aiAnalysis.buttonAnalyzing')}
      </Badge>
    );
  }
  return (
    <Badge variant="neutral" dot className={className}>
      {t('aiAnalysis.docBadgeNotAnalyzed')}
    </Badge>
  );
}
