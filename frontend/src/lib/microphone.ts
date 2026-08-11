export type MicrophoneIssue =
  | 'secure_context_required'
  | 'media_devices_unavailable'
  | 'media_recorder_unavailable'
  | 'microphone_permission_denied'
  | 'microphone_not_found'
  | 'microphone_in_use'
  | 'microphone_unavailable';

export function getMicrophoneIssue(): MicrophoneIssue | null {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') {
    return 'media_devices_unavailable';
  }
  if (!window.isSecureContext) return 'secure_context_required';
  if (!navigator.mediaDevices?.getUserMedia) return 'media_devices_unavailable';
  if (typeof MediaRecorder === 'undefined') return 'media_recorder_unavailable';
  return null;
}

export async function getUserMediaOrThrow(constraints: MediaStreamConstraints): Promise<MediaStream> {
  const issue = getMicrophoneIssue();
  if (issue) throw new Error(issue);
  return navigator.mediaDevices.getUserMedia(constraints);
}

export function toMicrophoneIssue(error: unknown): MicrophoneIssue {
  if (error instanceof Error) {
    if (isMicrophoneIssue(error.message)) return error.message;
    if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
      return 'microphone_permission_denied';
    }
    if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
      return 'microphone_not_found';
    }
    if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
      return 'microphone_in_use';
    }
  }
  return 'microphone_unavailable';
}

function isMicrophoneIssue(value: string): value is MicrophoneIssue {
  return [
    'secure_context_required',
    'media_devices_unavailable',
    'media_recorder_unavailable',
    'microphone_permission_denied',
    'microphone_not_found',
    'microphone_in_use',
    'microphone_unavailable',
  ].includes(value);
}
