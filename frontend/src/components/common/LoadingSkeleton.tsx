import React from 'react';
import { cn } from '../../utils/cn';

export const Skeleton: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('animate-pulse bg-[#162036]/60 rounded-lg border border-white/[0.04]', className)} />
);

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="space-y-3">
    <Skeleton className="h-11 w-full rounded-xl" />
    {Array.from({ length: rows }).map((_, i) => (
      <Skeleton key={i} className="h-16 w-full rounded-xl" />
    ))}
  </div>
);

export const CardSkeleton: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('bg-[#0B1020]/80 border border-white/[0.07] rounded-xl p-5 space-y-4', className)}>
    <div className="flex justify-between items-center">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-4 w-12" />
    </div>
    <Skeleton className="h-9 w-2/3" />
    <Skeleton className="h-3.5 w-1/2" />
  </div>
);
