/**
 * Batch Excel Processing Command Page
 * ===================================
 * Architecture Role:
 *   Main operations interface for high-throughput chemical Safety Data Sheet batch processing:
 *   - Uploads multi-sheet Excel spreadsheets.
 *   - Analyzes worksheet structures, detects column mappings, and isolates active SDS request datasets.
 *   - Monitors asynchronous batch execution progress in real time with 1.5s polling.
 *   - Displays tabular verification status with in-line confidence badges and deep detail modals.
 *   - Exports enriched Excel workbooks containing verified URLs, statuses, and reasoning.
 */

import React, { useState } from 'react';
import { Layers, RefreshCw, Download } from 'lucide-react';
import { BatchUploadCard } from '../components/batch/BatchUploadCard';
import { BatchProgressMonitor } from '../components/batch/BatchProgressMonitor';
import { BatchRequestTable } from '../components/batch/BatchRequestTable';
import { BatchDetailModal } from '../components/batch/BatchDetailModal';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { Button } from '../components/common/Button';
import {
  useBatchPreview,
  useBatchStatus,
  useStartBatch,
  useUploadBatch,
  useResetBatch,
  useConfirmMapping,
} from '../hooks/useBatch';
import { BatchRow } from '../types/sds';
import { api } from '../services/api';

export const BatchProcessingPage: React.FC = () => {
  const [selectedRow, setSelectedRow] = useState<BatchRow | null>(null);

  const { data: preview, isLoading: isPreviewLoading, error: previewError, refetch: refetchPreview } = useBatchPreview();
  const { data: batchStatus } = useBatchStatus();

  const { mutate: uploadFile, isPending: isUploading, error: uploadError } = useUploadBatch();
  const { mutate: startBatch, isPending: isStarting, error: startError } = useStartBatch();
  const { mutate: resetBatch, isPending: isResetting, error: resetError } = useResetBatch();
  const { mutate: confirmMapping, isPending: isSelectingSheet } = useConfirmMapping();

  const handleUpload = (file: File) => {
    uploadFile(file);
  };

  const handleStart = () => {
    startBatch();
  };

  const handleReset = () => {
    resetBatch();
  };

  const handleSelectSheet = (sheetName: string) => {
    confirmMapping({
      ...(preview?.column_mapping || {}),
      selected_sheets: [sheetName],
    });
  };

  const rows = preview?.rows || [];

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <Layers className="w-5 h-5 text-cyan-400" />
            <h2 className="text-xl font-black text-slate-100">
              SDS Batch Processing
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
              Sequential Agent
            </span>
          </div>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed font-sans">
            Upload an Excel workbook to extract and sequentially verify SDS documents using autonomous search and verification.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchPreview()}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh Preview
          </Button>

          <a href={api.getBatchExportUrl()} download>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Download className="w-3.5 h-3.5 text-cyan-400" />}
            >
              Export Excel
            </Button>
          </a>
        </div>
      </div>

      {/* Error Alerts */}
      {uploadError && (
        <ErrorMessage
          title="Excel Upload Failed"
          message={uploadError.message || 'Could not upload or parse the Excel file. Verify file format (.xlsx).'}
        />
      )}

      {startError && (
        <ErrorMessage
          title="Batch Execution Failed to Start"
          message={startError.message || 'Could not start batch execution. Verify Groq API key configuration in .env.'}
        />
      )}

      {resetError && (
        <ErrorMessage
          title="Failed to Reset Workbook"
          message={resetError.message || 'Error clearing workbook output columns.'}
        />
      )}

      {previewError && (
        <ErrorMessage
          title="Failed to Load Excel Workbook"
          message={previewError.message || 'Error parsing the workbook structure.'}
          onRetry={() => refetchPreview()}
        />
      )}

      {/* Upload & Control Card */}
      <BatchUploadCard
        preview={preview}
        batchStatus={batchStatus}
        onUploadFile={handleUpload}
        onSelectSheet={handleSelectSheet}
        onStartBatch={handleStart}
        onResetBatch={handleReset}
        isUploading={isUploading}
        isStarting={isStarting}
        isResetting={isResetting}
        isSelectingSheet={isSelectingSheet}
      />

      {/* Live Batch Execution Progress Monitor */}
      <BatchProgressMonitor status={batchStatus} />

      {/* Excel Request Rows Preview Table */}
      <BatchRequestTable
        rows={rows}
        isLoading={isPreviewLoading}
        onSelectRow={(row) => setSelectedRow(row)}
      />

      {/* Row Detail Modal */}
      <BatchDetailModal
        row={selectedRow}
        onClose={() => setSelectedRow(null)}
      />
    </div>
  );
};
