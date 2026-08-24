import React, { useState } from 'react';
import { ExternalLink, ArrowUpRight, FileText, Search, Layers } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { ConfidenceGauge } from '../common/ConfidenceGauge';
import { EmptyState } from '../common/EmptyState';
import { TableSkeleton } from '../common/LoadingSkeleton';
import { BatchRow } from '../../types/sds';

interface BatchRequestTableProps {
  rows: BatchRow[];
  isLoading?: boolean;
  onSelectRow: (row: BatchRow) => void;
}

export const BatchRequestTable: React.FC<BatchRequestTableProps> = ({
  rows,
  isLoading,
  onSelectRow,
}) => {
  const [filterQuery, setFilterQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [sheetFilter, setSheetFilter] = useState('ALL');

  if (isLoading) {
    return <TableSkeleton rows={8} />;
  }

  // Extract unique sheet names
  const uniqueSheets = Array.from(
    new Set(rows.map((r) => r._sheet_name).filter(Boolean))
  ) as string[];

  const filteredRows = rows.filter((r) => {
    const matchesQuery =
      !filterQuery.trim() ||
      (r.Product && r.Product.toLowerCase().includes(filterQuery.toLowerCase())) ||
      (r['Product Name'] && r['Product Name'].toLowerCase().includes(filterQuery.toLowerCase())) ||
      (r['Product Company Name'] && r['Product Company Name'].toLowerCase().includes(filterQuery.toLowerCase())) ||
      (r['Part Number'] && r['Part Number'].toLowerCase().includes(filterQuery.toLowerCase()));

    const matchesStatus =
      statusFilter === 'ALL' ||
      (r.Status && r.Status.toUpperCase() === statusFilter.toUpperCase());

    const matchesSheet =
      sheetFilter === 'ALL' ||
      r._sheet_name === sheetFilter;

    return matchesQuery && matchesStatus && matchesSheet;
  });

  return (
    <div className="bg-[#0B1020]/90 border border-white/[0.08] rounded-2xl overflow-hidden shadow-lg shadow-black/40 space-y-3">
      {/* Table Filter Controls */}
      <div className="p-4 border-b border-white/[0.06] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-[#070A12]/80">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <FileText className="w-3.5 h-3.5" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wide font-mono">
              SDS Requests ({rows.length} Total Records)
            </h3>
            <span className="text-[10px] text-slate-400">
              Active chemical requests extracted from uploaded workbook
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Text filter */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              placeholder="Filter product/company..."
              className="bg-[#070A12] border border-white/[0.08] text-slate-200 placeholder:text-slate-500 rounded-lg text-xs pl-8 pr-3 py-1.5 focus:outline-none focus:border-cyan-400"
            />
          </div>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#070A12] border border-white/[0.08] text-slate-200 rounded-lg text-xs px-2.5 py-1.5 focus:outline-none focus:border-cyan-400 cursor-pointer"
          >
            <option value="ALL">All Statuses</option>
            <option value="EXACT MATCH">Exact Match</option>
            <option value="BEST AVAILABLE">Best Available</option>
            <option value="NEEDS REVIEW">Needs Review</option>
            <option value="PENDING">Pending</option>
            <option value="ERROR">Error</option>
          </select>
        </div>
      </div>

      {/* Table Body */}
      {filteredRows.length === 0 ? (
        <div className="p-8">
          <EmptyState
            icon="inbox"
            title={rows.length === 0 ? "No Active Workbook Loaded" : "No Matching Request Rows"}
            description={rows.length === 0 ? "Upload an Excel (.xlsx) workbook above to extract and inspect SDS requests." : "No Excel rows match the current search or status filter."}
          />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-[#070A12] border-b border-white/[0.06] text-slate-400 uppercase font-mono font-semibold text-[10px] tracking-wider">
                <th className="py-2.5 px-3.5 w-10 text-center">#</th>
                <th className="py-2.5 px-3.5">Product Name</th>
                <th className="py-2.5 px-3.5">Manufacturer</th>
                <th className="py-2.5 px-3.5">Language</th>
                <th className="py-2.5 px-3.5">Jurisdiction</th>
                <th className="py-2.5 px-3.5">Status</th>
                <th className="py-2.5 px-3.5">Confidence</th>
                <th className="py-2.5 px-3.5">SDS Document URL</th>
                <th className="py-2.5 px-3.5 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filteredRows.map((r) => {
                const isResolved = r.Status && r.Status !== 'PENDING';
                const isPdf = r['Found URL']?.toLowerCase().split('?')[0].endsWith('.pdf');
                return (
                  <tr
                    key={`${r._sheet_name || 'sheet'}_${r._row_index}`}
                    onClick={() => onSelectRow(r)}
                    className="hover:bg-white/[0.03] transition-colors cursor-pointer group"
                  >
                    <td className="py-3 px-3.5 font-mono text-slate-400 text-center font-bold text-[11px]">
                      {r['S.No.']}
                    </td>

                    <td className="py-3 px-3.5 font-bold text-slate-100 max-w-[180px] truncate">
                      <div>
                        <span className="block truncate">{r.Product || r['Product Name']}</span>
                        {r['Part Number'] && (
                          <span className="text-[10px] text-slate-500 font-mono font-normal block truncate">
                            ID: {r['Part Number']}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-3 px-3.5 text-slate-300 max-w-[150px] truncate font-sans">
                      {r['Product Company Name'] || '—'}
                    </td>

                    <td className="py-3 px-3.5 text-slate-400 font-mono text-[11px]">
                      {r.Language || 'English'}
                    </td>

                    <td className="py-3 px-3.5 text-slate-400 font-mono text-[11px]">
                      {r.Country || 'Global'}
                    </td>

                    <td className="py-3 px-3.5">
                      <StatusBadge status={r.Status || 'PENDING'} size="sm" />
                    </td>

                    <td className="py-3 px-3.5">
                      {isResolved ? (
                        <ConfidenceGauge confidence={r.Confidence || 0} size="sm" />
                      ) : (
                        <span className="text-slate-600 font-mono text-[11px]">—</span>
                      )}
                    </td>

                    <td className="py-3 px-3.5">
                      {r['Found URL'] ? (
                        <div className="flex items-center gap-1.5 max-w-[200px]">
                          <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border shrink-0 ${
                            isPdf
                              ? 'text-emerald-300 bg-emerald-950/80 border-emerald-500/40'
                              : 'text-amber-300 bg-amber-950/80 border-amber-500/40'
                          }`}>
                            {isPdf ? 'PDF' : 'PAGE'}
                          </span>
                          <a
                            href={r['Found URL']}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 hover:underline truncate font-mono text-[11px]"
                          >
                            <ExternalLink className="w-3 h-3 shrink-0" />
                            <span className="truncate">{r['Found URL']}</span>
                          </a>
                        </div>
                      ) : (
                        <span className="text-slate-600 italic text-[11px]">
                          {r.Status === 'PENDING' ? 'Pending run' : 'No URL found'}
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-3.5 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectRow(r);
                        }}
                        className="inline-flex items-center gap-1 text-cyan-400 group-hover:text-cyan-300 font-mono text-[11px] font-semibold hover:underline cursor-pointer"
                      >
                        <span>Details</span>
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
