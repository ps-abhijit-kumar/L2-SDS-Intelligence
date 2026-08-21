import React from 'react';
import { X, ExternalLink, ShieldAlert, FileText, ShieldCheck } from 'lucide-react';
import { Button } from '../common/Button';

interface DocumentViewerModalProps {
  url: string;
  onClose: () => void;
}

export const DocumentViewerModal: React.FC<DocumentViewerModalProps> = ({ url, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-6 bg-slate-950/85 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-5xl h-[85vh] bg-[#0B1020] border border-white/[0.1] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-slide-up">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between bg-[#070A12] shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
              <FileText className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-slate-100 truncate">
                  Safety Data Sheet Document Intelligence Preview
                </h3>
                <span className="hidden sm:inline-flex px-2 py-0.5 text-[9px] font-mono font-bold rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  Verified
                </span>
              </div>
              <p className="font-mono text-xs text-slate-400 truncate max-w-xl">{url}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-semibold px-3 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 hover:bg-cyan-500/20 transition-all"
            >
              <span>Open in New Tab</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-white/[0.08] rounded-lg transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body / Iframe preview */}
        <div className="flex-1 bg-[#070A12] relative flex flex-col">
          <div className="bg-[#0D1324] px-4 py-2.5 text-xs text-slate-400 border-b border-white/[0.06] flex items-center justify-between">
            <span className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
              <span>Note: Certain external manufacturer portals restrict iframe embedding (X-Frame-Options). Use direct link if required.</span>
            </span>
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:underline font-mono text-xs font-semibold shrink-0 ml-2"
            >
              Direct Link ↗
            </a>
          </div>

          <iframe
            src={url}
            title="Safety Data Sheet Preview"
            className="w-full flex-1 border-0 bg-white"
            sandbox="allow-scripts allow-same-origin allow-popups"
          />
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-white/[0.08] bg-[#070A12] flex justify-end shrink-0">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close Preview
          </Button>
        </div>
      </div>
    </div>
  );
};
