/**
 * Audit History & Review Queue Query Hooks
 * ========================================
 * Architecture Role:
 *   Provides query hooks for audit logging, review queue monitoring, and trace visualization:
 *   - useHistory: Fetches filtered, paginated execution history records.
 *   - useHistoryDetail: Loads full diagnostic and evidence trace for a specific record.
 *   - useReviewQueue: Polls human-in-the-loop review queue (NEEDS REVIEW) every 15s.
 *   - useLatestTrace: Polls latest agent workflow state every 10s for trace visualization.
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export function useHistory(params?: {
  status?: string;
  query?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ['history', params],
    queryFn: () => api.getHistory(params),
  });
}

export function useHistoryDetail(id: string | null) {
  return useQuery({
    queryKey: ['historyDetail', id],
    queryFn: () => (id ? api.getHistoryDetail(id) : null),
    enabled: !!id,
  });
}

export function useReviewQueue() {
  return useQuery({
    queryKey: ['reviewQueue'],
    queryFn: () => api.getReviewQueue(),
    refetchInterval: 15000,
  });
}

export function useLatestTrace() {
  return useQuery({
    queryKey: ['latestTrace'],
    queryFn: () => api.getLatestTrace(),
    refetchInterval: 10000,
  });
}
