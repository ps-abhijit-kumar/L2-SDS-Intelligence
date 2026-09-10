/**
 * Main Application Shell Layout
 * =============================
 * Architecture Role:
 *   Provides the persistent layout wrapper for the entire SDS Intelligence command center,
 *   including the global sidebar navigation, top header bar, and system status alerts.
 */

import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/common/Sidebar';
import { Header } from '../components/common/Header';
import { useHealth } from '../hooks/useHealth';
import { AlertTriangle } from 'lucide-react';

export const MainLayout: React.FC = () => {
  const { data: health } = useHealth();
  const isKeyMissing = health && !health.groq_configured;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#070A12] text-slate-100 font-sans">
      {/* Command Center Sidebar */}
      <Sidebar />

      {/* Main Command Center Stage */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <Header />

        {/* Global Warning Banner if Groq API Key is unconfigured in .env */}
        {isKeyMissing && (
          <div className="bg-amber-500/10 border-b border-amber-500/30 px-6 py-2.5 flex items-center justify-between text-xs text-amber-300 shrink-0">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                <strong>Groq API Key Required:</strong> Configure <code className="bg-[#070A12] px-1.5 py-0.5 rounded border border-amber-500/30 text-amber-200 font-mono">GROQ_API_KEY</code> in <code className="bg-[#070A12] px-1.5 py-0.5 rounded border border-amber-500/30 text-amber-200 font-mono">.env</code> to execute live autonomous SDS agent workflows.
              </span>
            </div>
          </div>
        )}

        {/* Scrollable Workspace Content */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6">
          <div className="max-w-7xl mx-auto space-y-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
