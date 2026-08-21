import React, { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Card, CardHeader, CardTitle } from '../common/Card';
import { PieChart as PieIcon, Activity } from 'lucide-react';
import { StatsResponse } from '../../types/sds';

interface PerformanceChartProps {
  stats?: StatsResponse;
}

const COLORS: Record<string, string> = {
  'Exact Match': '#10B981', // Emerald
  'Best Available': '#00F2FE', // Cyan
  'Needs Review': '#F59E0B', // Amber
  'Errors': '#F43F5E', // Rose
};

export const PerformanceChart: React.FC<PerformanceChartProps> = ({ stats }) => {
  const [timeRange, setTimeRange] = useState<'7D' | '30D' | 'ALL'>('ALL');

  const total = stats?.total_searches ?? 0;
  const exact = stats?.exact_matches ?? 0;
  const best = stats?.best_available ?? 0;
  const review = stats?.needs_review ?? 0;
  const errors = stats?.errors ?? 0;

  const data = [
    { name: 'Exact Match', value: exact },
    { name: 'Best Available', value: best },
    { name: 'Needs Review', value: review },
    { name: 'Errors', value: errors },
  ].filter((item) => item.value > 0);

  const hasData = data.length > 0 && total > 0;

  return (
    <Card className="space-y-4">
      <CardHeader>
        <CardTitle>
          <PieIcon className="w-4 h-4 text-cyan-400" />
          <span>Verification Distribution</span>
        </CardTitle>
        <div className="flex items-center gap-1 bg-[#070A12] p-0.5 rounded-lg border border-white/[0.08]">
          {(['7D', '30D', 'ALL'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded transition-colors ${
                timeRange === range
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </CardHeader>

      {!hasData ? (
        <div className="flex flex-col items-center justify-center h-48 text-center text-xs text-slate-500 space-y-1">
          <Activity className="w-6 h-6 text-slate-700 mb-1" />
          <p>No verification data available yet</p>
          <span className="text-[10px] text-slate-600">Run searches to populate distribution metrics</span>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="h-44 w-full relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={48}
                  outerRadius={68}
                  paddingAngle={4}
                  dataKey="value"
                  stroke="rgba(0,0,0,0.5)"
                  strokeWidth={2}
                >
                  {data.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[entry.name] || '#64748B'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#070A12',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#F1F5F9',
                  }}
                  itemStyle={{ color: '#00F2FE' }}
                />
              </PieChart>
            </ResponsiveContainer>

            {/* Center Summary Metric */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="font-mono text-xl font-extrabold text-slate-100">{total}</span>
              <span className="text-[9px] uppercase tracking-wider text-slate-500 font-semibold">Total</span>
            </div>
          </div>

          {/* Legend Grid */}
          <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/[0.04]">
            {data.map((item) => (
              <div key={item.name} className="flex items-center justify-between text-xs p-1.5 rounded bg-[#070A12]/60">
                <div className="flex items-center gap-1.5 truncate">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: COLORS[item.name] || '#64748B' }}
                  />
                  <span className="text-slate-400 text-[11px] truncate">{item.name}</span>
                </div>
                <span className="font-mono font-bold text-slate-200 text-[11px]">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};
