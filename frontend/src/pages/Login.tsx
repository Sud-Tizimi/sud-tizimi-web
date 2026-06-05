/**
 * Login page — email + password. Posts as application/x-www-form-urlencoded
 * (FastAPI's OAuth2PasswordRequestForm expects that) by appending to
 * FormData.
 *
 * On success: stores token + user via authStore, navigates to /dashboard
 * (or to the `next` query param if set).
 */
import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, Button, Badge } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { ApiError } from '@/lib/api';

export function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { setSession } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      // Login is form-encoded for OAuth2PasswordRequestForm on the backend.
      const form = new FormData();
      form.append('username', email);
      form.append('password', password);
      const r = await fetch('/api/auth/login', {
        method: 'POST',
        body: form,
      });
      if (!r.ok) {
        // Try to extract a stable error code from the JSON body.
        let code = 'invalid_credentials';
        try {
          const parsed = (await r.json()) as { detail?: string };
          if (parsed && typeof parsed.detail === 'string') code = parsed.detail;
        } catch {
          /* keep default */
        }
        throw new ApiError(r.status, code);
      }
      const data = (await r.json()) as {
        accessToken: string;
        tokenType: string;
        user: import('@/types/domain').UserPublic;
      };
      setSession(data.accessToken, data.user);
      const next = params.get('next');
      navigate(next ? decodeURIComponent(next) : '/dashboard', { replace: true });
    } catch (e) {
      const detail = e instanceof ApiError ? e.detail : 'networkError';
      // Map well-known backend codes to translation keys.
      const key =
        detail === 'invalid_credentials'
          ? 'auth.login.invalidCredentials'
          : 'auth.login.networkError';
      setError(t(key));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card padding="lg">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>{t('auth.login.title')}</CardTitle>
            <CardDescription>{t('auth.login.subtitle')}</CardDescription>
          </div>
          <Badge variant="info">MVP</Badge>
        </div>
      </CardHeader>

      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-caption font-medium text-ink">{t('auth.login.email')}</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="h-10 px-3 rounded-md border border-outline-soft bg-white text-body-md text-ink placeholder:text-ink-muted focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15 transition-colors"
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-caption font-medium text-ink">{t('auth.login.password')}</span>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="h-10 px-3 rounded-md border border-outline-soft bg-white text-body-md text-ink placeholder:text-ink-muted focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15 transition-colors"
          />
        </label>

        {error && (
          <div
            role="alert"
            className="rounded-md border border-red-200 bg-red-50 p-3 text-body-md text-error"
          >
            {error}
          </div>
        )}

        <Button
          type="submit"
          size="lg"
          disabled={submitting || !email || !password}
        >
          {submitting ? '…' : t('auth.login.submit')}
        </Button>

        <p className="text-caption text-ink-muted text-center">
          {t('auth.login.registerPrompt')}{' '}
          <Link to="/register" className="text-primary-600 hover:underline font-medium">
            {t('auth.login.register')}
          </Link>
        </p>
      </form>
    </Card>
  );
}
