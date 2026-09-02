import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { Header } from './components/Header';
import type { TabType } from './components/Header';
import { ScanUpload } from './components/ScanUpload';
import { LiveResultsView } from './components/LiveResultsView';
import { DashboardView } from './components/DashboardView';
import { ScanHistoryView } from './components/ScanHistoryView';
import { ChatAssistant } from './components/ChatAssistant';
import { AuthModal } from './components/AuthModal';
import type { AnalyzeScanResponse } from './types/api';
import { Shield, ExternalLink } from 'lucide-react';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const AppContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('scan');
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [scanResult, setScanResult] = useState<AnalyzeScanResponse | null>(null);
  const [originalImageSrc, setOriginalImageSrc] = useState<string>('');

  const handleScanComplete = (result: AnalyzeScanResponse, imageSrc: string) => {
    setScanResult(result);
    setOriginalImageSrc(imageSrc);
  };

  const handleResetScan = () => {
    setScanResult(null);
    setOriginalImageSrc('');
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--surface-0)' }}>
      {/* Top Navbar */}
      <Header
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
        }}
        onOpenAuth={() => setIsAuthModalOpen(true)}
      />

      {/* Main View Area */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-7 sm:py-9">
        {activeTab === 'scan' && (
          <>
            {scanResult ? (
              <LiveResultsView
                result={scanResult}
                originalImageSrc={originalImageSrc}
                onReset={handleResetScan}
                onOpenChat={() => setActiveTab('assistant')}
              />
            ) : (
              <ScanUpload onScanComplete={handleScanComplete} />
            )}
          </>
        )}

        {activeTab === 'dashboard' && <DashboardView />}
        {activeTab === 'history' && <ScanHistoryView />}
        {activeTab === 'assistant' && (
          <ChatAssistant
            scanResult={scanResult}
            originalImageSrc={originalImageSrc}
            onOpenScanTab={() => setActiveTab('scan')}
            onClose={() => setActiveTab('scan')}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="w-full border-t py-5" style={{ borderColor: 'rgba(255,255,255,0.04)', background: 'rgba(8,15,30,0.8)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 text-xs text-slate-500">
            <div className="w-6 h-6 rounded-lg flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, rgba(1,113,199,0.3), rgba(79,70,229,0.3))', border: '1px solid rgba(14,165,233,0.2)' }}
            >
              <Shield className="w-3.5 h-3.5 text-sky-400" />
            </div>
            <span>
              <span className="text-slate-300 font-semibold">LegalMetrix AI</span>
              {' '}· Legal Compliance Platform
            </span>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-slate-600">
            <span>Packaged Commodities Compliance · 2011</span>
            <span className="hidden sm:inline">·</span>
            <span className="hidden sm:flex items-center gap-1">
              Visual Authenticity Verification
              <ExternalLink className="w-3 h-3" />
            </span>
          </div>
        </div>
      </footer>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </div>
  );
};

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
