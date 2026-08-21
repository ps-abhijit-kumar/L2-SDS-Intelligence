import React, { useState } from 'react';
import { SearchForm } from '../components/search/SearchForm';
import { AgentProcessingTimeline } from '../components/search/AgentProcessingTimeline';
import { SearchResultCard } from '../components/search/SearchResultCard';
import { EvidenceSection } from '../components/search/EvidenceSection';
import { DocumentViewerModal } from '../components/search/DocumentViewerModal';
import { ExecutionTraceViewer } from '../components/trace/ExecutionTraceViewer';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { Card, CardHeader, CardTitle } from '../components/common/Card';
import { useSdsSearch } from '../hooks/useSdsSearch';
import { SDSSearchRequest, SDSSearchResponse, HistoryItem } from '../types/sds';
import { Search, Sparkles, Terminal } from 'lucide-react';

export const SearchPage: React.FC = () => {
  const { mutate: executeSearch, isPending, error, data: searchResult } = useSdsSearch();
  const [activePreviewUrl, setActivePreviewUrl] = useState<string | null>(null);
  const [isTraceOpen, setIsTraceOpen] = useState(false);
  const [lastQuery, setLastQuery] = useState<SDSSearchRequest | null>(null);

  const handleSearch = (payload: SDSSearchRequest) => {
    setLastQuery(payload);
    setIsTraceOpen(false);
    executeSearch(payload);
  };

  const handleRetry = () => {
    if (lastQuery) {
      executeSearch(lastQuery);
    }
  };

  const traceItem: HistoryItem | null = searchResult
    ? {
        id: searchResult.id,
        product_name: searchResult.product_name,
        company_name: searchResult.company_name,
        country: searchResult.country,
        language: searchResult.language,
        status: searchResult.status,
        confidence: searchResult.confidence,
        final_url: searchResult.final_url,
        detailed_reasoning: searchResult.detailed_reasoning,
        timestamp: searchResult.timestamp,
        messages: searchResult.trace,
      }
    : null;

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Search Input Command Console */}
      <Card variant="elevated" className="border-cyan-500/20 shadow-xl shadow-black/50">
        <CardHeader>
          <CardTitle>
            <Search className="w-4 h-4 text-cyan-400" />
            <span>SDS Verification Console</span>
          </CardTitle>
          <span className="text-[10px] font-mono text-slate-400 bg-[#070A12] px-2.5 py-1 rounded-lg border border-white/[0.08]">
            Find & Validate Safety Data Sheets
          </span>
        </CardHeader>
        <SearchForm onSearch={handleSearch} isLoading={isPending} />
      </Card>

      {/* Live Agent Execution Progress Timeline */}
      {isPending && <AgentProcessingTimeline />}

      {/* Error Alert */}
      {error && !isPending && (
        <ErrorMessage
          title="SDS Verification Failed"
          message={error.message || 'We could not complete the SDS verification. Please verify backend connection and API key in .env.'}
          onRetry={handleRetry}
        />
      )}

      {/* Verification Result Presentation */}
      {searchResult && !isPending && (
        <div className="space-y-6 animate-slide-up">
          <SearchResultCard
            result={searchResult}
            onViewDocument={(url) => setActivePreviewUrl(url)}
            onToggleTrace={() => setIsTraceOpen(!isTraceOpen)}
            isTraceOpen={isTraceOpen}
          />

          <EvidenceSection
            reasoning={searchResult.detailed_reasoning}
            productName={searchResult.product_name}
            companyName={searchResult.company_name}
            country={searchResult.country}
            language={searchResult.language}
          />

          {isTraceOpen && (
            <div className="animate-slide-up">
              <ExecutionTraceViewer traceItem={traceItem} />
            </div>
          )}
        </div>
      )}

      {/* Document Intelligence Preview Modal */}
      {activePreviewUrl && (
        <DocumentViewerModal
          url={activePreviewUrl}
          onClose={() => setActivePreviewUrl(null)}
        />
      )}
    </div>
  );
};
