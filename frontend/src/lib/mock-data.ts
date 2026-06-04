import type { SessionStatus, SpeakerRole } from '@/types/domain';

export type HealthState = 'online' | 'degraded' | 'offline';

export interface SystemStatus {
  state: HealthState;
  uptimeHours: number;
  sttLatencyMs: number;
  sttEngine: string;
  diarizationEngine: string;
  speakerIdState: HealthState;
  activeSessions: number;
}

export const SYSTEM_STATUS: SystemStatus = {
  state: 'online',
  uptimeHours: 312.4,
  sttLatencyMs: 184,
  sttEngine: 'Whisper-Large v3',
  diarizationEngine: 'pyannote 3.1',
  speakerIdState: 'online',
  activeSessions: 1,
};

export interface RecentSession {
  id: string;
  caseNumber: string;
  title: string;
  judge: string;
  startedAt: string;
  durationSec: number;
  status: SessionStatus;
}

export const MOCK_RECENT_SESSIONS: RecentSession[] = [
  {
    id: 'sess-2401',
    caseNumber: 'CASE-2026-0241',
    title: 'Abdullayev vs. Tashkent City Administration',
    judge: 'Hon. Rustam Karimov',
    startedAt: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    durationSec: 12 * 60,
    status: 'live',
  },
  {
    id: 'sess-2400',
    caseNumber: 'CASE-2026-0239',
    title: 'Nazarova — inheritance dispute',
    judge: 'Hon. Dilshod Yusupov',
    startedAt: new Date(Date.now() - 1 * 3600 * 1000 - 24 * 60 * 1000).toISOString(),
    durationSec: 1 * 3600 + 22 * 60,
    status: 'completed',
  },
  {
    id: 'sess-2399',
    caseNumber: 'CASE-2026-0235',
    title: 'Procurement complaint #14/26',
    judge: 'Hon. Malika Rakhimova',
    startedAt: new Date(Date.now() - 3 * 3600 * 1000).toISOString(),
    durationSec: 2 * 3600 + 6 * 60,
    status: 'completed',
  },
  {
    id: 'sess-2398',
    caseNumber: 'CASE-2026-0231',
    title: 'Mirzaev — labour dispute',
    judge: 'Hon. Rustam Karimov',
    startedAt: new Date(Date.now() - 5 * 3600 * 1000).toISOString(),
    durationSec: 38 * 60,
    status: 'completed',
  },
  {
    id: 'sess-2397',
    caseNumber: 'CASE-2026-0228',
    title: 'Contractual dispute — LLC "Bunyodkor"',
    judge: 'Hon. Dilshod Yusupov',
    startedAt: new Date(Date.now() - 7 * 3600 * 1000).toISOString(),
    durationSec: 1 * 3600 + 51 * 60,
    status: 'completed',
  },
];

export interface CaseRow {
  id: string;
  caseNumber: string;
  title: string;
  judge: string;
  parties: string;
  hearingDate: string;
  status: 'open' | 'in_hearing' | 'adjourned' | 'closed';
}

export const MOCK_CASES: CaseRow[] = [
  {
    id: 'case-0241',
    caseNumber: 'CASE-2026-0241',
    title: 'Abdullayev vs. Tashkent City Administration',
    judge: 'Hon. Rustam Karimov',
    parties: 'A. Abdullayev · Tashkent City Admin',
    hearingDate: '2026-06-04',
    status: 'in_hearing',
  },
  {
    id: 'case-0239',
    caseNumber: 'CASE-2026-0239',
    title: 'Nazarova — inheritance dispute',
    judge: 'Hon. Dilshod Yusupov',
    parties: 'M. Nazarova · D. Nazarov',
    hearingDate: '2026-06-05',
    status: 'open',
  },
  {
    id: 'case-0235',
    caseNumber: 'CASE-2026-0235',
    title: 'Procurement complaint #14/26',
    judge: 'Hon. Malika Rakhimova',
    parties: 'LLC "Tashkent Stroy" · Ministry of Finance',
    hearingDate: '2026-06-06',
    status: 'open',
  },
  {
    id: 'case-0231',
    caseNumber: 'CASE-2026-0231',
    title: 'Mirzaev — labour dispute',
    judge: 'Hon. Rustam Karimov',
    parties: 'S. Mirzaev · JSC "Uzbekneftegaz"',
    hearingDate: '2026-06-03',
    status: 'closed',
  },
  {
    id: 'case-0228',
    caseNumber: 'CASE-2026-0228',
    title: 'Contractual dispute — LLC "Bunyodkor"',
    judge: 'Hon. Dilshod Yusupov',
    parties: 'LLC "Bunyodkor" · LLC "Kapremstroy"',
    hearingDate: '2026-06-03',
    status: 'closed',
  },
  {
    id: 'case-0224',
    caseNumber: 'CASE-2026-0224',
    title: 'Aliyev — administrative violation',
    judge: 'Hon. Malika Rakhimova',
    parties: 'R. Aliyev · MVD inspectorate',
    hearingDate: '2026-06-02',
    status: 'adjourned',
  },
  {
    id: 'case-0219',
    caseNumber: 'CASE-2026-0219',
    title: 'Salimov — property rights',
    judge: 'Hon. Dilshod Yusupov',
    parties: 'B. Salimov · Khokimiyat of Yunusabad',
    hearingDate: '2026-06-09',
    status: 'open',
  },
  {
    id: 'case-0214',
    caseNumber: 'CASE-2026-0214',
    title: 'Yusupova — family matter',
    judge: 'Hon. Rustam Karimov',
    parties: 'N. Yusupova · A. Yusupov',
    hearingDate: '2026-06-10',
    status: 'open',
  },
];

export interface SpeakerDef {
  id: string;
  label: string;
  role: SpeakerRole;
}

export const DEMO_SPEAKERS: SpeakerDef[] = [
  { id: 'sp-00', label: 'Hon. R. Karimov', role: 'judge' },
  { id: 'sp-01', label: 'A. Abdullayev', role: 'plaintiff' },
  { id: 'sp-02', label: 'Tashkent City Admin', role: 'defendant' },
  { id: 'sp-03', label: 'L. Tursunov', role: 'lawyer' },
];
