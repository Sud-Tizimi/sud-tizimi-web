/**
 * Auth shell — bare layout used by /login and /register. No sidebar, no
 * topbar; just a centred card on the page background.
 */
import { type ReactNode } from 'react';

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-surface flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center mb-8">
          <img
            src="/brand/faysal-ai-logo-horizontal.svg"
            alt="Faysal AI"
            className="h-14 w-auto max-w-full"
          />
        </div>
        {children}
      </div>
    </div>
  );
}
