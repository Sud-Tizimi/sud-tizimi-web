import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Construction, ArrowLeft } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface ComingSoonProps {
  moduleKey?: string;
}

export function ComingSoon({ moduleKey }: ComingSoonProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <div className="p-6 md:p-8 max-w-2xl mx-auto">
      <Card padding="lg" className="text-center">
        <div className="mx-auto h-12 w-12 rounded-full bg-primary-50 text-primary-500 inline-flex items-center justify-center mb-4">
          <Construction className="h-6 w-6" />
        </div>
        <h2 className="text-headline-md text-ink mb-2">
          {moduleKey ? t(moduleKey) : t('common.comingSoon')}
        </h2>
        <p className="text-body-md text-ink-muted mb-6">{t('common.comingSoonDesc')}</p>
        <Button
          variant="secondary"
          leftIcon={<ArrowLeft className="h-4 w-4" />}
          onClick={() => navigate('/dashboard')}
        >
          {t('nav.dashboard')}
        </Button>
      </Card>
    </div>
  );
}
