/**
 * Human-in-the-Loop Review Queue Page
 * ===================================
 * Architecture Role:
 *   Provides compliance officers with a dedicated triage queue for items marked as 'NEEDS REVIEW'.
 *   Allows manual inspection of candidate evidence, discrepancy diagnostics, and status sign-off.
 *
 * Integrated Components:
 *   - ReviewQueueTable: Tabular view of flagged items with sorting and filtering.
 *   - ReviewInspectionDrawer: Slide-out drawer displaying comprehensive grounding traces.
 */

import React, { useState } from 'react';
import { ShieldAlert, AlertCircle, Sparkles } from 'lucide-react';
import { ReviewQueueTable } from '../components/review/ReviewQueueTable';
import { ReviewInspectionDrawer } from '../components/review/ReviewInspectionDrawer';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { useReviewQueue } from '../hooks/useHistory';
import { HistoryItem } from '../types/sds';

export const ReviewPage: React.FC = () => {
  const { data, isLoading, error, refetch } = useReviewQueue();
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);

  const totalFlagged = data?.total || 0;

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Review Queue Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-[#0B1020]/90 border border-amber-500/30 shadow-lg shadow-black/40">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <h2 className="text-lg font-bold text-slate-100">
              Human-in-the-Loop Review Queue
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
              {totalFlagged} Pending Review
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            AI identified results requiring additional verification. Requests with uncertain supplier matches or moderate utility scores are routed here for compliance review.
          </p>
        </div>
      </div>

      {error && (
        <ErrorMessage
          title="Could not load review queue"
          message={error.message || 'Failed to fetch flagged items from the backend API.'}
          onRetry={() => refetch()}
        />
      )}

      {/* Review Table */}
      <ReviewQueueTable
        items={data?.items || []}
        isLoading={isLoading}
        onSelectItem={(item) => setSelectedItem(item)}
      />

      {/* Inspection Drawer */}
      <ReviewInspectionDrawer
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
      />
    </div>
  );
};
