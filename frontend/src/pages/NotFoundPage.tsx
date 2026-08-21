import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowLeft } from 'lucide-react';
import { Button } from '../components/common/Button';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-4">
      <div className="w-14 h-14 rounded-2xl bg-[#070A12] border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-glow-amber">
        <ShieldAlert className="w-7 h-7" />
      </div>
      <h2 className="text-2xl font-black text-slate-100">404 - Command Not Found</h2>
      <p className="text-xs text-slate-400 max-w-sm font-sans">
        The requested resource or workspace route does not exist in the SDS Intelligence Platform.
      </p>
      <Button
        variant="outline"
        size="sm"
        onClick={() => navigate('/')}
        leftIcon={<ArrowLeft className="w-4 h-4" />}
      >
        Return to Command Center
      </Button>
    </div>
  );
};
