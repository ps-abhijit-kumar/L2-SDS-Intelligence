/**
 * System KPI & Telemetry Statistics Hook
 * =====================================
 * Architecture Role:
 *   Polls aggregate platform performance metrics from GET /api/stats every 15s,
 *   powering the top-level KPI grid and performance analytics charts.
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: () => api.getStats(),
    refetchInterval: 15000,
  });
}
