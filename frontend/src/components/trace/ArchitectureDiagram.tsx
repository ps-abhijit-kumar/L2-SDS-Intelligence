import React, { useState } from 'react';
import {
  Search,
  ListOrdered,
  FileDown,
  FileText,
  BrainCircuit,
  CheckCircle2,
  Database,
  ArrowRight,
  Sparkles,
  Info,
  Terminal,
} from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../common/Card';
import { cn } from '../../utils/cn';

interface NodeDetail {
  id: string;
  name: string;
  type: string;
  description: string;
  inputs: string;
  outputs: string;
  tech: string;
}

const NODES: NodeDetail[] = [
  {
    id: 'input',
    name: 'Chemical Request Input',
    type: 'Entry Point',
    description: 'Receives target chemical product name, manufacturer company, jurisdiction, and language.',
    inputs: 'Product Name, Company, Country, Language',
    outputs: 'SDSState initialization dictionary with messages',
    tech: 'FastAPI / Pydantic SDSValidationResult',
  },
  {
    id: 'search',
    name: 'search_duckduckgo',
    type: 'Agent Tool',
    description: 'Executes targeted web search queries tailored for official manufacturer safety documents.',
    inputs: 'Target query string (e.g. "Acetone 99% Sigma-Aldrich SDS PDF")',
    outputs: 'Raw web results (URLs + text snippets)',
    tech: 'ddgs / DuckDuckGo Search API',
  },
  {
    id: 'rank',
    name: 'rank_sds_candidates',
    type: 'Deterministic Ranker Tool',
    description: 'Scores URL candidates using domain credibility heuristics, company name matching, and PDF priority.',
    inputs: 'List of candidate URLs + target product & company',
    outputs: 'Ranked candidate list sorted by score (0-100)',
    tech: 'Python urllib.parse / Keyword matcher',
  },
  {
    id: 'fetch',
    name: 'fetch_document_text',
    type: 'Document Extractor Tool',
    description: 'Fetches candidate URLs, parses PDF binary streams or HTML, and extracts safety text snippets.',
    inputs: 'Candidate URL',
    outputs: 'First-page text extract (first 800 chars) or HTML text',
    tech: 'PyMuPDF (fitz) & BeautifulSoup4',
  },
  {
    id: 'llm',
    name: 'Groq Cloud LLM Validation',
    type: 'LangGraph Reasoning Node',
    description: 'Analyzes document evidence against OSHA/GHS standards to verify manufacturer, chemical name, and language.',
    inputs: 'Prompt history + Document Text + Candidate info',
    outputs: 'SDSValidationResult schema (status, confidence, reasoning, url)',
    tech: 'LangChain Groq (openai/gpt-oss-120b)',
  },
  {
    id: 'mcp',
    name: 'FastMCP Excel Storage',
    type: 'MCP Server Integration',
    description: 'Protocol server exposing tools to inspect pending requests and update records in Excel spreadsheets.',
    inputs: 'Row ID + Status + URL + Confidence + Reasoning',
    outputs: 'Updated Excel evaluation spreadsheet',
    tech: 'FastMCP / openpyxl / pandas / Stdio transport',
  },
  {
    id: 'decision',
    name: 'Final Decision & Schema Extraction',
    type: 'Exit Node',
    description: 'Performs URL sanity validation, downgrades placeholders/low confidence, and returns final state.',
    inputs: 'Agent tool call or reasoning text',
    outputs: 'EXACT MATCH | BEST AVAILABLE | NEEDS REVIEW',
    tech: 'LangGraph extract_final_node',
  },
];

export const ArchitectureDiagram: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<NodeDetail>(NODES[0]);

  return (
    <div className="space-y-6">
      {/* Visual Pipeline Flow */}
      <Card className="space-y-6">
        <CardHeader>
          <CardTitle>
            <BrainCircuit className="w-5 h-5 text-cyan-400" />
            <span>Autonomous LangGraph & MCP Agent Architecture</span>
          </CardTitle>
          <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/80 px-2.5 py-1 rounded-full border border-cyan-500/30">
            Cyclic StateGraph Pipeline
          </span>
        </CardHeader>

        {/* Nodes Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {NODES.map((node) => {
            const isSelected = selectedNode.id === node.id;
            return (
              <div
                key={node.id}
                onClick={() => setSelectedNode(node)}
                className={cn(
                  'p-4 rounded-xl border transition-all duration-200 cursor-pointer flex flex-col justify-between space-y-3',
                  isSelected
                    ? 'bg-[#0D1324] border-cyan-400 shadow-glow-cyan ring-1 ring-cyan-400/50'
                    : 'bg-[#070A12] border-white/[0.07] hover:border-white/[0.15] hover:bg-[#0B1020]'
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[9px] uppercase font-mono font-bold text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-500/30">
                    {node.type}
                  </span>
                  {isSelected && <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />}
                </div>

                <div>
                  <h4 className="text-xs font-bold text-slate-100">{node.name}</h4>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed font-sans">
                    {node.description}
                  </p>
                </div>

                <div className="pt-2 border-t border-white/[0.04] flex items-center justify-between text-[10px] text-slate-500 font-mono">
                  <span className="truncate">{node.tech.split('/')[0]}</span>
                  <ArrowRight className="w-3 h-3 text-slate-500" />
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Selected Node Deep Dive */}
      <Card variant="elevated" className="border-cyan-500/20 space-y-4">
        <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div className="flex items-center gap-2.5">
            <Info className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-slate-100">
              Component Specification: <span className="text-cyan-300 font-mono">{selectedNode.name}</span>
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-400 bg-[#070A12] px-2.5 py-1 rounded-lg border border-white/[0.08]">
            {selectedNode.type}
          </span>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed font-sans">
          {selectedNode.description}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
          <div className="p-3 bg-[#070A12] rounded-xl border border-white/[0.06] space-y-1">
            <span className="text-[9px] font-mono font-bold uppercase text-slate-500">Input Data</span>
            <p className="text-xs font-mono text-slate-300">{selectedNode.inputs}</p>
          </div>
          <div className="p-3 bg-[#070A12] rounded-xl border border-white/[0.06] space-y-1">
            <span className="text-[9px] font-mono font-bold uppercase text-slate-500">Output Data</span>
            <p className="text-xs font-mono text-slate-300">{selectedNode.outputs}</p>
          </div>
          <div className="p-3 bg-[#070A12] rounded-xl border border-white/[0.06] space-y-1">
            <span className="text-[9px] font-mono font-bold uppercase text-slate-500">Underlying Technology</span>
            <p className="text-xs font-mono text-cyan-400">{selectedNode.tech}</p>
          </div>
        </div>
      </Card>
    </div>
  );
};
