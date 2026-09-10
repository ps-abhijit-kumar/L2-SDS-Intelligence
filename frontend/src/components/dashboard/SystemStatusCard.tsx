import React from 'react';
import { ShieldCheck, Cpu, Database, Network, Globe, FileText, CheckCircle2, AlertCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../common/Card';
import { HealthStatus } from '../../types/sds';
import { formatDate } from '../../utils/formatters';

interface SystemStatusCardProps {
  health?: HealthStatus;
  isLoading?: boolean;
}

export const SystemStatusCard: React.FC<SystemStatusCardProps> = ({ health, isLoading }) => {
  const subsystems = [
    {
      name: 'LangGraph ReAct Core',
      type: 'Agent Engine',
      status: 'OPERATIONAL',
      icon: Cpu,
      detail: 'Cyclic StateGraph (15-step recursion limit)',
      healthy: true,
    },
    {
      name: 'Groq Cloud LLM',
      type: 'Semantic Reasoning',
      status: health?.groq_configured ? 'OPERATIONAL' : 'KEY REQUIRED',
      icon: Network,
      detail: health?.groq_model || 'openai/gpt-oss-120b',
      healthy: !!health?.groq_configured,
    },
    {
      name: 'FastMCP Protocol Server',
      type: 'Stdio Storage Interface',
      status: health?.mcp_server_available ? 'OPERATIONAL' : 'UNAVAILABLE',
      icon: Database,
      detail: 'src/mcp/mcp_server.py (Persistent Excel memory)',
      healthy: !!health?.mcp_server_available,
    },
    {
      name: 'PyMuPDF Text Extractor',
      type: 'Document Reader',
      status: 'OPERATIONAL',
      icon: FileText,
      detail: 'Binary PDF extraction (fitz backend)',
      healthy: true,
    },
    {
      name: 'DuckDuckGo Discovery Tool',
      type: 'Search Provider',
      status: 'OPERATIONAL',
      icon: Globe,
      detail: 'ddgs web scraper & query ranker',
      healthy: true,
    },
    {
      name: 'Evaluation Excel Dataset',
      type: 'Persistent Memory',
      status: health?.excel_file_available ? 'ATTACHED' : 'NOT FOUND',
      icon: Database,
      detail: 'sample_requests_eval.xlsx',
      healthy: !!health?.excel_file_available,
    },
  ];

  return (
    <Card className="space-y-4">
      <CardHeader>
        <CardTitle>
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span>L2 Subsystem Health & Telemetry</span>
        </CardTitle>
        <span className="text-[10px] font-mono text-slate-400">
          Last Check: {health?.timestamp ? formatDate(health.timestamp) : 'Live'}
        </span>
      </CardHeader>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        {subsystems.map((sys, idx) => {
          const Icon = sys.icon;
          return (
            <div
              key={idx}
              className="p-3 rounded-xl bg-[#070A12]/80 border border-white/[0.06] hover:border-cyan-500/30 transition-all flex flex-col justify-between space-y-2 group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-[#0B1020] border border-white/[0.08] flex items-center justify-center text-cyan-400 group-hover:text-cyan-300">
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-200">{sys.name}</h4>
                    <span className="text-[9px] font-mono text-slate-500 uppercase">{sys.type}</span>
                  </div>
                </div>

                <span
                  className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-bold border ${
                    sys.healthy
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${sys.healthy ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                  {sys.status}
                </span>
              </div>

              <p className="text-[10px] font-mono text-slate-400 truncate pt-1 border-t border-white/[0.04]">
                {sys.detail}
              </p>
            </div>
          );
        })}
      </div>
    </Card>
  );
};
