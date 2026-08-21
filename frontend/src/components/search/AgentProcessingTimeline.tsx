import React from 'react';
import { Search, ListOrdered, FileDown, FileText, BrainCircuit, CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../common/Card';

export const AgentProcessingTimeline: React.FC = () => {
  const stages = [
    {
      title: 'Formulating Autonomous Query',
      desc: 'Injecting manufacturer & jurisdiction keywords into structured DuckDuckGo search queries.',
      icon: Search,
    },
    {
      title: 'Utility Scoring & Candidate Ranking',
      desc: 'Filtering and scoring candidate URLs using deterministic domain and PDF heuristics (0-100).',
      icon: ListOrdered,
    },
    {
      title: 'PyMuPDF Binary Fetching',
      desc: 'Downloading first-page binary PDF stream and extracting safety text snippets.',
      icon: FileDown,
    },
    {
      title: 'Groq LLM Semantic Validation',
      desc: 'Cross-verifying supplier, product name, and GHS elements via Groq inference.',
      icon: BrainCircuit,
    },
    {
      title: 'Final Decision & Schema Extraction',
      desc: 'Extracting SDSValidationResult structured output with full JSON reasoning.',
      icon: CheckCircle2,
    },
  ];

  return (
    <Card variant="elevated" className="border-cyan-500/30 shadow-glow-cyan space-y-6">
      <CardHeader>
        <CardTitle>
          <div className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500" />
          </div>
          <span>Autonomous LangGraph Agent In Progress</span>
        </CardTitle>
        <div className="flex items-center gap-2 text-xs font-mono text-cyan-300">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Executing ReAct Cycles</span>
        </div>
      </CardHeader>

      <div className="space-y-4">
        {stages.map((stage, idx) => {
          const Icon = stage.icon;
          return (
            <div key={idx} className="flex items-start gap-3.5 relative group">
              {/* Connector line between steps */}
              {idx < stages.length - 1 && (
                <div className="absolute left-[17px] top-[34px] bottom-[-14px] w-[2px] bg-gradient-to-b from-cyan-500/40 to-transparent" />
              )}

              <div className="w-9 h-9 rounded-xl bg-[#070A12] border border-cyan-500/40 shadow-glow-cyan flex items-center justify-center text-cyan-400 shrink-0 relative z-10">
                <Icon className="w-4 h-4" />
              </div>

              <div className="space-y-0.5 pt-0.5 min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-100">{stage.title}</h4>
                  <span className="text-[10px] font-mono text-cyan-400 font-semibold">Stage 0{idx + 1}</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed font-sans">{stage.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};
