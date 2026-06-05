import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell, AuthShell, RequireAuth } from '@/components/layout';
import { Dashboard } from '@/pages/Dashboard';
import { Sessions } from '@/pages/Sessions';
import { Cases } from '@/pages/Cases';
import { CaseDetail } from '@/pages/CaseDetail';
import { CaseCreate } from '@/pages/CaseCreate';
import { CaseEdit } from '@/pages/CaseEdit';
import { Login } from '@/pages/Login';
import { Register } from '@/pages/Register';
import { Upload } from '@/pages/Upload';
import { Documents } from '@/pages/Documents';
import { OcrProcessing } from '@/pages/OcrProcessing';
// CP2 FEATURE — HIDDEN FOR MVP — ENABLE AFTER CHECKPOINT 1
// import { ComingSoon } from '@/pages/ComingSoon';
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
  // ---- Public auth routes (no AppShell, no RequireAuth) ----
  { path: '/login', element: <AuthShell><Login /></AuthShell> },
  { path: '/register', element: <AuthShell><Register /></AuthShell> },

  // ---- Authed app shell ----
  {
    path: '/',
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },

      // CP1 — MVP
      { path: 'dashboard', element: <Dashboard /> },
      ...(ENABLED_FEATURES.sessions ? [{ path: 'sessions', element: <Sessions /> }] : []),
      ...(ENABLED_FEATURES.cases ? [{ path: 'cases', element: <Cases /> }] : []),

      // Case Management & Document Review (case-management.md)
      ...(ENABLED_FEATURES.caseDetails
        ? [
            { path: 'cases/new', element: <CaseCreate /> },
            { path: 'cases/:id', element: <CaseDetail /> },
            { path: 'cases/:id/edit', element: <CaseEdit /> },
          ]
        : []),

      // Phase B — standalone upload + library pages
      ...(ENABLED_FEATURES.upload ? [{ path: 'upload', element: <Upload /> }] : []),
      ...(ENABLED_FEATURES.documentsLibrary
        ? [{ path: 'documents', element: <Documents /> }]
        : []),
      ...(ENABLED_FEATURES.ocrProcessing ? [{ path: 'ocr', element: <OcrProcessing /> }] : []),

      // CP2 FEATURE — HIDDEN FOR MVP — ENABLE AFTER CHECKPOINT 1
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
