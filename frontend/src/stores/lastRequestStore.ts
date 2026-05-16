import { create } from 'zustand';

export interface LastRequestInfo {
  requestId: string;
  traceparent: string | null;
  method: string;
  url: string;
  status: number | null;
  timestamp: number;
}

interface LastRequestState {
  last: LastRequestInfo | null;
  setLast: (info: LastRequestInfo) => void;
  clear: () => void;
}

export const useLastRequestStore = create<LastRequestState>((set) => ({
  last: null,
  setLast: (info) => set({ last: info }),
  clear: () => set({ last: null }),
}));

export const shortId = (id: string, length = 8): string =>
  id.length <= length ? id : id.slice(0, length);
