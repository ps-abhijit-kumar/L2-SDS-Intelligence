import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layers, Search, Sparkles, ShieldCheck, ArrowRight, Activity, Plus } from 'lucide-react';
import { KpiGrid } from '../components/dashboard/KpiGrid';
import { SystemStatusCard } from '../components/dashboard/SystemStatusCard';
import { RecentActivityTable } from '../components/dashboard/RecentActivityTable';
import { PerformanceChart } from '../components/dashboard/PerformanceChart';
import { HistoryDetailModal } from '../components/history/HistoryDetailModal';
import { Button } from '../components/common/Button';
import { useStats } from '../hooks/useStats';
import { useHealth } from '../hooks/useHealth';
import { HistoryItem } from '../types/sds';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: stats, isLoading: isStatsLoading } = useStats();
  const { data: health, isLoading: isHealthLoading } = useHealth();
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);

  return (
    <div className="space-y-6 animate-fade-in pb-8">
      {/* Dashboard Command Center Hero */}
      <div className="relative overflow-hidden rounded-2xl bg-[#0B1020]/90 border border-white/[0.09] p-6 md:p-8 shadow-xl shadow-black/50">
        {/* Ambient Top Glow */}
        <div className="absolute top-0 right-1/4 w-96 h-48 bg-gradient-radial from-cyan-500/15 via-transparent to-transparent pointer-events-none" />

        <div className="relative z-10 max-w-2xl space-y-3.5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-mono font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>AI Safety Data Sheet Intelligence</span>
          </div>

          <h2 className="text-2xl md:text-3xl font-black text-slate-100 tracking-tight leading-tight">
            SDS Intelligence Command Center
          </h2>

          <p className="text-xs md:text-sm text-slate-300 leading-relaxed font-sans">
            Autonomous chemical compliance pipeline. Process batch Excel requests, discover official manufacturer Safety Data Sheets, extract PDF text via PyMuPDF, and validate compliance through Groq LLM function calling.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <Button
              variant="primary"
              size="md"
              onClick={() => navigate('/batch')}
              leftIcon={<Layers className="w-4 h-4" />}
              className="shadow-glow-cyan"
            >
              Start Batch Processing
            </Button>
            <Button
              variant="secondary"
              size="md"
              onClick={() => navigate('/search')}
              leftIcon={<Search className="w-4 h-4 text-cyan-400" />}
            >
              Single Chemical Search
            </Button>
            <Button
              variant="outline"
              size="md"
              onClick={() => navigate('/trace')}
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              Agent Architecture
            </Button>
          </div>
        </div>

        {/* Ambient Compliance Watermark Graphic */}
        <div className="absolute -right-8 -bottom-8 hidden lg:flex items-center justify-center opacity-10 pointer-events-none">
          <ShieldCheck className="w-64 h-64 text-cyan-400" />
        </div>
      </div>

      {/* KPI Telemetry Section */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span>Operational Verification KPIs</span>
        </div>
        <KpiGrid stats={stats} isLoading={isStatsLoading} />
      </div>

      {/* System Subsystem Health & Distribution Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SystemStatusCard health={health} isLoading={isHealthLoading} />
        </div>
        <div>
          <PerformanceChart stats={stats} />
        </div>
      </div>

      {/* Recent Verification Activity */}
      <RecentActivityTable
        items={stats?.recent_searches || []}
        onSelectItem={(item) => setSelectedItem(item)}
      />

      {/* Detail Inspection Modal */}
      <HistoryDetailModal
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
      />
    </div>
  );
};
