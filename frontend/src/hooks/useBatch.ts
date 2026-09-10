/**
 * Batch Processing State Management Hooks
 * =======================================
 * Architecture Role:
 *   Encapsulates React Query queries and mutations for the batch spreadsheet workflow:
 *   - useBatchPreview: Loads and caches workbook preview data and sheet classification.
 *   - useBatchStatus: Polls real-time batch execution state every 1.5s while active.
 *   - useStartBatch: Triggers asynchronous batch execution and invalidates downstream caches.
 *   - useUploadBatch: Manages Excel file uploads to the backend.
 *   - useConfirmMapping: Persists confirmed column-to-field mappings and active sheet selection.
 *   - useResetBatch: Clears current batch job state and resets the workspace.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { BatchPreviewResponse, BatchStatusResponse, ColumnMapping } from '../types/sds';

export function useBatchPreview(filePath?: string) {
  return useQuery<BatchPreviewResponse>({
    queryKey: ['batch', 'preview', filePath],
    queryFn: () => api.getBatchPreview(filePath),
    staleTime: 5000,
  });
}

export function useBatchStatus() {
  return useQuery<BatchStatusResponse>({
    queryKey: ['batch', 'status'],
    queryFn: api.getBatchStatus,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && data.status === 'running') {
        return 1500; // Poll every 1.5s while actively executing LangGraph batch
      }
      return false;
    },
  });
}

export function useStartBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.startBatch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['batch', 'preview'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      queryClient.invalidateQueries({ queryKey: ['history'] });
      queryClient.invalidateQueries({ queryKey: ['review'] });
    },
  });
}

export function useUploadBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => api.uploadBatchFile(file),
    onSuccess: (data) => {
      queryClient.setQueryData(['batch', 'preview', undefined], data);
      queryClient.invalidateQueries({ queryKey: ['batch', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['batch', 'preview'] });
      queryClient.invalidateQueries({ queryKey: ['health'] });
    },
  });
}

export function useConfirmMapping() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mapping: ColumnMapping) => api.confirmColumnMapping(mapping),
    onSuccess: (data) => {
      queryClient.setQueryData(['batch', 'preview', undefined], data);
      queryClient.invalidateQueries({ queryKey: ['batch', 'preview'] });
    },
  });
}

export function useSelectDefaultBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.selectDefaultBatchFile,
    onSuccess: (data) => {
      queryClient.setQueryData(['batch', 'preview', undefined], data);
      queryClient.invalidateQueries({ queryKey: ['batch', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['batch', 'preview'] });
      queryClient.invalidateQueries({ queryKey: ['health'] });
    },
  });
}

export function useResetBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.resetBatch,
    onSuccess: (data) => {
      queryClient.setQueryData(['batch', 'preview', undefined], data);
      queryClient.invalidateQueries({ queryKey: ['batch', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['batch', 'preview'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      queryClient.invalidateQueries({ queryKey: ['history'] });
      queryClient.invalidateQueries({ queryKey: ['review'] });
    },
  });
}
