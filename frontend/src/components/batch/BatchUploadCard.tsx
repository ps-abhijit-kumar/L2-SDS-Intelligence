import React, { useRef, useState } from 'react';
import { Upload, FileSpreadsheet, Play, RotateCcw, Download, Loader2 } from 'lucide-react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { BatchPreviewResponse, BatchStatusResponse } from '../../types/sds';
import { api } from '../../services/api';

interface BatchUploadCardProps {
  preview?: BatchPreviewResponse;
  batchStatus?: BatchStatusResponse;
  onUploadFile: (file: File) => void;
  onSelectSheet?: (sheetName: string) => void;
  onSelectDefault?: () => void;
  onStartBatch: () => void;
  onResetBatch: () => void;
  isUploading?: boolean;
  isStarting?: boolean;
  isResetting?: boolean;
  isSelectingSheet?: boolean;
}

export const BatchUploadCard: React.FC<BatchUploadCardProps> = ({
  preview,
  batchStatus,
  onUploadFile,
  onSelectSheet,
  onStartBatch,
  onResetBatch,
  isUploading = false,
  isStarting = false,
  isResetting = false,
  isSelectingSheet = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const candidateSheets = (preview?.sheets_summary || []).filter(
    (s) => s.valid_requests > 0 && s.classification !== 'SUMMARY'
  );

  const [selectedSheet, setSelectedSheet] = useState<string>(
    preview?.selected_sheets?.[0] || candidateSheets[0]?.sheet_name || ''
  );

  React.useEffect(() => {
    if (preview?.selected_sheets && preview.selected_sheets.length > 0) {
      setSelectedSheet(preview.selected_sheets[0]);
    } else if (candidateSheets.length > 0) {
      setSelectedSheet(candidateSheets[0].sheet_name);
    }
  }, [preview?.selected_sheets, preview?.sheets_summary]);

  const isRunning = batchStatus?.status === 'running';
  
  const validRequests = preview?.sds_requests_count ?? preview?.total_rows ?? 0;
  const pendingRequests = preview?.pending_requests_count ?? preview?.pending_rows ?? 0;
  const completedRequests = preview?.completed_requests_count ?? preview?.completed_rows ?? 0;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const lowerName = file.name.toLowerCase();
      if (lowerName.endsWith('.xlsx') || lowerName.endsWith('.xls')) {
        onUploadFile(file);
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      onUploadFile(file);
    }
    e.target.value = '';
  };

  return (
    <Card variant="elevated" className="border-cyan-500/20 shadow-xl shadow-black/50 space-y-6">
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-6">
        {/* Left: Drag & Drop Dropzone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => {
            if (!isUploading) {
              fileInputRef.current?.click();
            }
          }}
          className={`flex-1 border-2 border-dashed rounded-2xl p-6 transition-all duration-200 cursor-pointer flex flex-col items-center justify-center text-center group ${
            isDragOver
              ? 'border-cyan-400 bg-cyan-500/10 shadow-glow-cyan'
              : 'border-white/[0.1] hover:border-cyan-500/40 bg-[#070A12]/80 hover:bg-[#070A12]'
          } ${isUploading ? 'opacity-70 pointer-events-none' : ''}`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx, .xls, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
            onChange={handleFileChange}
            className="hidden"
          />

          <div className="w-12 h-12 rounded-2xl bg-[#0B1020] border border-cyan-500/30 shadow-glow-cyan flex items-center justify-center text-cyan-400 mb-3 group-hover:scale-105 transition-transform">
            {isUploading ? (
              <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
            ) : (
              <Upload className="w-5 h-5" />
            )}
          </div>

          <h4 className="text-sm font-bold text-slate-100 mb-1">
            {isUploading ? 'Extracting SDS Requests...' : 'Upload SDS Workbook'}
          </h4>
          <p className="text-xs text-slate-400 max-w-sm mb-3">
            Drag & drop an Excel (<code className="text-cyan-300 font-mono">.xlsx</code>) workbook to automatically extract and verify SDS chemical requests.
          </p>

          <span className="text-[10px] font-mono font-bold text-cyan-400 bg-cyan-950/80 px-2.5 py-1 rounded-full border border-cyan-500/30">
            Excel (.xlsx) Ingestion
          </span>
        </div>

        {/* Right: Active Workbook Details & Batch Action Controller */}
        <div className="lg:w-96 flex flex-col justify-between p-5 rounded-2xl bg-[#070A12] border border-white/[0.08] space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500">
                Active Workbook
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                {preview?.file_name ? 'Active Session' : 'No Workbook Active'}
              </span>
            </div>

            <div className="p-3 bg-[#0B1020] rounded-xl border border-white/[0.08] flex items-center gap-3">
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                preview?.file_name
                  ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
                  : 'bg-slate-800/40 border border-slate-700/40 text-slate-500'
              }`}>
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-slate-100 truncate">
                  {preview?.file_name || 'No workbook loaded'}
                </p>
                <p className="text-[10px] font-mono text-slate-400">
                  {preview?.file_name
                    ? preview.selected_sheets && preview.selected_sheets.length > 0
                      ? `${preview.selected_sheets[0]} (${validRequests} SDS Requests)`
                      : candidateSheets.length > 1
                      ? 'Select a request set below'
                      : `${validRequests} SDS Requests Detected`
                    : 'Upload an Excel (.xlsx) workbook above'}
                </p>
              </div>
            </div>

            {/* Accurate Metrics Display */}
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="p-2 bg-[#0B1020] rounded-lg border border-white/[0.06]">
                <span className="text-[9px] font-mono uppercase text-slate-500 block">SDS Requests</span>
                <span className="text-sm font-mono font-bold text-slate-200">{preview?.file_name ? validRequests : 0}</span>
              </div>
              <div className="p-2 bg-[#0B1020] rounded-lg border border-white/[0.06]">
                <span className="text-[9px] font-mono uppercase text-cyan-500 block">Pending</span>
                <span className="text-sm font-mono font-bold text-cyan-400">{preview?.file_name ? pendingRequests : 0}</span>
              </div>
              <div className="p-2 bg-[#0B1020] rounded-lg border border-white/[0.06]">
                <span className="text-[9px] font-mono uppercase text-emerald-500 block">Resolved</span>
                <span className="text-sm font-mono font-bold text-emerald-400">{preview?.file_name ? completedRequests : 0}</span>
              </div>
            </div>
          </div>

          {/* Action CTAs */}
          <div className="space-y-2 pt-2 border-t border-white/[0.06]">
            <Button
              variant="primary"
              size="md"
              onClick={onStartBatch}
              isLoading={isStarting || isRunning}
              disabled={!preview?.file_name || isRunning || validRequests === 0 || pendingRequests === 0}
              leftIcon={<Play className="w-4 h-4 fill-current" />}
              className="w-full shadow-glow-cyan"
            >
              {isRunning
                ? 'Processing Batch...'
                : !preview?.file_name
                ? 'Upload Workbook to Begin'
                : validRequests === 0
                ? 'Select a Request Set'
                : pendingRequests === 0
                ? 'All Requests Completed'
                : `Start Batch Processing (${pendingRequests} Pending)`}
            </Button>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onResetBatch}
                isLoading={isResetting}
                disabled={!preview?.file_name || isRunning}
                leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
                className="flex-1"
              >
                Reset Workbook
              </Button>

              {preview?.file_name ? (
                <a
                  href={api.getBatchExportUrl()}
                  download
                  className="flex-1"
                >
                  <Button
                    variant="secondary"
                    size="sm"
                    leftIcon={<Download className="w-3.5 h-3.5 text-cyan-400" />}
                    className="w-full"
                  >
                    Download Excel
                  </Button>
                </a>
              ) : (
                <Button
                  variant="secondary"
                  size="sm"
                  disabled
                  leftIcon={<Download className="w-3.5 h-3.5 text-slate-500" />}
                  className="flex-1 opacity-50"
                >
                  Download Excel
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Request Sets Found & Selection */}
      {preview?.file_name && candidateSheets.length > 1 && (
        <div className="p-4 rounded-xl bg-[#0B1020] border border-cyan-500/20 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-200 uppercase tracking-wide font-mono">
              Request Sets Found
            </span>
            <span className="text-[10px] font-mono text-cyan-400">
              {candidateSheets.length} Datasets Detected
            </span>
          </div>

          <div className="flex flex-wrap gap-2">
            {candidateSheets.map((s) => {
              const isCurrentActive = preview?.selected_sheets?.includes(s.sheet_name);
              return (
                <button
                  key={s.sheet_name}
                  type="button"
                  onClick={() => {
                    setSelectedSheet(s.sheet_name);
                    if (onSelectSheet && !isCurrentActive) {
                      onSelectSheet(s.sheet_name);
                    }
                  }}
                  className={`text-xs px-3 py-1.5 rounded-lg border font-mono transition-all flex items-center gap-2 ${
                    isCurrentActive
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50 font-bold shadow-sm shadow-cyan-500/20'
                      : 'bg-slate-900/60 text-slate-400 border-white/[0.08] hover:border-white/[0.2]'
                  }`}
                >
                  <span className="font-semibold">{s.sheet_name}</span>
                  <span>—</span>
                  <span>{s.valid_requests} requests</span>
                  {isCurrentActive && (
                    <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-500/30">
                      Active
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2 border-t border-white/[0.06]">
            <div className="flex-1 flex items-center gap-2">
              <label htmlFor="request-set-select" className="text-xs text-slate-400 shrink-0">
                Select Request Set:
              </label>
              <select
                id="request-set-select"
                value={selectedSheet}
                onChange={(e) => setSelectedSheet(e.target.value)}
                className="flex-1 bg-[#070A12] border border-white/[0.15] text-slate-200 text-xs rounded-lg px-3 py-2 focus:border-cyan-400 focus:outline-none cursor-pointer"
              >
                <option value="">-- Select a Request Set --</option>
                {candidateSheets.map((s) => (
                  <option key={s.sheet_name} value={s.sheet_name}>
                    {s.sheet_name} — {s.valid_requests} requests
                  </option>
                ))}
              </select>
            </div>

            <Button
              variant="primary"
              size="sm"
              disabled={!selectedSheet || isSelectingSheet || (preview?.selected_sheets?.length === 1 && preview?.selected_sheets[0] === selectedSheet)}
              onClick={() => selectedSheet && onSelectSheet?.(selectedSheet)}
              isLoading={isSelectingSheet}
            >
              Use Selected Request Set
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
};
