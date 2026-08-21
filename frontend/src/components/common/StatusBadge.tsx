import React from 'react';
import { getStatusConfig } from '../../utils/statusColors';
import { SDSStatus } from '../../types/sds';
import { cn } from '../../utils/cn';

interface StatusBadgeProps {
  status: SDSStatus | string;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  glow?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  showIcon = true,
  size = 'md',
  className,
  glow = true,
}) => {
  const config = getStatusConfig(status);
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px] gap-1',
    md: 'px-2.5 py-1 text-xs gap-1.5',
    lg: 'px-3 py-1.5 text-xs font-semibold gap-2',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center font-medium border rounded-full select-none transition-all duration-150 backdrop-blur-sm',
        config.bg,
        config.text,
        config.border,
        glow && config.glow,
        sizeClasses[size],
        className
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', config.dot)} />
      {showIcon && (
        <Icon className={cn(size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5', 'shrink-0')} />
      )}
      <span className="tracking-wide uppercase text-[10px] font-bold">{config.label}</span>
    </span>
  );
};
