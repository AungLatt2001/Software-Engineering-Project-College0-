// client/src/context/AuthContext.js
import React, { createContext, useContext, useState, useCallback } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

const api = axios.create({ baseURL: '/api' });
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('college0_token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('college0_user')); } catch { return null; }
  });

  const login = useCallback(async (userId, password) => {
    const res = await api.post('/login', { userId, password });
    localStorage.setItem('college0_token', res.data.token);
    localStorage.setItem('college0_user', JSON.stringify(res.data.user));
    setUser(res.data.user);
    return res.data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('college0_token');
    localStorage.removeItem('college0_user');
    setUser(null);
  }, []);

  const changePassword = useCallback(async (newPassword) => {
    await api.post('/change-password', { newPassword });
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, changePassword, api }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
export { api };
