import React from 'react';
import { ExternalLink, ArrowUpRight, FileText, Calendar, Building2, Globe2 } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { ConfidenceGauge } from '../common/ConfidenceGauge';
import { EmptyState } from '../common/EmptyState';
import { TableSkeleton } from '../common/LoadingSkeleton';
import { HistoryItem } from '../../types/sds';
import { formatDate } from '../../utils/formatters';

interface HistoryTableProps {
  items: HistoryItem[];
  isLoading?: boolean;
  total: number;
  onSelectItem: (item: HistoryItem) => void;
}

export const HistoryTable: React.FC<HistoryTableProps> = ({
  items,
  isLoading,
  total,
  onSelectItem,
}) => {
  if (isLoading) {
    return <TableSkeleton rows={8} />;
  }

  if (items.length === 0) {
    return (
      <EmptyState
        icon="inbox"
        title="No Verification Records Found"
        description="No SDS search requests match the selected search query or status filter."
      />
    );
  }

  return (
    <div className="bg-[#0B1020]/90 border border-white/[0.08] rounded-2xl overflow-hidden shadow-lg shadow-black/40">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="bg-[#070A12] border-b border-white/[0.06] text-slate-400 uppercase font-mono font-semibold text-[10px] tracking-wider">
              <th className="py-3 px-4">Chemical Product</th>
              <th className="py-3 px-4">Manufacturer</th>
              <th className="py-3 px-4">Region</th>
              <th className="py-3 px-4">Verdict</th>
              <th className="py-3 px-4">Confidence</th>
              <th className="py-3 px-4">SDS Document</th>
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4 text-right">Inspect</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {items.map((item) => (
              <tr
                key={item.id}
                onClick={() => onSelectItem(item)}
                className="hover:bg-white/[0.03] transition-colors cursor-pointer group"
              >
                <td className="py-3.5 px-4 font-semibold text-slate-100 max-w-[220px]">
                  <div className="flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span className="truncate">{item.product_name}</span>
                  </div>
                </td>

                <td className="py-3.5 px-4 text-slate-400 max-w-[150px] truncate font-sans">
                  {item.company_name || '—'}
                </td>

                <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                  {item.country || 'Global'}
                </td>

                <td className="py-3.5 px-4">
                  <StatusBadge status={item.status} size="sm" />
                </td>

                <td className="py-3.5 px-4">
                  <ConfidenceGauge confidence={item.confidence} size="sm" />
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
                    <span className="text-slate-600 italic">No Document</span>
                  )}
                </td>

                <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px] whitespace-nowrap">
                  {formatDate(item.timestamp)}
                </td>

                <td className="py-3.5 px-4 text-right">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectItem(item);
                    }}
                    className="inline-flex items-center gap-1 text-cyan-400 group-hover:text-cyan-300 font-mono text-[11px] font-semibold hover:underline cursor-pointer"
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

      <div className="px-5 py-3 border-t border-white/[0.06] bg-[#070A12] flex items-center justify-between text-xs text-slate-500 font-mono">
        <span>Showing {items.length} of {total} records</span>
        <span>logs/agent_trace.jsonl</span>
      </div>
    </div>
  );
};
