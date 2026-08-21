import React from 'react';
import { ArchitectureDiagram } from '../components/trace/ArchitectureDiagram';
import { ExecutionTraceViewer } from '../components/trace/ExecutionTraceViewer';
import { useLatestTrace } from '../hooks/useHistory';
import { GitBranch, Sparkles } from 'lucide-react';

export const AgentTracePage: React.FC = () => {
  const { data } = useLatestTrace();

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      <div className="space-y-1.5">
        <div className="flex items-center gap-2.5">
          <GitBranch className="w-5 h-5 text-cyan-400" />
          <h2 className="text-xl font-black text-slate-100">
            L2 Agent Intelligence Architecture
          </h2>
        </div>
        <p className="text-xs text-slate-400 max-w-3xl leading-relaxed font-sans">
          Understand how the SDS agent discovers, ranks, retrieves, and validates documents using LangGraph state graphs, deterministic candidate ranking algorithms, PyMuPDF extraction, and Groq LLM function calling.
        </p>
      </div>

      {/* Interactive Architecture Workflow */}
      <ArchitectureDiagram />

      {/* Latest Live Execution Trace */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          <span>Latest Agent Execution Trace</span>
        </div>
        <ExecutionTraceViewer traceItem={data?.trace || null} />
      </div>
    </div>
  );
};
