import React, { createContext, useContext, useState, useEffect } from 'react';
import type { OfficerProfile } from '../types/api';
import { authApi } from '../services/api';

interface AuthContextType {
  user: OfficerProfile | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, user: OfficerProfile) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('legalmetrix_token'));
  const [user, setUser] = useState<OfficerProfile | null>(() => {
    const saved = localStorage.getItem('legalmetrix_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const profile = await authApi.getMe();
          setUser(profile);
          localStorage.setItem('legalmetrix_user', JSON.stringify(profile));
        } catch {
          // Token expired or invalid
          localStorage.removeItem('legalmetrix_token');
          localStorage.removeItem('legalmetrix_user');
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, [token]);

  const login = (newToken: string, newUser: OfficerProfile) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('legalmetrix_token', newToken);
    localStorage.setItem('legalmetrix_user', JSON.stringify(newUser));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('legalmetrix_token');
    localStorage.removeItem('legalmetrix_user');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        isAuthenticated: !!token && !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
