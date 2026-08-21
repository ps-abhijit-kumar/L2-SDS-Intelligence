import React from 'react';
import { X, ExternalLink, ShieldCheck, Terminal, Cpu, Clock, Building2, Globe2 } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { ConfidenceGauge } from '../common/ConfidenceGauge';
import { Button } from '../common/Button';
import { HistoryItem } from '../../types/sds';
import { formatDate } from '../../utils/formatters';

interface HistoryDetailModalProps {
  item: HistoryItem | null;
  onClose: () => void;
}

export const HistoryDetailModal: React.FC<HistoryDetailModalProps> = ({ item, onClose }) => {
  if (!item) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-6 bg-slate-950/85 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-4xl max-h-[90vh] bg-[#0B1020] border border-white/[0.1] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-slide-up">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between bg-[#070A12] shrink-0">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h3 className="text-base font-bold text-slate-100">
                {item.product_name}
              </h3>
              <StatusBadge status={item.status} size="sm" />
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Audit ID: {item.id} • Processed: {formatDate(item.timestamp)}
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-white/[0.08] rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1 text-xs">
          {/* Top Attributes Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-[#070A12] p-4 rounded-xl border border-white/[0.06]">
            <div>
              <span className="text-slate-500 font-mono font-bold uppercase text-[10px]">Manufacturer</span>
              <p className="font-semibold text-slate-200 mt-0.5">{item.company_name || 'N/A'}</p>
            </div>
            <div>
              <span className="text-slate-500 font-mono font-bold uppercase text-[10px]">Jurisdiction</span>
              <p className="font-semibold text-slate-200 mt-0.5">{item.country || 'Global'}</p>
            </div>
            <div>
              <span className="text-slate-500 font-mono font-bold uppercase text-[10px]">Language</span>
              <p className="font-semibold text-slate-200 mt-0.5">{item.language || 'English'}</p>
            </div>
            <div>
              <span className="text-slate-500 font-mono font-bold uppercase text-[10px]">Confidence</span>
              <div className="mt-1">
                <ConfidenceGauge confidence={item.confidence} size="sm" />
              </div>
            </div>
          </div>

          {/* Confirmed Safety Data Sheet Document */}
          {item.final_url && (
            <div className="space-y-1.5">
              <span className="text-cyan-400 font-mono font-bold uppercase text-[10px] tracking-wider">
                Confirmed Safety Data Sheet URL
              </span>
              <div className="flex items-center justify-between gap-3 bg-[#070A12] p-3.5 rounded-xl border border-cyan-500/30 shadow-glow-cyan">
                <span className="font-mono text-slate-200 truncate select-all">
                  {item.final_url}
                </span>
                <a
                  href={item.final_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 inline-flex items-center gap-1.5 text-cyan-400 hover:text-cyan-300 font-semibold bg-cyan-950/80 px-3 py-1.5 rounded-lg border border-cyan-500/40"
                >
                  <span>Open SDS</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          )}

          {/* Compliance Reasoning */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-slate-200 font-semibold">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span>Compliance Rationale & Agent Validation</span>
            </div>
            <div className="p-4 rounded-xl bg-[#070A12] border border-white/[0.08] leading-relaxed text-slate-300 whitespace-pre-wrap font-sans">
              {item.detailed_reasoning || 'No additional rationale stored.'}
            </div>
          </div>

          {/* LangGraph Message Trace */}
          {item.messages && item.messages.length > 0 && (
            <div className="space-y-3 pt-3 border-t border-white/[0.06]">
              <div className="flex items-center gap-2 text-slate-200 font-semibold">
                <Terminal className="w-4 h-4 text-purple-400" />
                <span>LangGraph Execution Messages & Tool Calls ({item.messages.length} steps)</span>
              </div>
              <div className="space-y-2.5">
                {item.messages.map((m, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-[#070A12] border border-white/[0.06] font-mono text-[11px] space-y-2"
                  >
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="text-cyan-400 font-bold">[{m.type}]</span>
                      <span className="text-slate-600">Step #{idx + 1}</span>
                    </div>
                    {m.content && (
                      <p className="text-slate-300 whitespace-pre-wrap font-sans text-xs">{m.content}</p>
                    )}
                    {m.tool_calls && m.tool_calls.length > 0 && (
                      <div className="bg-[#0B1020] p-2.5 rounded-lg border border-white/[0.08] text-slate-300 space-y-1">
                        <span className="text-purple-400 text-[10px] uppercase font-bold flex items-center gap-1">
                          <Cpu className="w-3 h-3" /> Tool Call: {m.tool_calls[0].name}
                        </span>
                        <pre className="text-[10px] text-cyan-300 overflow-x-auto">
                          {JSON.stringify(m.tool_calls[0].args, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-white/[0.08] bg-[#070A12] flex justify-end shrink-0">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};
