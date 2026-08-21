import React from 'react';
import { AlertTriangle, ExternalLink, ShieldAlert, ArrowUpRight, FileText } from 'lucide-react';
import { ConfidenceGauge } from '../common/ConfidenceGauge';
import { EmptyState } from '../common/EmptyState';
import { TableSkeleton } from '../common/LoadingSkeleton';
import { HistoryItem } from '../../types/sds';
import { formatDate } from '../../utils/formatters';

interface ReviewQueueTableProps {
  items: HistoryItem[];
  isLoading?: boolean;
  onSelectItem: (item: HistoryItem) => void;
}

export const ReviewQueueTable: React.FC<ReviewQueueTableProps> = ({
  items,
  isLoading,
  onSelectItem,
}) => {
  if (isLoading) {
    return <TableSkeleton rows={5} />;
  }

  if (items.length === 0) {
    return (
      <EmptyState
        icon="inbox"
        title="Human Review Queue is Clear"
        description="All evaluated chemical searches have achieved high confidence or definitive verdicts. Any searches flagged as 'NEEDS REVIEW' will appear here for compliance review."
      />
    );
  }

  return (
    <div className="bg-[#0B1020]/90 border border-amber-500/20 rounded-2xl overflow-hidden shadow-lg shadow-black/40">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="bg-[#070A12] border-b border-white/[0.06] text-amber-300 uppercase font-mono font-semibold text-[10px] tracking-wider">
              <th className="py-3 px-4">Flagged Chemical Product</th>
              <th className="py-3 px-4">Manufacturer</th>
              <th className="py-3 px-4">Confidence</th>
              <th className="py-3 px-4">Review Rationale / Flag</th>
              <th className="py-3 px-4">Candidate Document</th>
              <th className="py-3 px-4">Logged At</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {items.map((item) => (
              <tr
                key={item.id}
                onClick={() => onSelectItem(item)}
                className="hover:bg-amber-500/[0.03] transition-colors cursor-pointer group"
              >
                <td className="py-3.5 px-4 font-semibold text-slate-100 max-w-[200px]">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
                    <span className="truncate">{item.product_name}</span>
                  </div>
                </td>

                <td className="py-3.5 px-4 text-slate-300 font-sans">
                  {item.company_name || '—'}
                </td>

                <td className="py-3.5 px-4">
                  <ConfidenceGauge confidence={item.confidence} size="sm" />
                </td>

                <td className="py-3.5 px-4 text-slate-300 max-w-xs truncate font-sans">
                  {item.detailed_reasoning || 'Flagged for low confidence or ambiguous manufacturer match.'}
                </td>

                <td className="py-3.5 px-4">
                  {item.final_url ? (
                    <a
                      href={item.final_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 hover:underline max-w-[130px] truncate font-mono text-[11px]"
                    >
                      <ExternalLink className="w-3 h-3 shrink-0" />
                      <span className="truncate">{item.final_url}</span>
                    </a>
                  ) : (
                    <span className="text-slate-600 italic">No Candidate URL</span>
                  )}
                </td>

                <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                  {formatDate(item.timestamp)}
                </td>

                <td className="py-3.5 px-4 text-right">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectItem(item);
                    }}
                    className="inline-flex items-center gap-1 text-amber-400 hover:text-amber-300 font-mono text-[11px] font-semibold group-hover:underline cursor-pointer"
                  >
                    <span>Inspect</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
