import React, { useState } from 'react';
import {
  ExternalLink,
  Copy,
  Check,
  FileSearch,
  Eye,
  Calendar,
  Building2,
  Globe2,
  Languages,
  ShieldCheck,
  FileText,
  Sparkles,
} from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { ConfidenceGauge } from '../common/ConfidenceGauge';
import { Button } from '../common/Button';
import { SDSSearchResponse } from '../../types/sds';
import { formatDate, getDomainFromUrl } from '../../utils/formatters';

interface SearchResultCardProps {
  result: SDSSearchResponse;
  onViewDocument?: (url: string) => void;
  onToggleTrace?: () => void;
  isTraceOpen?: boolean;
}

export const SearchResultCard: React.FC<SearchResultCardProps> = ({
  result,
  onViewDocument,
  onToggleTrace,
  isTraceOpen,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopyUrl = () => {
    if (result.final_url) {
      navigator.clipboard.writeText(result.final_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const domain = result.final_url ? getDomainFromUrl(result.final_url) : null;

  return (
    <div className="bg-[#0B1020]/90 border border-white/[0.09] rounded-2xl p-6 md:p-8 shadow-xl shadow-black/50 space-y-6 relative overflow-hidden">
      {/* Background Subtle Accent Glow */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-radial from-cyan-500/10 via-transparent to-transparent pointer-events-none" />

      {/* Top Banner: Verdict & Confidence */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-white/[0.06] pb-6 relative z-10">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Autonomous Verification Verdict</span>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <h3 className="text-xl md:text-2xl font-black text-slate-100 tracking-tight">
              {result.product_name}
            </h3>
            <StatusBadge status={result.status} size="lg" />
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 font-sans">
            {result.company_name && (
              <span className="flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 text-slate-500" />
                {result.company_name}
              </span>
            )}
            {result.country && (
              <span className="flex items-center gap-1.5">
                <Globe2 className="w-3.5 h-3.5 text-slate-500" />
                {result.country}
              </span>
            )}
            {result.language && (
              <span className="flex items-center gap-1.5">
                <Languages className="w-3.5 h-3.5 text-slate-500" />
                {result.language}
              </span>
            )}
          </div>
        </div>

        <div className="md:w-64 shrink-0">
          <ConfidenceGauge confidence={result.confidence} size="md" />
        </div>
      </div>

      {/* Verified Document URL Banner */}
      {result.final_url ? (
        <div className="bg-[#070A12] border border-cyan-500/30 rounded-xl p-4 space-y-2.5 shadow-glow-cyan relative z-10">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              {result.url_type === 'landing_page' || (!result.final_url.toLowerCase().split('?')[0].endsWith('.pdf') && result.url_type !== 'pdf')
                ? 'SDS Landing / Download Page (Manual Download Available)'
                : 'Direct Verified SDS PDF Document'}
            </span>
            <div className="flex items-center gap-2">
              <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                result.url_type === 'landing_page' || (!result.final_url.toLowerCase().split('?')[0].endsWith('.pdf') && result.url_type !== 'pdf')
                  ? 'text-amber-300 bg-amber-950/80 border-amber-500/40'
                  : 'text-emerald-300 bg-emerald-950/80 border-emerald-500/40'
              }`}>
                {result.url_type === 'landing_page' || (!result.final_url.toLowerCase().split('?')[0].endsWith('.pdf') && result.url_type !== 'pdf')
                  ? 'LANDING PAGE'
                  : 'PDF DOCUMENT'}
              </span>
              {domain && (
                <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded-full border border-cyan-500/40">
                  {domain}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between gap-3 bg-[#0B1020] px-3.5 py-2.5 rounded-lg border border-white/[0.08]">
            <span className="font-mono text-xs text-slate-200 truncate select-all">
              {result.final_url}
            </span>
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                onClick={handleCopyUrl}
                title="Copy URL"
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-white/[0.06] rounded-lg transition-colors cursor-pointer"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
              <a
                href={result.final_url}
                target="_blank"
                rel="noopener noreferrer"
                title="Open SDS document"
                className="p-1.5 text-slate-400 hover:text-cyan-400 hover:bg-white/[0.06] rounded-lg transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-[#070A12] border border-white/[0.08] rounded-xl p-4 text-xs text-slate-400 flex items-center justify-between">
          <span>No direct SDS document URL was confirmed for this query.</span>
          <span className="font-mono text-amber-400">Status: {result.status}</span>
        </div>
      )}

      {/* Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2 relative z-10 border-t border-white/[0.04]">
        <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
          <Calendar className="w-3.5 h-3.5" />
          <span>Processed {formatDate(result.timestamp)}</span>
          <span className="text-slate-600">•</span>
          <span className="text-slate-500">ID: {result.id.slice(0, 8)}</span>
        </div>

        <div className="flex items-center gap-3">
          {result.final_url && onViewDocument && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onViewDocument(result.final_url)}
              leftIcon={<Eye className="w-3.5 h-3.5 text-cyan-400" />}
            >
              Document Intelligence Preview
            </Button>
          )}

          {onToggleTrace && (
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleTrace}
              leftIcon={<FileSearch className="w-3.5 h-3.5" />}
            >
              {isTraceOpen ? 'Hide Execution Trace' : 'Inspect Agent Trace'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
