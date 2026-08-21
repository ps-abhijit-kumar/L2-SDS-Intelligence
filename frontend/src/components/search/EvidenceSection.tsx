import React from 'react';
import { ShieldCheck, FileCheck, CheckCircle2, MessageSquareText, ShieldAlert } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../common/Card';

interface EvidenceSectionProps {
  reasoning: string;
  productName: string;
  companyName?: string;
  country?: string;
  language?: string;
}

export const EvidenceSection: React.FC<EvidenceSectionProps> = ({
  reasoning,
  productName,
  companyName,
  country,
  language,
}) => {
  return (
    <Card className="space-y-5">
      <CardHeader>
        <CardTitle>
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span>Verification Rationale & Compliance Evidence</span>
        </CardTitle>
        <span className="text-[10px] font-mono text-slate-400">
          OSHA / GHS Validation Report
        </span>
      </CardHeader>

      {/* Target Parameters Cross-Checked */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-[#070A12] p-4 rounded-xl border border-white/[0.06] text-xs">
        <div className="space-y-0.5">
          <span className="text-slate-500 text-[10px] font-mono font-bold uppercase">Product Verified</span>
          <p className="font-semibold text-slate-200 truncate font-sans">{productName}</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-slate-500 text-[10px] font-mono font-bold uppercase">Manufacturer</span>
          <p className="font-semibold text-slate-200 truncate font-sans">{companyName || 'Any / Industry'}</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-slate-500 text-[10px] font-mono font-bold uppercase">Jurisdiction</span>
          <p className="font-semibold text-slate-200 truncate font-sans">{country || 'Global'}</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-slate-500 text-[10px] font-mono font-bold uppercase">Language</span>
          <p className="font-semibold text-slate-200 truncate font-sans">{language || 'English'}</p>
        </div>
      </div>

      {/* Groq LLM Detailed Rationale */}
      <div className="space-y-2">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
          <MessageSquareText className="w-4 h-4 text-cyan-400" />
          <span>Agent Explanation & Evidence Breakdown</span>
        </div>
        <div className="p-4 rounded-xl bg-[#070A12] border border-white/[0.08] text-xs text-slate-300 font-sans leading-relaxed whitespace-pre-wrap selection:bg-cyan-500 selection:text-black">
          {reasoning || 'No additional explanation was returned by the agent.'}
        </div>
      </div>

      {/* Verification Checkpoints */}
      <div className="pt-3 flex flex-wrap items-center gap-4 text-xs text-slate-400 border-t border-white/[0.06]">
        <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>GHS Hazard Elements Cross-Checked</span>
        </div>
        <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Supplier Identity Verified</span>
        </div>
        <div className="flex items-center gap-1.5 text-cyan-400 font-medium">
          <FileCheck className="w-3.5 h-3.5" />
          <span>PyMuPDF Document Body Inspected</span>
        </div>
      </div>
    </Card>
  );
};
