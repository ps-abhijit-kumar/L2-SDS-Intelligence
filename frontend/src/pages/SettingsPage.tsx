import React from 'react';
import { Settings, Cpu, Database, Layers, CheckCircle2, Shield, Radio, Terminal } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../components/common/Card';
import { useHealth } from '../hooks/useHealth';

export const SettingsPage: React.FC = () => {
  const { data: health, isLoading } = useHealth();

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      <div className="space-y-1">
        <h2 className="text-xl font-black text-slate-100 flex items-center gap-2.5">
          <Settings className="w-5 h-5 text-cyan-400" />
          <span>System Environment & Model Configuration</span>
        </h2>
        <p className="text-xs text-slate-400 font-sans">
          Operational parameters connecting the frontend application to the FastAPI server, Groq Cloud, and FastMCP.
        </p>
      </div>

      {/* Backend & Inference Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card variant="elevated" className="space-y-4">
          <CardHeader>
            <CardTitle>
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>Active Inference Engine</span>
            </CardTitle>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
              Active
            </span>
          </CardHeader>

          <div className="space-y-3 text-xs">
            <div className="p-3.5 bg-[#070A12] rounded-xl border border-white/[0.06] flex justify-between items-center">
              <span className="text-slate-400">Inference Provider</span>
              <span className="font-semibold text-slate-200">Groq Cloud API</span>
            </div>
            <div className="p-3.5 bg-[#070A12] rounded-xl border border-white/[0.06] flex justify-between items-center">
              <span className="text-slate-400">Active Model</span>
              <span className="font-mono text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/30">
                {health?.groq_model || 'openai/gpt-oss-120b'}
              </span>
            </div>
            <div className="p-3.5 bg-[#070A12] rounded-xl border border-white/[0.06] flex justify-between items-center">
              <span className="text-slate-400">Tool Calling Mode</span>
              <span className="font-semibold text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Native Function Calling
              </span>
            </div>
            <div className="p-3.5 bg-[#070A12] rounded-xl border border-white/[0.06] flex justify-between items-center">
              <span className="text-slate-400">Recursion Limit</span>
              <span className="font-mono text-slate-200">15 ReAct Cycles</span>
            </div>
          </div>
        </Card>

        <Card variant="elevated" className="space-y-4">
          <CardHeader>
            <CardTitle>
              <Database className="w-4 h-4 text-purple-400" />
              <span>Storage & MCP Protocol Endpoints</span>
            </CardTitle>
            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/30">
              Attached
            </span>
          </CardHeader>

          <div className="space-y-3 text-xs">
            <div className="p-3.5 bg-[#070A12] rounded-xl border border-white/[0.06] flex justify-between items-center">
              <span className="text-slate-400">FastAPI Base URL</span>
              <span className="font-mono text-slate-200">{import.meta.env.VITE_API_BASE_URL || '/api'}</span>
            </div>
            <div className="p-3.5 bg-[#070A12] rounded-xl border border-white/[0.06] flex justify-between items-center">
              <span className="text-slate-400">Active Excel File</span>
              <span className="font-mono text-cyan-300">{health?.active_file || 'sample_requests_eval.xlsx'}</span>
            </div>
            <div className="p-3.5 bg-[#070A12] rounded-xl border border-white/[0.06] flex justify-between items-center">
              <span className="text-slate-400">Audit Log Storage</span>
              <span className="font-mono text-slate-200">logs/agent_trace.jsonl</span>
            </div>
            <div className="p-3.5 bg-[#070A12] rounded-xl border border-white/[0.06] flex justify-between items-center">
              <span className="text-slate-400">FastMCP Protocol Server</span>
              <span className="font-mono text-emerald-400">src/mcp/mcp_server.py (Stdio)</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Enterprise Security Notice */}
      <Card className="bg-[#0B1020]/70 border-white/[0.07] space-y-3">
        <div className="flex items-center gap-2 text-sm font-bold text-slate-200">
          <Shield className="w-4 h-4 text-cyan-400" />
          <span>Enterprise Security & Credential Isolation</span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed font-sans">
          The SDS Intelligence Platform is architected with strict separation of concerns. Secret credentials (<code className="text-cyan-300 font-mono">GROQ_API_KEY</code>) reside exclusively on the backend server environment and are never transmitted to client browsers.
        </p>
      </Card>
    </div>
  );
};
