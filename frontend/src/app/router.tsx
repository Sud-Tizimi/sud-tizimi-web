import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { Dashboard } from '@/pages/Dashboard';
import { Sessions } from '@/pages/Sessions';
import { Cases } from '@/pages/Cases';
// CP2 FEATURE — HIDDEN FOR MVP — ENABLE AFTER CHECKPOINT 1
// import { ComingSoon } from '@/pages/ComingSoon';
// import { CaseDetails } from '@/pages/CaseDetails'; // CP2
// import { OcrProcessing } from '@/pages/OcrProcessing'; // CP2
// import { AiSummaryCenter } from '@/pages/AiSummaryCenter'; // CP2
// import { GeneratedDocuments } from '@/pages/GeneratedDocuments'; // CP2
// import { NotificationsCenter } from '@/pages/NotificationsCenter'; // CP2
// import { PlatformSettings } from '@/pages/PlatformSettings'; // CP2
// import { MobileDashboard } from '@/pages/mobile/MobileDashboard'; // CP2
// import { MobileSessionMonitoring } from '@/pages/mobile/MobileSessionMonitoring'; // CP2
// import { MobileShell } from '@/components/layout/MobileShell'; // CP2
import { ENABLED_FEATURES } from '@/lib/featureFlags';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },

      // CP1 — MVP
      { path: 'dashboard', element: <Dashboard /> },
      ...(ENABLED_FEATURES.sessions ? [{ path: 'sessions', element: <Sessions /> }] : []),
      ...(ENABLED_FEATURES.cases ? [{ path: 'cases', element: <Cases /> }] : []),

      // CP2 FEATURE — HIDDEN FOR MVP — ENABLE AFTER CHECKPOINT 1
      // { path: 'cases/:id', element: <CaseDetails /> },
      // { path: 'documents', element: <OcrProcessing /> },
      // { path: 'documents/generated', element: <GeneratedDocuments /> },
      // { path: 'ai', element: <AiSummaryCenter /> },
      // { path: 'notifications', element: <NotificationsCenter /> },
      // { path: 'settings', element: <PlatformSettings /> },
      //
      // Mobile (CP2 — separate shell)
      // {
      //   path: 'mobile',
      //   element: <MobileShell />,
      //   children: [
      //     { index: true, element: <Navigate to="/mobile/dashboard" replace /> },
      //     { path: 'dashboard', element: <MobileDashboard /> },
      //     { path: 'sessions', element: <MobileSessionMonitoring /> },
      //   ],
      // },

      { path: '*', element: <Navigate to="/dashboard" replace /> },
    ],
  },
]);
