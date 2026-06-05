import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { X, CheckCircle2, Undo2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';

interface BaseProps {
  open: boolean;
  onClose: () => void;
}

interface ApproveModalProps extends BaseProps {
  variant: 'approve';
  onConfirm: () => void;
}

interface ReturnModalProps extends BaseProps {
  variant: 'return';
  onConfirm: (reason: string) => void;
}

type CaseActionModalProps = ApproveModalProps | ReturnModalProps;

/**
 * Approve / Return modal — used by the Case Review screen.
 * Returns the case to the assistant (variant="return") with a reason,
 * or approves it (variant="approve").
 */
export function CaseActionModal(props: CaseActionModalProps) {
  const { t } = useTranslation();
  const [reason, setReason] = useState('');
  const reasonRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (props.open) {
      setReason('');
      // Autofocus the reason field for the return modal
      setTimeout(() => {
        reasonRef.current?.focus();
      }, 50);
    }
  }, [props.open]);

  if (!props.open) return null;

  const handleConfirm = () => {
    if (props.variant === 'approve') {
      props.onConfirm();
    } else {
      if (!reason.trim()) return;
      props.onConfirm(reason.trim());
    }
  };

  const isReturn = props.variant === 'return';
  const canConfirm = isReturn ? reason.trim().length > 0 : true;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <button
        type="button"
        aria-label={t('common.close')}
        className="absolute inset-0 bg-ink/40 cursor-default"
        onClick={props.onClose}
      />
      {/* Panel */}
      <div className="relative w-full max-w-lg bg-white border border-outline-soft rounded-lg shadow-floating p-6">
        <button
          type="button"
          onClick={props.onClose}
          aria-label={t('common.close')}
          className="absolute top-3 right-3 h-8 w-8 rounded-md inline-flex items-center justify-center text-ink-muted hover:bg-surface-container-low hover:text-ink transition-colors"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-start gap-3 mb-4">
          <div
            className={cn(
              'h-10 w-10 rounded-md inline-flex items-center justify-center shrink-0',
              isReturn ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-600',
            )}
          >
            {isReturn ? <Undo2 className="h-5 w-5" /> : <CheckCircle2 className="h-5 w-5" />}
          </div>
          <div className="min-w-0">
            <h3 className="text-title-lg text-ink mb-1">
              {t(
                isReturn
                  ? 'caseMgmt.detail.returnModal.title'
                  : 'caseMgmt.detail.approveModal.title',
              )}
            </h3>
            <p className="text-body-md text-ink-muted">
              {t(
                isReturn
                  ? 'caseMgmt.detail.returnModal.body'
                  : 'caseMgmt.detail.approveModal.body',
              )}
            </p>
          </div>
        </div>

        {isReturn && (
          <div className="mb-4">
            <label
              htmlFor="return-reason"
              className="text-mono text-ink-muted block mb-1.5"
            >
              {t('caseMgmt.detail.returnModal.reasonLabel')}
            </label>
            <textarea
              id="return-reason"
              ref={reasonRef}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={4}
              placeholder={t('caseMgmt.detail.returnModal.reasonPlaceholder')}
              className="w-full rounded-md border border-outline-soft bg-white text-body-md text-ink placeholder:text-ink-muted p-3 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15 transition-colors"
            />
            {reason.trim().length === 0 && (
              <p className="mt-1.5 text-caption text-amber-700 inline-flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                {t('common.required')}
              </p>
            )}
          </div>
        )}

        <div className="flex items-center justify-end gap-3">
          <Button variant="ghost" onClick={props.onClose}>
            {t('common.cancel')}
          </Button>
          <Button
            variant={isReturn ? 'secondary' : 'primary'}
            onClick={handleConfirm}
            disabled={!canConfirm}
          >
            {t(
              isReturn
                ? 'caseMgmt.detail.returnModal.confirm'
                : 'caseMgmt.detail.approveModal.confirm',
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
