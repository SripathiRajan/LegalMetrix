import React, { useState } from 'react';
import { X, Lock, User, Mail, ShieldAlert, Shield, Eye, EyeOff } from 'lucide-react';
import { authApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const { login } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState('');
  const [badgeNumber, setBadgeNumber] = useState('');
  const [role, setRole] = useState('inspector');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      if (isRegister) {
        const data = await authApi.register({ username, password, email: email || undefined, badge_number: badgeNumber || undefined, role });
        login(data.access_token, data.officer);
      } else {
        const data = await authApi.login(username, password);
        login(data.access_token, data.officer);
      }
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Authentication failed. Please check credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const inputCls = "w-full rounded-xl px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-500/50 transition-all";
  const inputStyle = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
      <div
        className="relative w-full max-w-md rounded-2xl p-7 shadow-2xl animate-slide-up"
        style={{
          background: 'rgba(8,15,30,0.98)',
          border: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '0 25px 80px rgba(0,0,0,0.7), 0 0 60px rgba(14,165,233,0.08), 0 0 0 1px rgba(255,255,255,0.06)',
        }}
      >
        {/* Top accent */}
        <div className="absolute top-0 left-8 right-8 h-px rounded-full"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(14,165,233,0.6), transparent)' }} />

        {/* Close */}
        <button onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-white/8 transition-colors">
          <X className="w-5 h-5" />
        </button>

        {/* Icon + Title */}
        <div className="text-center mb-7">
          <div className="relative inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-4"
            style={{ background: 'linear-gradient(135deg, rgba(1,113,199,0.2), rgba(79,70,229,0.2))', border: '1px solid rgba(14,165,233,0.25)' }}
          >
            <Lock className="w-6 h-6 text-sky-400" />
            <div className="absolute inset-0 rounded-2xl" style={{ boxShadow: '0 0 30px rgba(14,165,233,0.15)' }} />
          </div>
          <h2 className="text-xl font-bold text-white font-display">
            {isRegister ? 'Register Officer Account' : 'Inspector Authentication'}
          </h2>
          <p className="text-xs text-slate-500 mt-1.5 max-w-xs mx-auto">
            {isRegister
              ? 'Create secure officer credentials to manage audits & view analytics.'
              : 'Sign in with your official department credentials.'}
          </p>
        </div>

        {/* Security badge */}
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl mb-5 border"
          style={{ background: 'rgba(14,165,233,0.05)', borderColor: 'rgba(14,165,233,0.15)' }}
        >
          <Shield className="w-3.5 h-3.5 text-sky-500 flex-shrink-0" />
          <span className="text-[11px] text-slate-400">Secured by Official Authentication System · SSL Encrypted</span>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3.5 rounded-xl flex items-start gap-2.5 text-rose-300 text-xs animate-fade-in"
            style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
            <ShieldAlert className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Username */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Username <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <input type="text" required value={username} onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. officer_sharma" className={inputCls} style={inputStyle} />
              <User className="absolute right-3.5 top-3.5 w-4 h-4 text-slate-600" />
            </div>
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Password <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <input type={showPassword ? 'text' : 'password'} required value={password}
                onChange={(e) => setPassword(e.target.value)} placeholder="••••••••"
                className={`${inputCls} pr-10`} style={inputStyle} />
              <button type="button" onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-3.5 text-slate-600 hover:text-slate-400 transition-colors">
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Register fields */}
          {isRegister && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Official Email (Optional)</label>
                <div className="relative">
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                    placeholder="officer@dept.gov.in" className={inputCls} style={inputStyle} />
                  <Mail className="absolute right-3.5 top-3.5 w-4 h-4 text-slate-600" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">Badge Number</label>
                  <input type="text" value={badgeNumber} onChange={(e) => setBadgeNumber(e.target.value)}
                    placeholder="e.g. LM-892" className={inputCls} style={inputStyle} />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">Role</label>
                  <select value={role} onChange={(e) => setRole(e.target.value)}
                    className={inputCls} style={inputStyle}>
                    <option value="inspector">Inspector</option>
                    <option value="admin">Administrator</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Submit */}
          <button type="submit" disabled={isLoading}
            className="w-full py-3 px-4 rounded-xl font-bold text-sm text-white transition-all active:scale-95 disabled:opacity-50 mt-2 flex items-center justify-center gap-2"
            style={{
              background: 'linear-gradient(135deg, #0171c7, #4f46e5)',
              boxShadow: '0 4px 20px rgba(14,165,233,0.3)',
            }}
          >
            {isLoading ? (
              <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Authenticating...</>
            ) : isRegister ? 'Complete Officer Registration' : 'Sign In to Dashboard'}
          </button>
        </form>

        <div className="mt-5 pt-4 border-t border-white/5 text-center">
          <button type="button" onClick={() => { setIsRegister(!isRegister); setError(null); }}
            className="text-xs text-sky-500 hover:text-sky-300 transition-colors font-medium">
            {isRegister ? 'Already have an account? Sign In' : "Need an Inspector profile? Create Account"}
          </button>
        </div>
      </div>
    </div>
  );
};
