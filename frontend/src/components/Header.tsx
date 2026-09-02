import React from 'react';
import { 
  Scan, 
  BarChart3, 
  History, 
  Bot, 
  LogIn, 
  LogOut, 
  Scale,
  Sparkles
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export type TabType = 'scan' | 'dashboard' | 'history' | 'assistant';

interface HeaderProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  onOpenAuth: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  onOpenAuth,
}) => {
  const { user, isAuthenticated, logout } = useAuth();

  const navItems: { id: TabType; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: 'scan', label: 'Scan & Inspect', icon: <Scan className="w-4 h-4" /> },
    { id: 'dashboard', label: 'Analytics Dashboard', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'history', label: 'Audit History', icon: <History className="w-4 h-4" /> },
    { id: 'assistant', label: 'Legal Assistant', icon: <Bot className="w-4 h-4" />, badge: 'DoCA AI' },
  ];

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('scan')}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center shadow-glow">
            <Scale className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-display font-bold text-xl tracking-tight text-white">
                Legal<span className="text-brand-400">Metrix</span>
              </span>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-300 border border-brand-500/20">
                PCR 2011
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Dept. of Consumer Affairs Compliance Engine
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center space-x-1 sm:space-x-2">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`relative flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-brand-500/15 text-brand-300 border border-brand-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                {item.icon}
                <span className="hidden md:inline">{item.label}</span>
                {item.badge && (
                  <span className="hidden lg:inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    <Sparkles className="w-2.5 h-2.5 mr-0.5" />
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Auth / Profile Area */}
        <div className="flex items-center space-x-3">
          {isAuthenticated && user ? (
            <div className="flex items-center space-x-3 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg">
              <div className="w-7 h-7 rounded-full bg-brand-600/30 border border-brand-500/40 flex items-center justify-center text-brand-300 font-semibold text-xs">
                {user.username.charAt(0).toUpperCase()}
              </div>
              <div className="hidden sm:block text-left">
                <p className="text-xs font-medium text-slate-200">{user.username}</p>
                <p className="text-[10px] text-slate-400 capitalize">{user.role} {user.badge_number ? `• #${user.badge_number}` : ''}</p>
              </div>
              <button
                onClick={logout}
                title="Sign Out"
                className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="flex items-center space-x-1.5 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-xs font-semibold px-3.5 py-2 rounded-lg shadow-md transition-all active:scale-95"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Officer Login</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
