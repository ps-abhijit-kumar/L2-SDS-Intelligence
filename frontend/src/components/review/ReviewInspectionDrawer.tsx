import React from 'react';
import { X, ExternalLink, ShieldAlert, FileText, Info } from 'lucide-react';
import { ConfidenceGauge } from '../common/ConfidenceGauge';
import { Button } from '../common/Button';
import { HistoryItem } from '../../types/sds';
import { formatDate } from '../../utils/formatters';

interface ReviewInspectionDrawerProps {
  item: HistoryItem | null;
  onClose: () => void;
}

export const ReviewInspectionDrawer: React.FC<ReviewInspectionDrawerProps> = ({
  item,
  onClose,
}) => {
  if (!item) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-6 bg-slate-950/85 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-3xl max-h-[90vh] bg-[#0B1020] border border-amber-500/30 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-slide-up">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/[0.08] bg-[#070A12] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-100">
                  {item.product_name}
                </h3>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Needs Human Review
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Logged: {formatDate(item.timestamp)} • Request ID: {item.id}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-white/[0.08] rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1 text-xs">
          {/* Review Banner */}
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200 space-y-1.5">
            <div className="flex items-center gap-2 font-semibold text-amber-300">
              <ShieldAlert className="w-4 h-4" />
              <span>Compliance Uncertainty Flagged</span>
            </div>
            <p className="text-xs leading-relaxed text-amber-200/90 font-sans">
              The autonomous retrieval agent did not achieve the required threshold for a 100% verified EXACT MATCH. A human compliance officer should manually inspect the candidate document and confirm chemical specification.
            </p>
          </div>

          {/* Target Attributes Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-[#070A12] p-4 rounded-xl border border-white/[0.06]">
            <div>
              <span className="text-slate-500 font-mono font-bold uppercase text-[10px]">Product</span>
              <p className="font-semibold text-slate-200 mt-0.5 font-sans">{item.product_name}</p>
            </div>
            <div>
              <span className="text-slate-500 font-mono font-bold uppercase text-[10px]">Target Supplier</span>
              <p className="font-semibold text-slate-200 mt-0.5 font-sans">{item.company_name || 'Unspecified'}</p>
            </div>
            <div>
              <span className="text-slate-500 font-mono font-bold uppercase text-[10px]">Country</span>
              <p className="font-semibold text-slate-200 mt-0.5 font-sans">{item.country || 'Global'}</p>
            </div>
            <div>
              <span className="text-slate-500 font-mono font-bold uppercase text-[10px]">Confidence</span>
              <div className="mt-1">
                <ConfidenceGauge confidence={item.confidence} size="sm" />
              </div>
            </div>
          </div>

          {/* Candidate Document */}
          {item.final_url ? (
            <div className="space-y-2">
              <span className="text-slate-200 font-semibold flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-cyan-400" />
                Candidate SDS Document for Review
              </span>
              <div className="flex items-center justify-between gap-3 bg-[#070A12] p-3.5 rounded-xl border border-white/[0.08]">
                <span className="font-mono text-slate-200 truncate select-all">
                  {item.final_url}
                </span>
                <a
                  href={item.final_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-semibold bg-cyan-950/80 px-3 py-1.5 rounded-lg border border-cyan-500/40"
                >
                  <span>Open SDS</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          ) : (
            <div className="p-3.5 bg-[#070A12] rounded-xl border border-white/[0.06] text-slate-400">
              No candidate document URL could be confirmed by the agent during the automated cycle.
            </div>
          )}

          {/* Reasoning */}
          <div className="space-y-2">
            <span className="text-slate-200 font-semibold flex items-center gap-1.5">
              <Info className="w-4 h-4 text-slate-400" />
              Agent Rationale & Evidence Notes
            </span>
            <div className="p-4 rounded-xl bg-[#070A12] border border-white/[0.08] leading-relaxed text-slate-300 font-sans whitespace-pre-wrap">
              {item.detailed_reasoning || 'No additional rationale provided.'}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-white/[0.08] bg-[#070A12] flex justify-end shrink-0">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close Inspection
          </Button>
        </div>
      </div>
    </div>
  );
};
