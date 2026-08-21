import React from 'react';
import { ExternalLink, ShieldCheck, ArrowUpRight, History, FileText } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';
import { ConfidenceGauge } from '../common/ConfidenceGauge';
import { EmptyState } from '../common/EmptyState';
import { HistoryItem } from '../../types/sds';
import { formatRelativeTime } from '../../utils/formatters';

interface RecentActivityTableProps {
  items: HistoryItem[];
  onSelectItem: (item: HistoryItem) => void;
}

export const RecentActivityTable: React.FC<RecentActivityTableProps> = ({
  items,
  onSelectItem,
}) => {
  return (
    <Card className="space-y-4">
      <CardHeader>
        <CardTitle>
          <History className="w-4 h-4 text-cyan-400" />
          <span>Recent Verification Activity</span>
        </CardTitle>
        <span className="text-[10px] font-mono text-slate-400">
          Real-time Audit Logs
        </span>
      </CardHeader>

      {items.length === 0 ? (
        <EmptyState
          icon="inbox"
          title="No Recent Verifications"
          description="Autonomous SDS agent search operations will appear here as safety requests are evaluated."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.06] text-slate-400 uppercase font-mono font-semibold text-[10px] tracking-wider">
                <th className="py-2.5 px-3">Chemical Product</th>
                <th className="py-2.5 px-3">Manufacturer</th>
                <th className="py-2.5 px-3">Verdict</th>
                <th className="py-2.5 px-3">Confidence</th>
                <th className="py-2.5 px-3">SDS Source</th>
                <th className="py-2.5 px-3">Activity</th>
                <th className="py-2.5 px-3 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => onSelectItem(item)}
                  className="hover:bg-white/[0.03] transition-colors cursor-pointer group"
                >
                  <td className="py-3 px-3 font-semibold text-slate-100 max-w-[200px] truncate">
                    <div className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      <span className="truncate">{item.product_name}</span>
                    </div>
                  </td>

                  <td className="py-3 px-3 text-slate-400 max-w-[140px] truncate font-sans">
                    {item.company_name || '—'}
                  </td>

                  <td className="py-3 px-3">
                    <StatusBadge status={item.status} size="sm" />
                  </td>

                  <td className="py-3 px-3">
                    <ConfidenceGauge confidence={item.confidence} size="sm" />
                  </td>

                  <td className="py-3 px-3">
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

                  <td className="py-3 px-3 text-slate-400 font-mono text-[11px] whitespace-nowrap">
                    {formatRelativeTime(item.timestamp)}
                  </td>

                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectItem(item);
                      }}
                      className="inline-flex items-center gap-1 text-cyan-400 group-hover:text-cyan-300 font-mono text-[11px] font-semibold hover:underline"
                    >
                      <span>Trace</span>
                      <ArrowUpRight className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};
