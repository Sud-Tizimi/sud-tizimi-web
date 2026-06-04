import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { SYSTEM_STATUS } from '@/lib/mock-data';

export function AppShell() {
  return (
    <div className="min-h-screen flex bg-surface">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        <TopBar systemOnline={SYSTEM_STATUS.state === 'online'} uptimeHours={SYSTEM_STATUS.uptimeHours} />
        <main className="flex-1 min-w-0 overflow-x-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
