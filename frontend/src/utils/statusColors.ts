import { CheckCircle2, AlertTriangle, XCircle, Clock, ShieldCheck, HelpCircle } from 'lucide-react';
import React from 'react';
import { SDSStatus } from '../types/sds';

export interface StatusConfig {
  label: string;
  bg: string;
  text: string;
  border: string;
  dot: string;
  glow: string;
  icon: React.ElementType;
}

export function getStatusConfig(status: SDSStatus | string): StatusConfig {
  const norm = (status || '').toUpperCase().trim();
  switch (norm) {
    case 'EXACT MATCH':
      return {
        label: 'Exact Match',
        bg: 'bg-emerald-500/10',
        text: 'text-emerald-400',
        border: 'border-emerald-500/30',
        dot: 'bg-emerald-400',
        glow: 'shadow-[0_0_12px_rgba(16,185,129,0.25)]',
        icon: CheckCircle2,
      };
    case 'BEST AVAILABLE':
      return {
        label: 'Best Available',
        bg: 'bg-cyan-500/10',
        text: 'text-cyan-400',
        border: 'border-cyan-500/30',
        dot: 'bg-cyan-400',
        glow: 'shadow-[0_0_12px_rgba(6,182,212,0.25)]',
        icon: ShieldCheck,
      };
    case 'NEEDS REVIEW':
      return {
        label: 'Needs Review',
        bg: 'bg-amber-500/10',
        text: 'text-amber-400',
        border: 'border-amber-500/30',
        dot: 'bg-amber-400',
        glow: 'shadow-[0_0_12px_rgba(245,158,11,0.25)]',
        icon: AlertTriangle,
      };
    case 'NOT FOUND':
      return {
        label: 'Not Found',
        bg: 'bg-rose-500/10',
        text: 'text-rose-400',
        border: 'border-rose-500/30',
        dot: 'bg-rose-400',
        glow: 'shadow-[0_0_12px_rgba(244,63,94,0.25)]',
        icon: HelpCircle,
      };
    case 'ERROR':
      return {
        label: 'Error',
        bg: 'bg-red-500/10',
        text: 'text-red-400',
        border: 'border-red-500/30',
        dot: 'bg-red-400',
        glow: 'shadow-[0_0_12px_rgba(239,68,68,0.25)]',
        icon: XCircle,
      };
    default:
      return {
        label: status || 'Pending',
        bg: 'bg-slate-500/10',
        text: 'text-slate-400',
        border: 'border-slate-700/50',
        dot: 'bg-slate-400',
        glow: '',
        icon: Clock,
      };
  }
}
