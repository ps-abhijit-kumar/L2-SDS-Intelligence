import React from 'react';
import { Search, CheckCircle2, AlertTriangle, TrendingUp, Percent, Sparkles, Activity } from 'lucide-react';
import { StatsResponse } from '../../types/sds';
import { cn } from '../../utils/cn';

interface KpiGridProps {
  stats?: StatsResponse;
  isLoading?: boolean;
}

export const KpiGrid: React.FC<KpiGridProps> = ({ stats, isLoading }) => {
  const cards = [
    {
      title: 'TOTAL VERIFICATIONS',
      value: stats?.total_searches ?? 0,
      icon: Search,
      accent: 'from-cyan-500 to-blue-500',
      iconColor: 'text-cyan-400',
      borderGlow: 'hover:border-cyan-500/40 hover:shadow-glow-cyan',
      description: 'Processed via LangGraph agent',
    },
    {
      title: 'VERIFIED SDS',
      value: (stats?.exact_matches ?? 0) + (stats?.best_available ?? 0),
      icon: CheckCircle2,
      accent: 'from-emerald-500 to-teal-500',
      iconColor: 'text-emerald-400',
      borderGlow: 'hover:border-emerald-500/40 hover:shadow-glow-emerald',
      description: 'Exact & high-confidence matches',
    },
    {
      title: 'NEEDS REVIEW',
      value: stats?.needs_review ?? 0,
      icon: AlertTriangle,
      accent: 'from-amber-500 to-yellow-500',
      iconColor: 'text-amber-400',
      borderGlow: 'hover:border-amber-500/40 hover:shadow-glow-amber',
      description: 'Flagged for compliance review',
    },
    {
      title: 'RESOLUTION RATE',
      value: `${stats?.resolution_rate ?? 0}%`,
      icon: TrendingUp,
      accent: 'from-blue-500 to-indigo-500',
      iconColor: 'text-blue-400',
      borderGlow: 'hover:border-blue-500/40 hover:shadow-glow-purple',
      description: 'Automated match accuracy ratio',
    },
    {
      title: 'AVG CONFIDENCE',
      value: `${stats?.avg_confidence ?? 0}%`,
      icon: Percent,
      accent: 'from-purple-500 to-pink-500',
      iconColor: 'text-purple-400',
      borderGlow: 'hover:border-purple-500/40 hover:shadow-glow-purple',
      description: 'Mean utility score index',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={cn(
              'relative bg-[#0B1020]/80 backdrop-blur-md border border-white/[0.07] rounded-xl p-4 transition-all duration-200 group overflow-hidden shadow-lg shadow-black/40',
              card.borderGlow
            )}
          >
            {/* Top Glowing Accent Line */}
            <div className={cn('absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r opacity-50 group-hover:opacity-100 transition-opacity', card.accent)} />

            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono font-bold tracking-wider text-slate-400 uppercase">
                {card.title}
              </span>
              <div className="w-7 h-7 rounded-lg bg-[#070A12] border border-white/[0.08] flex items-center justify-center">
                <Icon className={cn('w-3.5 h-3.5', card.iconColor)} />
              </div>
            </div>

            <div className="space-y-1">
              <p className="text-2xl font-black text-slate-100 tracking-tight font-mono">
                {isLoading ? '...' : card.value}
              </p>
              <p className="text-[10px] text-slate-400 leading-tight">
                {card.description}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
