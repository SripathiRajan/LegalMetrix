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
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-brand-500 selection:text-white">
      {/* Top Navbar */}
      <Header
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
        }}
        onOpenAuth={() => setIsAuthModalOpen(true)}
      />

      {/* Main View Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {activeTab === 'scan' && (
          <>
            {scanResult ? (
              <LiveResultsView
                result={scanResult}
                originalImageSrc={originalImageSrc}
                onReset={handleResetScan}
              />
            ) : (
              <ScanUpload onScanComplete={handleScanComplete} />
            )}
          </>
        )}

        {activeTab === 'dashboard' && <DashboardView />}

        {activeTab === 'history' && <ScanHistoryView />}

        {activeTab === 'assistant' && <ChatAssistant />}
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-slate-900 bg-slate-950/80 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            LegalMetrix AI • Department of Consumer Affairs (DoCA) Compliance Suite
          </span>
          <span className="text-[11px] text-slate-600">
            Legal Metrology (Packaged Commodities) Rules, 2011 • DINOv2 Visual Authenticity
          </span>
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
