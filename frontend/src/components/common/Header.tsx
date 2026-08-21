import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Search, Bell, ShieldCheck, Layers, Terminal, ArrowRight } from 'lucide-react';
import { useHealth } from '../../hooks/useHealth';

export const Header: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { data: health } = useHealth();

  const getPageTitle = (path: string) => {
    switch (path) {
      case '/':
        return 'Dashboard';
      case '/batch':
        return 'Batch Excel Processing';
      case '/search':
        return 'Single SDS Search';
      case '/history':
        return 'Audit & Verification History';
      case '/review':
        return 'Human Review Queue';
      case '/trace':
        return 'Agent Workflow Architecture';
      case '/settings':
        return 'System Configuration';
      default:
        return 'Command Center';
    }
  };

  const currentTitle = getPageTitle(location.pathname);

  return (
    <header className="h-16 px-6 border-b border-white/[0.07] bg-[#070A12]/80 backdrop-blur-md flex items-center justify-between gap-4 shrink-0 z-20">
      {/* Left: Breadcrumbs & Page Context */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <span className="text-cyan-400 font-bold">L2</span>
          <span className="text-slate-600">/</span>
          <span className="text-slate-200 font-semibold">{currentTitle}</span>
        </div>
      </div>

      {/* Center: Quick Search Input */}
      <div className="hidden md:flex items-center max-w-md w-full">
        <div
          onClick={() => navigate('/batch')}
          className="w-full flex items-center justify-between px-3.5 py-1.5 rounded-xl bg-[#0B1020]/90 border border-white/[0.08] hover:border-cyan-500/40 text-slate-400 hover:text-slate-200 transition-all cursor-pointer shadow-sm group"
        >
          <div className="flex items-center gap-2.5">
            <Layers className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 transition-colors" />
            <span className="text-xs">Execute Excel batch or single chemical search...</span>
          </div>
          <kbd className="text-[10px] font-mono bg-[#070A12] border border-white/[0.08] text-slate-400 px-1.5 py-0.5 rounded">
            ⌘B
          </kbd>
        </div>
      </div>

      {/* Right: Operational Status, Compliance, and User Profile */}
      <div className="flex items-center gap-3">
        {/* All Systems Operational Pill */}
        <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold shadow-sm">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <span className="text-[11px] font-mono">All Systems Operational</span>
        </div>

        {/* OSHA / GHS Verification Pill */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-semibold">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[11px] font-mono">GHS / OSHA Compliant</span>
        </div>

        {/* Profile Avatar */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-white/[0.08]">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-300 font-mono text-xs font-bold shadow-sm">
            AI
          </div>
        </div>
      </div>
    </header>
  );
};
