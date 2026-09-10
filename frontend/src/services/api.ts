/**
 * Frontend API Service Layer
 * ===========================
 * Architecture Role:
 *   Centralized HTTP client managing communication between the React/TypeScript UI
 *   and the FastAPI backend endpoints (/api/*).
 *
 * Capabilities:
 *   - Health & Telemetry: Real-time backend system status and LLM connectivity checks.
 *   - Interactive Search: Direct single-query chemical SDS retrieval and verification.
 *   - Multi-Sheet Batch Management: Workbook upload, sheet inspection, mapping confirmation,
 *     batch job dispatch, polling, and verified Excel file export.
 *   - Audit & History: Historical trace queries, review queue fetching, and live agent telemetry.
 */

import {
  SDSSearchRequest,
  SDSSearchResponse,
  HealthStatus,
  StatsResponse,
  HistoryListResponse,
  HistoryItem,
  BatchPreviewResponse,
  BatchStatusResponse,
  ColumnMapping,
} from '../types/sds';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = 'Network response was not ok';
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorJson.message || errorDetail;
    } catch {
      errorDetail = `HTTP Error ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Health & Subsystem Telemetry
  async getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse<HealthStatus>(res);
  },

  // Single SDS Search
  async searchSDS(payload: SDSSearchRequest): Promise<SDSSearchResponse> {
    const res = await fetch(`${API_BASE}/sds/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<SDSSearchResponse>(res);
  },

  // Batch Processing & Multi-Sheet Excel Management (PRIMARY WORKFLOW)
  async getBatchPreview(filePath?: string): Promise<BatchPreviewResponse> {
    const url = filePath
      ? `${API_BASE}/batch/preview?file_path=${encodeURIComponent(filePath)}`
      : `${API_BASE}/batch/preview`;
    const res = await fetch(url);
    return handleResponse<BatchPreviewResponse>(res);
  },

  async uploadBatchFile(file: File): Promise<BatchPreviewResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/batch/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<BatchPreviewResponse>(res);
  },

  async confirmColumnMapping(mapping: ColumnMapping): Promise<BatchPreviewResponse> {
    const res = await fetch(`${API_BASE}/batch/confirm-mapping`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(mapping),
    });
    return handleResponse<BatchPreviewResponse>(res);
  },

  async selectDefaultBatchFile(): Promise<BatchPreviewResponse> {
    const res = await fetch(`${API_BASE}/batch/select-default`, {
      method: 'POST',
    });
    return handleResponse<BatchPreviewResponse>(res);
  },

  async startBatch(): Promise<{ status: string; file_name: string; message: string }> {
    const res = await fetch(`${API_BASE}/batch/start`, {
      method: 'POST',
    });
    return handleResponse<{ status: string; file_name: string; message: string }>(res);
  },

  async getBatchStatus(): Promise<BatchStatusResponse> {
    const res = await fetch(`${API_BASE}/batch/status`);
    return handleResponse<BatchStatusResponse>(res);
  },

  async resetBatch(): Promise<BatchPreviewResponse> {
    const res = await fetch(`${API_BASE}/batch/reset`, {
      method: 'POST',
    });
    return handleResponse<BatchPreviewResponse>(res);
  },

  getBatchExportUrl(): string {
    return `${API_BASE}/batch/export`;
  },

  // Metrics & Activity Logs
  async getStats(): Promise<StatsResponse> {
    const res = await fetch(`${API_BASE}/stats`);
    return handleResponse<StatsResponse>(res);
  },

  // Audit History
  async getHistory(params?: {
    status?: string;
    query?: string;
    limit?: number;
    offset?: number;
  }): Promise<HistoryListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.append('status', params.status);
    if (params?.query) searchParams.append('query', params.query);
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.offset) searchParams.append('offset', String(params.offset));

    const url = `${API_BASE}/history?${searchParams.toString()}`;
    const res = await fetch(url);
    return handleResponse<HistoryListResponse>(res);
  },

  async getHistoryDetail(id: string): Promise<HistoryItem> {
    const res = await fetch(`${API_BASE}/history/${encodeURIComponent(id)}`);
    return handleResponse<HistoryItem>(res);
  },

  // Review Queue
  async getReviewQueue(): Promise<{ items: HistoryItem[]; total: number }> {
    const res = await fetch(`${API_BASE}/review`);
    return handleResponse<{ items: HistoryItem[]; total: number }>(res);
  },

  // Agent Trace
  async getLatestTrace(): Promise<{ trace: HistoryItem | null }> {
    const res = await fetch(`${API_BASE}/trace/latest`);
    return handleResponse<{ trace: HistoryItem | null }>(res);
  },
};
