import React, { useState } from 'react';
import { 
  Scan, 
  BarChart3, 
  History, 
  Bot, 
  LogIn, 
  LogOut, 
  Scale,
  Sparkles,
  Menu,
  X,
  Shield,
  ChevronRight
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems: { id: TabType; label: string; icon: React.ReactNode; badge?: string; color?: string }[] = [
    { id: 'scan', label: 'Scan & Inspect', icon: <Scan className="w-4 h-4" />, color: 'brand' },
    { id: 'dashboard', label: 'Analytics', icon: <BarChart3 className="w-4 h-4" />, color: 'indigo' },
    { id: 'history', label: 'Audit History', icon: <History className="w-4 h-4" />, color: 'emerald' },
    { id: 'assistant', label: 'Legal AI', icon: <Bot className="w-4 h-4" />, badge: 'AI', color: 'violet' },
  ];

  const colorMap: Record<string, string> = {
    brand:  'text-sky-300 bg-sky-500/10 border-sky-500/30 hover:bg-sky-500/15',
    indigo: 'text-indigo-300 bg-indigo-500/10 border-indigo-500/30 hover:bg-indigo-500/15',
    emerald:'text-emerald-300 bg-emerald-500/10 border-emerald-500/30 hover:bg-emerald-500/15',
    violet: 'text-violet-300 bg-violet-500/10 border-violet-500/30 hover:bg-violet-500/15',
  };

  return (
    <>
      <header className="sticky top-0 z-40 w-full">
        {/* Top accent line */}
        <div className="h-[2px] w-full bg-gradient-to-r from-transparent via-sky-500 to-indigo-500 opacity-70" />
        
        <div className="glass-strong border-b border-white/5">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
            
            {/* ── Brand ── */}
            <div
              className="flex items-center space-x-3 cursor-pointer group flex-shrink-0"
              onClick={() => { setActiveTab('scan'); setMobileMenuOpen(false); }}
            >
              <div className="relative w-10 h-10 rounded-2xl flex items-center justify-center shadow-lg overflow-hidden"
                style={{ background: 'linear-gradient(135deg, #0171c7, #4f46e5)' }}
              >
                <Scale className="w-5 h-5 text-white" />
                <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-display font-900 text-lg tracking-tight text-white leading-none">
                    Legal<span className="juru-badge">Metrix</span>
                  </span>
                </div>
              </div>
            </div>

            {/* ── Desktop Nav ── */}
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => {
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    id={`nav-${item.id}`}
                    onClick={() => setActiveTab(item.id)}
                    className={`relative flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-200 border ${
                      isActive
                        ? `${colorMap[item.color || 'brand']} shadow-sm`
                        : 'text-slate-400 border-transparent hover:text-slate-100 hover:bg-white/5'
                    }`}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                    {item.badge && (
                      <span className="px-1.5 py-0.5 rounded-md bg-violet-500/20 text-violet-300 text-[9px] font-bold border border-violet-500/30 flex items-center gap-0.5">
                        <Sparkles className="w-2.5 h-2.5" />
                        {item.badge}
                      </span>
                    )}
                    {isActive && (
                      <span className="absolute -bottom-px left-4 right-4 h-0.5 rounded-full bg-current opacity-60" />
                    )}
                  </button>
                );
              })}
            </nav>

            {/* ── Auth / Profile ── */}
            <div className="flex items-center gap-2 flex-shrink-0">
              {isAuthenticated && user ? (
                <div className="flex items-center gap-2.5 glass rounded-xl px-3 py-1.5 border border-white/5">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center text-sky-200 font-bold text-xs shrink-0"
                    style={{ background: 'linear-gradient(135deg, rgba(1,113,199,0.5), rgba(79,70,229,0.5))' }}
                  >
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <div className="hidden sm:block leading-tight">
                    <p className="text-xs font-semibold text-slate-100">{user.username}</p>
                    <p className="text-[10px] text-slate-400 capitalize">{user.role}{user.badge_number ? ` · #${user.badge_number}` : ''}</p>
                  </div>
                  <button
                    onClick={logout}
                    title="Sign Out"
                    className="p-1 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors ml-1"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={onOpenAuth}
                  id="officer-login-btn"
                  className="btn-primary text-xs !py-2 !px-3.5"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Officer Login</span>
                </button>
              )}

              {/* Mobile menu toggle */}
              <button
                className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ── Mobile Menu Drawer ── */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-30 pt-16">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} />
          <div className="relative glass-strong border-b border-white/5 animate-slide-up">
            <nav className="max-w-7xl mx-auto px-4 py-4 flex flex-col gap-1">
              {navItems.map((item) => {
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => { setActiveTab(item.id); setMobileMenuOpen(false); }}
                    className={`flex items-center justify-between px-4 py-3.5 rounded-xl text-sm font-semibold transition-all ${
                      isActive ? `${colorMap[item.color || 'brand']} border` : 'text-slate-300 hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {item.icon}
                      <span>{item.label}</span>
                      {item.badge && (
                        <span className="px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 text-[10px] font-bold">
                          {item.badge}
                        </span>
                      )}
                    </div>
                    <ChevronRight className="w-4 h-4 opacity-40" />
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      )}
    </>
  );
};
