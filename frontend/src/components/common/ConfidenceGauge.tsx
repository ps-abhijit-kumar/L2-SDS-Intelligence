import React from 'react';
import { cn } from '../../utils/cn';
import { ShieldCheck, AlertCircle, AlertTriangle } from 'lucide-react';

interface ConfidenceGaugeProps {
  confidence: number;
  size?: 'sm' | 'md' | 'lg' | 'radial';
  showLabel?: boolean;
  className?: string;
}

export const ConfidenceGauge: React.FC<ConfidenceGaugeProps> = ({
  confidence,
  size = 'md',
  showLabel = true,
  className,
}) => {
  const score = Math.max(0, Math.min(100, confidence || 0));

  let colorClass = 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10 shadow-[0_0_10px_rgba(16,185,129,0.2)]';
  let barGradient = 'from-emerald-500 to-teal-400';
  let qualityText = 'High Confidence Match';
  let QualityIcon = ShieldCheck;

  if (score < 50) {
    colorClass = 'text-rose-400 border-rose-500/30 bg-rose-500/10 shadow-[0_0_10px_rgba(244,63,94,0.2)]';
    barGradient = 'from-rose-500 to-red-500';
    qualityText = 'Low Confidence (Uncertain)';
    QualityIcon = AlertCircle;
  } else if (score < 75) {
    colorClass = 'text-amber-400 border-amber-500/30 bg-amber-500/10 shadow-[0_0_10px_rgba(245,158,11,0.2)]';
    barGradient = 'from-amber-500 to-yellow-400';
    qualityText = 'Moderate Match (Review Suggested)';
    QualityIcon = AlertTriangle;
  }

  if (size === 'sm') {
    return (
      <div className={cn('inline-flex items-center gap-1.5 font-mono text-xs font-bold', className)}>
        <span className={cn('px-2 py-0.5 rounded-full border backdrop-blur-sm', colorClass)}>
          {score}%
        </span>
      </div>
    );
  }

  if (size === 'radial') {
    const radius = 32;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (score / 100) * circumference;

    return (
      <div className={cn('flex items-center gap-4 bg-[#070A12]/80 p-3.5 rounded-xl border border-white/[0.08]', className)}>
        <div className="relative w-20 h-20 flex items-center justify-center shrink-0">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 80 80">
            <circle
              cx="40"
              cy="40"
              r={radius}
              className="stroke-slate-800"
              strokeWidth="6"
              fill="transparent"
            />
            <circle
              cx="40"
              cy="40"
              r={radius}
              className={score >= 75 ? 'stroke-cyan-400' : score >= 50 ? 'stroke-amber-400' : 'stroke-rose-400'}
              strokeWidth="6"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              fill="transparent"
              style={{ transition: 'stroke-dashoffset 0.8s ease-in-out' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-base font-extrabold text-slate-100 tracking-tight">{score}%</span>
            <span className="text-[9px] uppercase tracking-wider text-slate-500 font-semibold">Score</span>
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
            <QualityIcon className="w-3.5 h-3.5 text-cyan-400" />
            <span>{qualityText}</span>
          </div>
          <p className="text-[11px] text-slate-400">
            Deterministic ranking based on manufacturer domain credibility & document verification.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-slate-400 flex items-center gap-1.5">
          <QualityIcon className="w-3.5 h-3.5 text-slate-500" />
          Verification Confidence
        </span>
        <span className="font-mono font-bold text-slate-100 bg-[#070A12] px-2 py-0.5 rounded border border-white/[0.08]">
          {score}%
        </span>
      </div>

      {/* Segmented Gradient Bar */}
      <div className="w-full h-2 bg-[#070A12] border border-white/[0.08] rounded-full overflow-hidden p-0.5">
        <div
          className={cn('h-full bg-gradient-to-r transition-all duration-700 rounded-full shadow-glow-cyan', barGradient)}
          style={{ width: `${score}%` }}
        />
      </div>

      {showLabel && (
        <div className="flex justify-between items-center text-[10px] font-mono text-slate-500">
          <span className="truncate">{qualityText}</span>
          <span>Index: {score}/100</span>
        </div>
      )}
    </div>
  );
};
