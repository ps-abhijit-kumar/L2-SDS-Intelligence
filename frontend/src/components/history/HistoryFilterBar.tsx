import React from 'react';
import { Search, Filter, RefreshCw } from 'lucide-react';
import { Button } from '../common/Button';

interface HistoryFilterBarProps {
  query: string;
  onQueryChange: (query: string) => void;
  status: string;
  onStatusChange: (status: string) => void;
  onRefresh: () => void;
  isLoading?: boolean;
}

const STATUS_OPTIONS = [
  { label: 'All Verdicts', value: 'ALL' },
  { label: 'Exact Matches Only', value: 'EXACT MATCH' },
  { label: 'Best Available Only', value: 'BEST AVAILABLE' },
  { label: 'Needs Human Review', value: 'NEEDS REVIEW' },
  { label: 'Errors / Unresolved', value: 'ERROR' },
];

export const HistoryFilterBar: React.FC<HistoryFilterBarProps> = ({
  query,
  onQueryChange,
  status,
  onStatusChange,
  onRefresh,
  isLoading,
}) => {
  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-[#0B1020]/90 p-3.5 rounded-2xl border border-white/[0.08] shadow-md">
      <div className="flex flex-1 flex-col sm:flex-row items-center gap-3">
        {/* Search input */}
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="Search by product, company, or request ID..."
            className="w-full bg-[#070A12] border border-white/[0.08] text-slate-100 placeholder:text-slate-500 rounded-xl text-xs pl-10 pr-3.5 py-2.5 focus:outline-none focus:border-cyan-400 focus:shadow-glow-cyan transition-all"
          />
        </div>

        {/* Status Dropdown Filter */}
        <div className="relative w-full sm:w-56">
          <Filter className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
          <select
            value={status}
            onChange={(e) => onStatusChange(e.target.value)}
            className="w-full bg-[#070A12] border border-white/[0.08] text-slate-200 rounded-xl text-xs pl-9 pr-8 py-2.5 focus:outline-none focus:border-cyan-400 appearance-none cursor-pointer"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-[#070A12] text-slate-200">
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          isLoading={isLoading}
          leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
        >
          Refresh Logs
        </Button>
      </div>
    </div>
  );
};
