import React from 'react';
import { Loader2, CheckCircle2, AlertTriangle, Cpu, Download } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../common/Card';
import { Button } from '../common/Button';
import { BatchStatusResponse } from '../../types/sds';
import { api } from '../../services/api';

interface BatchProgressMonitorProps {
  status?: BatchStatusResponse;
}

export const BatchProgressMonitor: React.FC<BatchProgressMonitorProps> = ({ status }) => {
  if (!status || status.status === 'idle') {
    return null;
  }

  const isRunning = status.status === 'running';
  const isCompleted = status.status === 'completed';
  const isError = status.status === 'error';

  const total = status.total_requests || 1;
  const completed = status.completed_requests || 0;
  const percent = Math.min(100, Math.round((completed / total) * 100));

  return (
    <Card
      variant="elevated"
      className={`border-cyan-500/40 shadow-xl transition-all duration-300 ${
        isRunning ? 'shadow-glow-cyan' : isCompleted ? 'border-emerald-500/40 shadow-glow-emerald' : 'border-rose-500/40'
      }`}
    >
      <CardHeader>
        <CardTitle>
          {isRunning ? (
            <div className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500" />
            </div>
          ) : isCompleted ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          )}

          <span>
            {isRunning
              ? 'Sequential SDS Batch In Progress'
              : isCompleted
              ? 'Batch Processing Complete'
              : 'Batch Processing Halted'}
          </span>
        </CardTitle>

        <div className="flex items-center gap-3">
          <span className="text-xs font-mono font-bold text-slate-300">
            {completed} / {total} Requests ({percent}%)
          </span>
          {isRunning && <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400" />}
        </div>
      </CardHeader>

      <div className="space-y-4">
        {/* Luminous Progress Bar */}
        <div className="w-full h-2.5 bg-[#070A12] border border-white/[0.08] rounded-full overflow-hidden p-0.5">
          <div
            className={`h-full transition-all duration-500 rounded-full ${
              isRunning
                ? 'bg-gradient-to-r from-cyan-500 to-blue-500 shadow-glow-cyan'
                : isCompleted
                ? 'bg-gradient-to-r from-emerald-500 to-teal-400 shadow-glow-emerald'
                : 'bg-rose-500'
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>

        {/* Current Active Request Status */}
        {isRunning && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3.5 rounded-xl bg-[#070A12] border border-white/[0.06] text-xs">
            <div className="space-y-0.5">
              <span className="text-[10px] font-mono uppercase text-slate-500 font-bold">
                Currently Processing Target
              </span>
              <p className="font-bold text-cyan-300 truncate">
                {status.current_product || 'Evaluating chemical...'}
                {status.current_company && (
                  <span className="text-slate-400 font-normal font-sans ml-1.5">
                    ({status.current_company})
                  </span>
                )}
              </p>
            </div>

            <div className="space-y-0.5">
              <span className="text-[10px] font-mono uppercase text-slate-500 font-bold">
                Agent Lifecycle Stage
              </span>
              <p className="text-slate-300 font-mono text-[11px] truncate flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <span>{status.current_stage}</span>
              </p>
            </div>
          </div>
        )}

        {/* Completed Batch Summary Banner */}
        {isCompleted && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div className="space-y-0.5">
                <h4 className="font-bold text-emerald-300">
                  All {total} SDS Chemical Requests Evaluated & Saved
                </h4>
                <p className="text-emerald-200/80 text-[11px]">
                  Workbook updated in-place with confirmed URLs, status verdicts, and reasoning.
                </p>
              </div>
            </div>

            <a href={api.getBatchExportUrl()} download className="shrink-0">
              <Button
                variant="primary"
                size="sm"
                leftIcon={<Download className="w-3.5 h-3.5" />}
                className="shadow-glow-emerald"
              >
                Download Updated Excel
              </Button>
            </a>
          </div>
        )}

        {/* Error Alert */}
        {isError && (
          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
            <strong>Batch Stopped:</strong> {status.error || 'An unexpected error occurred during execution.'}
          </div>
        )}
      </div>
    </Card>
  );
};
