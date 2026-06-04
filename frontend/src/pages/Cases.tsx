import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Scale, Gavel, Calendar, Plus, FileText } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardHeader, CardTitle, Badge, Button, EmptyState } from '@/components/ui';
import { MOCK_CASES, type CaseRow } from '@/lib/mock-data';
import { format, parseISO } from 'date-fns';
import { cn } from '@/lib/cn';

const STATUS_STYLES: Record<CaseRow['status'], { variant: 'success' | 'warning' | 'info' | 'neutral'; labelKey: string }> = {
  open: { variant: 'info', labelKey: 'case.status.open' },
  in_hearing: { variant: 'warning', labelKey: 'case.status.inHearing' },
  adjourned: { variant: 'neutral', labelKey: 'case.status.adjourned' },
  closed: { variant: 'success', labelKey: 'case.status.closed' },
};

export function Cases() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const inHearing = MOCK_CASES.filter((c) => c.status === 'in_hearing').length;
  const total = MOCK_CASES.length;

  return (
    <div className="p-6 md:p-8 max-w-screen-2xl">
      <PageHeader
        title={t('nav.cases')}
        subtitle="All cases scheduled for hearing. Filters and analytics coming in Checkpoint 2."
        actions={
          <Button
            size="md"
            variant="secondary"
            leftIcon={<Plus className="h-4 w-4" />}
            disabled
            title="Available in Checkpoint 2"
          >
            New Case
          </Button>
        }
      />

      {/* Lightweight summary — no analytics, just orientation */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <SummaryTile
          icon={<Scale className="h-5 w-5" />}
          label="Total cases"
          value={`${total}`}
        />
        <SummaryTile
          icon={<Gavel className="h-5 w-5" />}
          label="In hearing now"
          value={`${inHearing}`}
        />
      </div>

      <Card padding="md">
        <CardHeader>
          <div>
            <CardTitle>All Cases</CardTitle>
            <p className="text-body-md text-ink-muted mt-0.5">{total} records</p>
          </div>
        </CardHeader>

        {MOCK_CASES.length === 0 ? (
          <EmptyState
            icon={<FileText className="h-5 w-5" />}
            title="No cases"
            description="No cases have been filed yet."
          />
        ) : (
          <div className="overflow-x-auto -mx-6">
            <table className="w-full">
              <thead>
                <tr className="border-b border-outline-soft">
                  <th className="text-left text-mono text-ink-muted h-10 px-6 font-medium">
                    Case
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium hidden md:table-cell">
                    Parties
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium hidden lg:table-cell">
                    Judge
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium hidden sm:table-cell">
                    Hearing
                  </th>
                  <th className="text-left text-mono text-ink-muted h-10 px-3 font-medium">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {MOCK_CASES.map((c) => {
                  const style = STATUS_STYLES[c.status];
                  const hearing = safeFormat(c.hearingDate);
                  return (
                    <tr
                      key={c.id}
                      onClick={() => navigate('/sessions')}
                      className="border-b border-outline-soft last:border-0 hover:bg-surface-container-low transition-colors cursor-pointer"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-start gap-3 min-w-0">
                          <div
                            className={cn(
                              'h-9 w-9 rounded-md inline-flex items-center justify-center shrink-0',
                              c.status === 'in_hearing'
                                ? 'bg-error-container text-error'
                                : 'bg-primary-50 text-primary-500',
                            )}
                          >
                            <Scale className="h-4 w-4" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-body-md font-medium text-ink truncate">{c.title}</p>
                            <p className="text-caption font-mono text-ink-muted">{c.caseNumber}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-4 text-body-md text-ink-muted hidden md:table-cell">
                        {c.parties}
                      </td>
                      <td className="px-3 py-4 text-body-md text-ink-muted hidden lg:table-cell">
                        {c.judge}
                      </td>
                      <td className="px-3 py-4 hidden sm:table-cell">
                        {hearing ? (
                          <div className="flex items-center gap-1.5 text-body-md text-ink">
                            <Calendar className="h-3.5 w-3.5 text-ink-muted" />
                            <span className="font-mono tabular-nums">{hearing}</span>
                          </div>
                        ) : (
                          <span className="text-ink-muted">—</span>
                        )}
                      </td>
                      <td className="px-3 py-4">
                        <Badge variant={style.variant}>{t(style.labelKey)}</Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function SummaryTile({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-white border border-outline-soft rounded-lg p-4 flex items-center gap-3">
      <span className="h-10 w-10 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center">
        {icon}
      </span>
      <div>
        <p className="text-mono text-ink-muted">{label}</p>
        <p className="text-headline-md text-ink tabular-nums">{value}</p>
      </div>
    </div>
  );
}

function safeFormat(iso: string): string | null {
  try {
    return format(parseISO(iso), 'yyyy-MM-dd');
  } catch {
    return null;
  }
}
