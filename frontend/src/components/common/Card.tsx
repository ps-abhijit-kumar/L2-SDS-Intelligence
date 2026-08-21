import React from 'react';
import { cn } from '../../utils/cn';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean;
  variant?: 'default' | 'elevated' | 'glass';
  glow?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  hoverEffect = false,
  variant = 'default',
  glow = false,
  ...props
}) => {
  const variantStyles = {
    default: 'bg-[#0B1020]/80 backdrop-blur-md border border-white/[0.07] shadow-lg shadow-black/40',
    elevated: 'bg-[#0D1324]/90 backdrop-blur-lg border border-white/[0.09] shadow-xl shadow-black/50',
    glass: 'bg-[#070A12]/60 backdrop-blur-xl border border-cyan-500/20 shadow-glow-cyan',
  };

  return (
    <div
      className={cn(
        'rounded-xl p-5 transition-all duration-200 relative overflow-hidden',
        variantStyles[variant],
        hoverEffect && 'hover:border-cyan-500/30 hover:shadow-glow-cyan hover:bg-[#0D1324]/90 hover:-translate-y-0.5',
        glow && 'border-cyan-500/30 shadow-glow-cyan',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={cn('flex items-center justify-between pb-3.5 border-b border-white/[0.06] mb-4', className)} {...props}>
    {children}
  </div>
);

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  className,
  children,
  ...props
}) => (
  <h3 className={cn('text-sm font-semibold text-slate-100 flex items-center gap-2.5 tracking-tight', className)} {...props}>
    {children}
  </h3>
);
