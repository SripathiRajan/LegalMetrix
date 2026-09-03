import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { AuthModal } from './components/AuthModal';
import { OfficerPortal } from './components/OfficerPortal';
import { AdminPanel } from './components/AdminPanel';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function AppContent() {
  const [mode, setMode] = useState<'officer' | 'admin'>('officer');
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  return (
    <>
      <div className="mode-bar">
        <span>Preview — choose an experience</span>
        <button 
          className={`mode-btn ${mode === 'officer' ? 'active' : ''}`} 
          onClick={() => setMode('officer')}
        >
          Officer Portal
        </button>
        <button 
          className={`mode-btn ${mode === 'admin' ? 'active' : ''}`} 
          onClick={() => setMode('admin')}
        >
          Admin Panel
        </button>
      </div>

      {mode === 'officer' && <OfficerPortal onOpenAuth={() => setIsAuthModalOpen(true)} />}
      {mode === 'admin' && <AdminPanel />}

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </>
  );
}

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
