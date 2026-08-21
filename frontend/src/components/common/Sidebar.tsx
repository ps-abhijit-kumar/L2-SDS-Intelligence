import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Layers,
  Search,
  History,
  ShieldAlert,
  GitBranch,
  Settings,
  Activity,
  Cpu,
  ShieldCheck,
  Radio,
} from 'lucide-react';
import { useHealth } from '../../hooks/useHealth';
import { useReviewQueue } from '../../hooks/useHistory';
import { useBatchStatus } from '../../hooks/useBatch';
import { cn } from '../../utils/cn';

interface NavItem {
  name: string;
  to: string;
  icon: React.ElementType;
  badge?: number | string;
  badgeColor?: string;
  highlight?: boolean;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export const Sidebar: React.FC = () => {
  const { data: health } = useHealth();
  const { data: reviewData } = useReviewQueue();
  const { data: batchStatus } = useBatchStatus();

  const pendingReviews = reviewData?.total || 0;
  const isBatchRunning = batchStatus?.status === 'running';

  const sections: NavSection[] = [
    {
      title: 'OVERVIEW',
      items: [
        { name: 'Dashboard', to: '/', icon: LayoutDashboard },
      ],
    },
    {
      title: 'INTELLIGENCE (PRIMARY)',
      items: [
        {
          name: 'Batch Processing',
          to: '/batch',
          icon: Layers,
          badge: isBatchRunning ? 'RUNNING' : 'PRIMARY',
          badgeColor: isBatchRunning
            ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 animate-pulse'
            : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
          highlight: true,
        },
        { name: 'Single SDS Search', to: '/search', icon: Search },
        { name: 'History & Audits', to: '/history', icon: History },
        {
          name: 'Review Queue',
          to: '/review',
          icon: ShieldAlert,
          badge: pendingReviews > 0 ? pendingReviews : undefined,
          badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
        },
      ],
    },
    {
      title: 'AGENT SYSTEM',
      items: [
        { name: 'Agent Trace', to: '/trace', icon: GitBranch },
        { name: 'System Health', to: '/settings', icon: Activity },
      ],
    },
    {
      title: 'CONFIGURATION',
      items: [
        { name: 'Settings', to: '/settings', icon: Settings },
      ],
    },
  ];

  return (
    <aside className="w-64 h-full bg-[#070A12] border-r border-white/[0.07] flex flex-col justify-between shrink-0 select-none z-30">
      {/* Brand Header */}
      <div>
        <div className="p-5 border-b border-white/[0.06] flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 p-0.5 shadow-glow-cyan">
            <div className="w-full h-full bg-[#070A12] rounded-[10px] flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
            </div>
          </div>
          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-sm font-black tracking-widest text-slate-100">◈ L2</span>
              <span className="text-[9px] font-extrabold uppercase px-1.5 py-0.2 bg-cyan-500/20 text-cyan-300 rounded border border-cyan-500/30">
                ENTERPRISE
              </span>
            </div>
            <p className="text-[10px] font-mono tracking-wider uppercase text-slate-400 font-semibold">
              SDS INTELLIGENCE
            </p>
          </div>
        </div>

        {/* Grouped Navigation Links */}
        <nav className="p-4 space-y-6 overflow-y-auto">
          {sections.map((section, sIdx) => (
            <div key={sIdx} className="space-y-1.5">
              <span className="block px-3 text-[10px] font-mono font-bold tracking-wider text-slate-500 uppercase">
                {section.title}
              </span>
              <div className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to + item.name}
                      to={item.to}
                      end={item.to === '/'}
                      className={({ isActive }) =>
                        cn(
                          'group relative flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-150',
                          isActive
                            ? 'bg-[#0D1324] text-cyan-300 border border-cyan-500/30 shadow-glow-cyan'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {/* Active Left Indicator Bar */}
                          {isActive && (
                            <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-gradient-to-b from-cyan-400 to-blue-500 rounded-r-full shadow-glow-cyan" />
                          )}

                          <div className="flex items-center gap-2.5">
                            <Icon
                              className={cn(
                                'w-4 h-4 transition-colors',
                                isActive ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-300'
                              )}
                            />
                            <span>{item.name}</span>
                          </div>

                          {item.badge !== undefined && (
                            <span
                              className={cn(
                                'px-1.5 py-0.5 text-[9px] font-mono font-bold rounded-full border',
                                item.badgeColor || 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
                              )}
                            >
                              {item.badge}
                            </span>
                          )}
                        </>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>

      {/* System Status Footer */}
      <div className="p-4 border-t border-white/[0.06] space-y-3 bg-[#070A12]/90">
        <div className="p-3 rounded-xl bg-[#0B1020] border border-white/[0.06] space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-wider">
                System Operational
              </span>
            </div>
            <Radio className="w-3 h-3 text-slate-500 animate-pulse" />
          </div>

          <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1 border-t border-white/[0.04]">
            <span className="flex items-center gap-1">
              <Cpu className="w-3 h-3 text-cyan-400" />
              L2 AI ENGINE
            </span>
            <span className="text-slate-500">v2.0</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
