/**
 * Register page — email, password, full name, role, optional court.
 */
import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, Button } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { api, ApiError } from '@/lib/api';
import type { UserPublic, LoginResponse } from '@/types/domain';

export function Register() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { setSession } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<'judge' | 'assistant'>('assistant');
  const [court, setCourt] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api<{ user: UserPublic }>('/api/auth/register', {
        method: 'POST',
        body: {
          email,
          password,
          fullName,
          role,
          court: role === 'judge' && court.trim() ? court.trim() : null,
        },
      });
      // After register, log in automatically.
      const form = new FormData();
      form.append('username', email);
      form.append('password', password);
      const r = await fetch('/api/auth/login', { method: 'POST', body: form });
      if (!r.ok) {
        throw new ApiError(r.status, 'login_after_register_failed');
      }
      const data = (await r.json()) as LoginResponse;
      setSession(data.accessToken, data.user);
      navigate('/dashboard', { replace: true });
    } catch (e) {
      const detail = e instanceof ApiError ? e.detail : 'networkError';
      const key =
        detail === 'email_taken'
          ? 'auth.errors.emailTaken'
          : detail === 'weakPassword'
            ? 'auth.errors.weakPassword'
            : 'auth.login.networkError';
      setError(t(key));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card padding="lg">
      <CardHeader>
        <CardTitle>{t('auth.register.title')}</CardTitle>
        <CardDescription>{t('auth.register.subtitle')}</CardDescription>
      </CardHeader>

      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-caption font-medium text-ink">{t('auth.register.fullName')}</span>
          <input
            type="text"
            required
            autoComplete="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="h-10 px-3 rounded-md border border-outline-soft bg-white text-body-md text-ink placeholder:text-ink-muted focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15 transition-colors"
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-caption font-medium text-ink">{t('auth.register.email')}</span>
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
          <span className="text-caption font-medium text-ink">{t('auth.register.password')}</span>
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="h-10 px-3 rounded-md border border-outline-soft bg-white text-body-md text-ink placeholder:text-ink-muted focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15 transition-colors"
          />
        </label>

        <fieldset className="flex flex-col gap-1.5">
          <legend className="text-caption font-medium text-ink mb-1">
            {t('auth.register.role')}
          </legend>
          <div className="grid grid-cols-2 gap-2">
            <label
              className={`flex items-center gap-2 p-3 rounded-md border cursor-pointer transition-colors ${
                role === 'judge'
                  ? 'border-primary-500 bg-primary-50/40'
                  : 'border-outline-soft hover:border-outline'
              }`}
            >
              <input
                type="radio"
                name="role"
                value="judge"
                checked={role === 'judge'}
                onChange={() => setRole('judge')}
                className="accent-primary-500"
              />
              <span className="text-body-md text-ink">{t('auth.register.role.judge')}</span>
            </label>
            <label
              className={`flex items-center gap-2 p-3 rounded-md border cursor-pointer transition-colors ${
                role === 'assistant'
                  ? 'border-primary-500 bg-primary-50/40'
                  : 'border-outline-soft hover:border-outline'
              }`}
            >
              <input
                type="radio"
                name="role"
                value="assistant"
                checked={role === 'assistant'}
                onChange={() => setRole('assistant')}
                className="accent-primary-500"
              />
              <span className="text-body-md text-ink">{t('auth.register.role.assistant')}</span>
            </label>
          </div>
        </fieldset>

        {role === 'judge' && (
          <label className="flex flex-col gap-1.5">
            <span className="text-caption font-medium text-ink">
              {t('auth.register.court')}
            </span>
            <input
              type="text"
              value={court}
              onChange={(e) => setCourt(e.target.value)}
              className="h-10 px-3 rounded-md border border-outline-soft bg-white text-body-md text-ink placeholder:text-ink-muted focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15 transition-colors"
            />
          </label>
        )}

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
          disabled={submitting || !email || !password || !fullName}
        >
          {submitting ? '…' : t('auth.register.submit')}
        </Button>

        <p className="text-caption text-ink-muted text-center">
          {t('auth.register.loginPrompt')}{' '}
          <Link to="/login" className="text-primary-600 hover:underline font-medium">
            {t('auth.login.submit')}
          </Link>
        </p>
      </form>
    </Card>
  );
}
