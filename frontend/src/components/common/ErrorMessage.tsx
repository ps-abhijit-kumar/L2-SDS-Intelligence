import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';
import { cn } from '../../utils/cn';

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  title = 'Execution Warning',
  message,
  onRetry,
  className,
}) => {
  return (
    <div
      className={cn(
        'p-5 rounded-2xl border border-rose-500/30 bg-[#160b14]/80 backdrop-blur-md flex items-start gap-4 shadow-lg shadow-rose-950/20 text-slate-200',
        className
      )}
    >
      <div className="w-10 h-10 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 shrink-0 mt-0.5 shadow-sm shadow-rose-500/20">
        <AlertTriangle className="w-5 h-5" />
      </div>
      <div className="space-y-1.5 flex-1 min-w-0">
        <h4 className="text-sm font-bold text-rose-300 tracking-tight">{title}</h4>
        <p className="text-xs text-rose-200/80 leading-relaxed font-sans">{message}</p>
        {onRetry && (
          <div className="pt-2">
            <Button
              variant="danger"
              size="sm"
              onClick={onRetry}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Retry Agent Execution
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};
