/**
 * Auth shell — bare layout used by /login and /register. No sidebar, no
 * topbar; just a centred card on the page background.
 */
import { type ReactNode } from 'react';
import { Scale } from 'lucide-react';

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-surface flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="h-10 w-10 rounded-md bg-primary-500 text-white inline-flex items-center justify-center">
            <Scale className="h-5 w-5" />
          </div>
          <span className="text-headline-md text-ink">Sud-Tizimi</span>
        </div>
        {children}
      </div>
    </div>
  );
}
