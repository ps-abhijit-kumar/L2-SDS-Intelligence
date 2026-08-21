import React from 'react';
import { Search, Inbox, AlertCircle, Sparkles } from 'lucide-react';
import { Button } from './Button';
import { cn } from '../../utils/cn';

interface EmptyStateProps {
  icon?: 'search' | 'inbox' | 'alert';
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = 'inbox',
  title,
  description,
  actionLabel,
  onAction,
  className,
}) => {
  const IconComponent = {
    search: Search,
    inbox: Inbox,
    alert: AlertCircle,
  }[icon];

  return (
    <div
      className={cn(
        'relative flex flex-col items-center justify-center p-8 md:p-12 text-center rounded-2xl border border-white/[0.06] bg-[#0B1020]/60 backdrop-blur-md overflow-hidden',
        className
      )}
    >
      {/* Background Subtle Radial Glow */}
      <div className="absolute inset-0 bg-radial from-cyan-500/5 via-transparent to-transparent pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center">
        <div className="w-14 h-14 rounded-2xl bg-[#070A12] border border-cyan-500/20 shadow-glow-cyan flex items-center justify-center text-cyan-400 mb-4">
          <IconComponent className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-slate-100 mb-1.5">{title}</h3>
        <p className="text-xs text-slate-400 max-w-md leading-relaxed mb-6">{description}</p>
        {actionLabel && onAction && (
          <Button variant="primary" size="sm" onClick={onAction} leftIcon={<Sparkles className="w-3.5 h-3.5" />}>
            {actionLabel}
          </Button>
        )}
      </div>
    </div>
  );
};
