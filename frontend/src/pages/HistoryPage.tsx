import React, { useState } from 'react';
import { HistoryFilterBar } from '../components/history/HistoryFilterBar';
import { HistoryTable } from '../components/history/HistoryTable';
import { HistoryDetailModal } from '../components/history/HistoryDetailModal';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { useHistory } from '../hooks/useHistory';
import { HistoryItem } from '../types/sds';
import { History, ShieldCheck } from 'lucide-react';

export const HistoryPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('ALL');
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);

  const { data, isLoading, error, refetch } = useHistory({
    query: query.trim() || undefined,
    status: status !== 'ALL' ? status : undefined,
    limit: 100,
  });

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="space-y-1">
          <h2 className="text-xl font-black text-slate-100 flex items-center gap-2.5">
            <History className="w-5 h-5 text-cyan-400" />
            <span>Verification Audit & Search History</span>
          </h2>
          <p className="text-xs text-slate-400 font-sans">
            Immutable audit logs loaded directly from <code className="text-cyan-300 font-mono">logs/agent_trace.jsonl</code>.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <HistoryFilterBar
        query={query}
        onQueryChange={setQuery}
        status={status}
        onStatusChange={setStatus}
        onRefresh={() => refetch()}
        isLoading={isLoading}
      />

      {/* Error Alert */}
      {error && (
        <ErrorMessage
          title="Could not load audit history"
          message={error.message || 'Failed to fetch history logs from the backend API.'}
          onRetry={() => refetch()}
        />
      )}

      {/* History Audit Table */}
      <HistoryTable
        items={data?.items || []}
        isLoading={isLoading}
        total={data?.total || 0}
        onSelectItem={(item) => setSelectedItem(item)}
      />

      {/* Detailed Trace Modal */}
      <HistoryDetailModal
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
      />
    </div>
  );
};
