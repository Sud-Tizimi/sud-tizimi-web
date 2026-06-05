import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, AlertCircle, Scale } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardDescription, Button, EmptyState } from '@/components/ui';
import { useCases, useCreateCase, useJudges } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import { ApiError } from '@/lib/api';
import { cn } from '@/lib/cn';

interface FormState {
  caseNumber: string;
  citizenName: string;
  description: string;
  assignedJudgeId: string;
}

const FORMAT_RE = /^CASE-\d{4}-\d{4}$/;

export function CaseCreate() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { role } = useAuth();
  const { data: cases = [] } = useCases();
  const { data: judges = [], isLoading: judgesLoading } = useJudges();
  const createCase = useCreateCase();

  const [form, setForm] = useState<FormState>({
    caseNumber: '',
    citizenName: '',
    description: '',
    assignedJudgeId: '',
  });
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [touched, setTouched] = useState<Partial<Record<keyof FormState, boolean>>>({});
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Auto-fill next case number when we know existing cases.
  useEffect(() => {
    if (!form.caseNumber) {
      setForm((f) => ({ ...f, caseNumber: nextCaseNumber(cases.map((c) => c.caseNumber)) }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cases.length]);

  // Default the judge picker to the first judge in the list.
  useEffect(() => {
    if (!form.assignedJudgeId && judges.length > 0) {
      setForm((f) => ({ ...f, assignedJudgeId: judges[0].id }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [judges.length]);

  // Server-enforced: only assistants can create cases.
  if (role !== 'assistant') {
    return (
      <div className="p-6 md:p-8 max-w-3xl">
        <EmptyState
          title="Not available"
          description="Only assistants can create cases."
        />
        <div className="mt-4">
          <Button variant="ghost" onClick={() => navigate('/cases')}>
            {t('common.back')}
          </Button>
        </div>
      </div>
    );
  }

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => {
    setForm((f) => ({ ...f, [k]: v }));
    if (touched[k]) {
      setErrors(validate({ ...form, [k]: v }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const v = validate(form);
    setErrors(v);
    setTouched({ caseNumber: true, citizenName: true, description: true, assignedJudgeId: true });
    if (Object.keys(v).length > 0) return;
    setSubmitting(true);
    setApiError(null);
    try {
      const c = await createCase.mutateAsync({
        caseNumber: form.caseNumber.trim(),
        citizenName: form.citizenName.trim(),
        description: form.description,
        assignedJudgeId: form.assignedJudgeId,
      });
      navigate(`/cases/${c.id}`);
    } catch (e) {
      if (e instanceof ApiError && e.detail === 'case_number_taken') {
        setErrors({ caseNumber: 'caseNumberFormat' });
      } else {
        setApiError(t('auth.login.networkError'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const judgeOptions = useMemo(() => judges, [judges]);

  return (
    <div className="p-6 md:p-8 max-w-3xl">
      <PageHeader
        title={t('caseMgmt.create.title')}
        subtitle={t('caseMgmt.create.subtitle')}
        actions={
          <Button
            variant="ghost"
            size="md"
            leftIcon={<ArrowLeft className="h-4 w-4" />}
            onClick={() => navigate('/cases')}
          >
            {t('caseMgmt.list.title')}
          </Button>
        }
      />

      <Card padding="lg">
        <form onSubmit={handleSubmit} noValidate>
          <CardHeader>
            <div>
              <CardTitle>{t('caseMgmt.create.title')}</CardTitle>
              <CardDescription>{t('caseMgmt.create.subtitle')}</CardDescription>
            </div>
          </CardHeader>

          <div className="flex flex-col gap-4">
            <Field
              label={t('caseMgmt.create.fields.caseNumber')}
              required
              error={
                touched.caseNumber && errors.caseNumber
                  ? t(`caseMgmt.create.errors.${errors.caseNumber}`)
                  : undefined
              }
            >
              <input
                type="text"
                value={form.caseNumber}
                onChange={(e) => set('caseNumber', e.target.value.toUpperCase())}
                onBlur={() => {
                  setTouched((tt) => ({ ...tt, caseNumber: true }));
                  setErrors(validate(form));
                }}
                placeholder={t('caseMgmt.create.placeholders.caseNumber')}
                className={inputCx(!!(touched.caseNumber && errors.caseNumber))}
                aria-invalid={!!(touched.caseNumber && errors.caseNumber)}
                aria-describedby="caseNumber-error"
                autoFocus
              />
            </Field>

            <Field
              label={t('caseMgmt.create.fields.citizenName')}
              required
              error={
                touched.citizenName && errors.citizenName
                  ? t(`caseMgmt.create.errors.${errors.citizenName}`)
                  : undefined
              }
            >
              <input
                type="text"
                value={form.citizenName}
                onChange={(e) => set('citizenName', e.target.value)}
                onBlur={() => {
                  setTouched((tt) => ({ ...tt, citizenName: true }));
                  setErrors(validate(form));
                }}
                placeholder={t('caseMgmt.create.placeholders.citizenName')}
                className={inputCx(!!(touched.citizenName && errors.citizenName))}
                aria-invalid={!!(touched.citizenName && errors.citizenName)}
              />
            </Field>

            <Field label={t('caseMgmt.create.fields.description')}>
              <textarea
                value={form.description}
                onChange={(e) => set('description', e.target.value)}
                rows={4}
                placeholder={t('caseMgmt.create.placeholders.description')}
                className={inputCx(false)}
              />
            </Field>

            <Field
              label={t('caseMgmt.create.fields.assignedJudge')}
              required
              error={
                touched.assignedJudgeId && errors.assignedJudgeId
                  ? t(`caseMgmt.create.errors.${errors.assignedJudgeId}`)
                  : undefined
              }
            >
              {judgesLoading ? (
                <EmptyState className="py-6" title={t('common.loading')} />
              ) : judgeOptions.length === 0 ? (
                <EmptyState className="py-6" title={t('common.noResults')} />
              ) : (
                <div className="flex flex-col gap-2">
                  {judgeOptions.map((j) => {
                    const active = form.assignedJudgeId === j.id;
                    return (
                      <button
                        key={j.id}
                        type="button"
                        onClick={() => set('assignedJudgeId', j.id)}
                        className={cn(
                          'flex items-center gap-3 p-3 rounded-md border text-left transition-colors',
                          active
                            ? 'border-primary-500 bg-primary-50/30'
                            : 'border-outline-soft bg-white hover:border-outline',
                        )}
                      >
                        <div
                          className={cn(
                            'h-9 w-9 rounded-md inline-flex items-center justify-center shrink-0',
                            active ? 'bg-primary-500 text-white' : 'bg-primary-50 text-primary-500',
                          )}
                        >
                          <Scale className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-body-md font-medium text-ink">{j.fullName}</p>
                          {j.court && (
                            <p className="text-caption text-ink-muted truncate">{j.court}</p>
                          )}
                        </div>
                        <span
                          className={cn(
                            'h-4 w-4 rounded-full border-2 shrink-0',
                            active ? 'border-primary-500 bg-primary-500' : 'border-outline',
                          )}
                          aria-hidden
                        />
                      </button>
                    );
                  })}
                </div>
              )}
            </Field>

            {apiError && (
              <div
                role="alert"
                className="rounded-md border border-red-200 bg-red-50 p-3 text-body-md text-error"
              >
                {apiError}
              </div>
            )}
          </div>

          <div className="mt-6 pt-4 border-t border-outline-soft flex items-center justify-end gap-3">
            <Button variant="ghost" onClick={() => navigate('/cases')}>
              {t('common.cancel')}
            </Button>
            <Button
              type="submit"
              size="md"
              leftIcon={<Save className="h-4 w-4" />}
              disabled={submitting}
            >
              {submitting ? t('caseMgmt.create.actions.creating') : t('caseMgmt.create.actions.create')}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function Field({
  label,
  required,
  error,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-mono text-ink-muted inline-flex items-center gap-1">
        {label}
        {required && <span className="text-error">*</span>}
      </label>
      {children}
      {error && (
        <p className="text-caption text-error inline-flex items-center gap-1">
          <AlertCircle className="h-3 w-3" />
          {error}
        </p>
      )}
    </div>
  );
}

function inputCx(hasError: boolean) {
  return cn(
    'w-full rounded-md border bg-white text-body-md text-ink placeholder:text-ink-muted px-3 py-2 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15 transition-colors',
    hasError ? 'border-error' : 'border-outline-soft',
  );
}

function validate(form: FormState): Partial<Record<keyof FormState, string>> {
  const e: Partial<Record<keyof FormState, string>> = {};
  if (!form.caseNumber.trim()) e.caseNumber = 'caseNumberRequired';
  else if (!FORMAT_RE.test(form.caseNumber.trim())) e.caseNumber = 'caseNumberFormat';
  if (!form.citizenName.trim()) e.citizenName = 'citizenNameRequired';
  if (!form.assignedJudgeId) e.assignedJudgeId = 'judgeRequired';
  return e;
}

function nextCaseNumber(existing: string[]): string {
  const year = new Date().getFullYear();
  const prefix = `CASE-${year}-`;
  const used = new Set(
    existing
      .filter((c) => c.startsWith(prefix))
      .map((c) => Number(c.slice(prefix.length))),
  );
  let n = 1;
  while (used.has(n)) n += 1;
  return `${prefix}${String(n).padStart(4, '0')}`;
}
