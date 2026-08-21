import React from 'react';
import { Terminal, Cpu, MessageSquare, Wrench, CheckCircle2, ChevronRight } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { HistoryItem } from '../../types/sds';
import { formatDate } from '../../utils/formatters';

interface ExecutionTraceViewerProps {
  traceItem: HistoryItem | null;
}

export const ExecutionTraceViewer: React.FC<ExecutionTraceViewerProps> = ({ traceItem }) => {
  if (!traceItem) {
    return (
      <EmptyState
        icon="search"
        title="No Live Agent Trace Available"
        description="Execute an SDS search from the search console to generate and inspect live tool calls, PDF text extracts, and LLM reasoning steps."
      />
    );
  }

  const messages = traceItem.messages || [];

  return (
    <Card className="space-y-5">
      <CardHeader>
        <CardTitle>
          <Terminal className="w-4 h-4 text-purple-400" />
          <span>Execution Message Log: {traceItem.product_name}</span>
        </CardTitle>
        <span className="text-[10px] font-mono text-slate-400">
          {messages.length} Steps • {formatDate(traceItem.timestamp)}
        </span>
      </CardHeader>

      {messages.length === 0 ? (
        <div className="p-4 bg-[#070A12] rounded-xl border border-white/[0.06] text-xs text-slate-400">
          This record was populated from the Excel evaluation benchmark without step-by-step raw message traces. Run a live search to view raw tool calls.
        </div>
      ) : (
        <div className="space-y-3 font-mono text-xs">
          {messages.map((msg, idx) => {
            const isSystem = msg.type === 'SystemMessage';
            const isHuman = msg.type === 'HumanMessage';
            const isAI = msg.type === 'AIMessage';
            const isTool = msg.type === 'ToolMessage';

            let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700';
            let icon = MessageSquare;

            if (isSystem) {
              badgeColor = 'bg-slate-800 text-slate-400 border-slate-700';
            } else if (isHuman) {
              badgeColor = 'bg-blue-950 text-blue-400 border-blue-800';
            } else if (isAI) {
              badgeColor = 'bg-purple-950 text-purple-400 border-purple-800';
              icon = Cpu;
            } else if (isTool) {
              badgeColor = 'bg-emerald-950 text-emerald-400 border-emerald-800';
              icon = Wrench;
            }

            const Icon = icon;

            return (
              <div
                key={idx}
                className="p-4 rounded-xl bg-[#070A12] border border-white/[0.06] space-y-2 hover:border-cyan-500/30 transition-colors"
              >
                <div className="flex items-center justify-between border-b border-white/[0.04] pb-2">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold border ${badgeColor}`}>
                      <Icon className="w-3 h-3" />
                      {msg.type}
                    </span>
                    <span className="text-[10px] text-slate-500 font-sans">
                      Step #{idx + 1}
                    </span>
                  </div>
                  {msg.tool_calls && msg.tool_calls.length > 0 && (
                    <span className="text-[10px] text-purple-400 bg-purple-950 px-2 py-0.5 rounded border border-purple-800/60 font-semibold">
                      Tool Call: {msg.tool_calls[0].name}
                    </span>
                  )}
                </div>

                {/* Content */}
                {msg.content && (
                  <p className="text-slate-300 whitespace-pre-wrap leading-relaxed text-[11px] font-sans">
                    {msg.content}
                  </p>
                )}

                {/* Tool Call Payload */}
                {msg.tool_calls && msg.tool_calls.length > 0 && (
                  <div className="mt-2 p-2.5 rounded-lg bg-[#0B1020] border border-white/[0.08] space-y-1">
                    <div className="flex items-center gap-1 text-[10px] text-slate-400 font-semibold uppercase">
                      <ChevronRight className="w-3 h-3 text-purple-400" />
                      Tool Arguments:
                    </div>
                    <pre className="text-[10px] text-cyan-300 overflow-x-auto p-1.5 bg-[#070A12] rounded">
                      {JSON.stringify(msg.tool_calls[0].args, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};
